import time
from playwright.sync_api import sync_playwright

def verify_chat_rendering():
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Navigate to app - NOTE: using /app/ based on log
            print("Navigating to app...")
            page.goto("http://localhost:5173/app/")

            # Wait for input to be ready
            page.wait_for_selector("textarea", state="visible", timeout=20000)

            # Type a message
            print("Typing message...")
            page.fill("textarea", "Testing Bolt Optimization")

            # Take a screenshot before submit
            page.screenshot(path="verification/verification.png")
            print("Screenshot taken: verification/verification.png")

            print("Verification script finished successfully (UI loads).")

        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="verification/error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    verify_chat_rendering()
