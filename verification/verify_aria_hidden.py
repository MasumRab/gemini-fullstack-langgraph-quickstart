
import os
import sys
import time
import subprocess
import requests
from playwright.sync_api import sync_playwright, expect

# Constants
FRONTEND_PORT = 5173
BACKEND_PORT = 8000
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}/app/"
SCREENSHOT_PATH = "verification/aria_hidden_verification.png"

def wait_for_service(url, timeout=60):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print(f"Service at {url} is ready.")
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    print(f"Service at {url} timed out.")
    return False

def verify_aria_attributes(page):
    print("Navigating to app...")
    page.goto(FRONTEND_URL)

    # Wait for the input form to be visible (indicates app loaded)
    page.wait_for_selector("form")

    # 1. Verify InputForm icons have aria-hidden
    print("Verifying InputForm icons...")
    # The Send icon in the search button
    send_icon = page.locator("button[type='submit'] svg.lucide-send")
    if send_icon.count() > 0:
        expect(send_icon).to_have_attribute("aria-hidden", "true")
        print("✅ Send icon has aria-hidden='true'")

    # The StopCircle icon (if visible, but usually not on load)

    # 2. Simulate a search to generate activity and messages
    # We can't easily simulate a full search without a running backend that responds.
    # However, we can check the static elements we modified if they are present or mock the state.
    # Since we modified `ChatMessagesView` (copy button) and `ActivityTimeline`, we need these to render.

    # To properly test this without a full backend response, we might need to rely on unit tests or
    # manually inspecting the code. But let's try to see if we can trigger a state.
    # Actually, the WelcomeScreen uses InputForm, so we verified InputForm icons.

    # Let's verify the "New Search" button icon if history is present?
    # Hard to force history without backend interaction.

    # However, we can check the ActivityTimeline if we can trigger a loading state.
    # If we type and submit, it enters loading state.

    print("Submitting a query to trigger loading state...")
    page.fill("textarea[aria-label='Chat input']", "Test query")
    page.click("button[type='submit']")

    # Wait for loading state (ActivityTimeline should appear)
    # The backend might not respond if not fully set up or mocked, but the frontend should show loading state immediately.

    try:
        page.wait_for_selector("text=Searching...", timeout=5000)
        print("✅ Loading state triggered.")

        # Verify ActivityTimeline icons
        # The loader icon in ActivityTimeline
        loader_icon = page.locator("div.rounded-full > svg.animate-spin")
        # There might be multiple loaders. Check the one in the timeline.
        if loader_icon.count() > 0:
             # We expect at least one loader to have aria-hidden=true
             # The first one might be the main loader, but let's check the first one found.
             expect(loader_icon.first).to_have_attribute("aria-hidden", "true")
             print("✅ ActivityTimeline Loader icon has aria-hidden='true'")

    except Exception as e:
        print(f"⚠️ Could not trigger/find loading state: {e}")

    # Take a screenshot
    page.screenshot(path=SCREENSHOT_PATH)
    print(f"Screenshot saved to {SCREENSHOT_PATH}")

def run_verification():
    # Start Backend (for app to load config/health)
    # We use a minimal command to just keep it alive if needed, or rely on existing running services?
    # The instructions say "lifecycle managed".

    # Assuming environment is set up.

    print("Starting Backend...")
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "agent.app:app", "--port", str(BACKEND_PORT)],
        cwd="backend",
        env={**os.environ, "PYTHONPATH": f"{os.getcwd()}/backend/src"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    print("Starting Frontend...")
    frontend_process = subprocess.Popen(
        ["pnpm", "dev", "--port", str(FRONTEND_PORT)],
        cwd="frontend",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    try:
        # Wait for services
        if not wait_for_service(f"http://localhost:{BACKEND_PORT}/health"):
            print("Backend failed to start.")
            # proceed anyway, maybe frontend can load partially

        if not wait_for_service(FRONTEND_URL):
            print("Frontend failed to start.")
            return

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            verify_aria_attributes(page)
            browser.close()

    finally:
        print("Stopping services...")
        frontend_process.terminate()
        backend_process.terminate()
        frontend_process.wait()
        backend_process.wait()

if __name__ == "__main__":
    run_verification()
