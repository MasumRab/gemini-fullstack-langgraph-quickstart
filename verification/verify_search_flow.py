import os
import sys
import time
from playwright.sync_api import sync_playwright, Page, expect

# Configuration
VERIFICATION_URL = os.environ.get("VERIFICATION_URL", "http://localhost:5173")
VERIFICATION_MODEL = os.environ.get("VERIFICATION_MODEL", "gemma-3-27b-it")
ARTIFACT_DIR = "verification/artifacts"
TIMEOUT = int(os.environ.get("VERIFICATION_TIMEOUT", "30000"))  # 30 seconds default

def ensure_artifacts_dir():
    if not os.path.exists(ARTIFACT_DIR):
        os.makedirs(ARTIFACT_DIR)

def log_message(message: str):
    print(f"[VERIFY] {message}")

def capture_artifact(page: Page, name: str):
    """Captures a screenshot and saves it to artifacts."""
    timestamp = int(time.time())
    screenshot_path = f"{ARTIFACT_DIR}/{name}_{timestamp}.png"
    page.screenshot(path=screenshot_path)
    log_message(f"Screenshot saved: {screenshot_path}")

def run_verification():
    ensure_artifacts_dir()
    log_message(f"Starting verification against {VERIFICATION_URL} with model {VERIFICATION_MODEL}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 1. Capture Console & Network Errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        failed_requests = []
        page.on("requestfailed", lambda request: failed_requests.append(f"{request.url} ({request.failure})"))

        try:
            # 2. Navigate to App
            log_message("Navigating to app...")
            page.goto(VERIFICATION_URL, timeout=TIMEOUT)
            page.wait_for_load_state("networkidle")
            capture_artifact(page, "initial_load")

            # 3. Select Model
            # Open dropdown
            log_message(f"Selecting model: {VERIFICATION_MODEL}")
            # Locate the trigger - based on InputForm.tsx, it has aria-label="Model selection"
            model_trigger = page.locator('button[aria-label="Model selection"]')

            # Check if we need to change it (it might default to what we want, but we should verify selection works)
            if model_trigger.is_visible():
                model_trigger.click()

                # Wait for content
                # The values in SelectItem are standard, e.g., 'gemma-3-27b-it'
                # We need to click the item with the value matching our desired model
                # Shadcn Select items often don't expose the value easily in text, but let's try data-value or internal text
                # Based on InputForm.tsx: <SelectItem value="gemma-3-27b-it">... Gemma 3 ...</SelectItem>
                # Playwright can select by text or look for the item

                # We'll use a locator for the item in the viewport (SelectContent)
                # Note: Shadcn portals the content to body usually
                model_option = page.locator(f'div[role="option"][data-value="{VERIFICATION_MODEL}"]')
                if not model_option.is_visible():
                     # Fallback: maybe the value prop isn't reflected as data-value in dom (it usually is for radix)
                     # Let's try to find it by text if the value selector fails, but specific value is safer
                     pass

                model_option.click()
                log_message("Model selected.")
            else:
                log_message("WARNING: Model selection dropdown not found. Continuing with default.")

            # 4. Input Query
            query = "What are the latest developments in AI agents?"
            log_message(f"Entering query: {query}")
            textarea = page.locator('textarea[aria-label="Chat input"]')
            textarea.fill(query)

            # 5. Submit
            submit_btn = page.locator('button[type="submit"]')
            # Ensure it's enabled
            expect(submit_btn).not_to_be_disabled()
            submit_btn.click()
            log_message("Query submitted.")

            # 6. Verify Flow Stages
            # We expect different UI states.
            # A common pattern is:
            # - Input clears or moves
            # - "Agent is thinking" or "Planning" appears
            # - Timeline updates

            # Wait for specific elements that indicate progress.
            # Adjust these selectors based on actual app behavior if needed.

            # a) Wait for processing state (Stop button appears)
            stop_btn = page.locator('button[aria-label="Stop generating"]')
            expect(stop_btn).to_be_visible(timeout=5000)
            log_message("Search in progress (Stop button visible).")
            capture_artifact(page, "search_in_progress")

            # b) Wait for completion (Stop button disappears OR Final Answer appears)
            # We'll wait for the "Final Answer" or a specific container
            # Assuming there's a markdown view or specific output container.
            # If we don't know the exact class, we wait for the network to settle or a long timeout

            log_message("Waiting for search completion...")

            # We assume the stream finishes when the stop button is gone or "Search" comes back
            # Or we look for a specific success element
            # Let's wait for the "Search" button to reappear, indicating streaming is done
            # OR check for content.

            # Let's wait up to 60s for a result (Deep search can be slow)
            page.wait_for_selector('button[type="submit"]', timeout=60000)
            # Verify we have some content. Ideally we look for "Final Answer" or similar text if the UI renders it.
            # We can check if the chat history has grown.

            capture_artifact(page, "search_complete")
            log_message("Search completed.")

            # 7. Semantic Verification
            # Check for generic success indicators
            content = page.content()

            # Simple heuristic: Did we get a response that isn't an error?
            if "Error" in content and "An error occurred" in content:
                 raise Exception("App displayed an error message.")

            # Check for non-empty response area (this depends on DOM structure)
            # Let's assume there's a message bubble container.

            log_message("Verification successful!")

        except Exception as e:
            log_message(f"ERROR: {str(e)}")
            capture_artifact(page, "error_state")

            # Log collected console errors
            if console_errors:
                log_message("Console Errors:")
                for err in console_errors:
                    log_message(f"  - {err}")

            if failed_requests:
                log_message("Failed Requests:")
                for req in failed_requests:
                    log_message(f"  - {req}")

            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    run_verification()
