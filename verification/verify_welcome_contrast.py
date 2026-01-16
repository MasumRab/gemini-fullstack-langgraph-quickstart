import os
import sys
import subprocess
import time
from playwright.sync_api import sync_playwright, expect

# Constants
FRONTEND_DIR = "frontend"
FRONTEND_PORT = 5174
BASE_URL = f"http://localhost:{FRONTEND_PORT}"
SCREENSHOT_PATH = "verification/welcome_screen_contrast.png"

def verify_welcome_contrast():
    print(f"Starting frontend verification on {BASE_URL}...")

    # Ensure verification directory exists
    os.makedirs("verification", exist_ok=True)

    # Start frontend server
    frontend_process = subprocess.Popen(
        ["pnpm", "dev", "--port", str(FRONTEND_PORT)],
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Wait for server to start
        print("Waiting for frontend server...")
        time.sleep(5)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            print(f"Navigating to {BASE_URL}...")
            try:
                page.goto(BASE_URL)
            except Exception as e:
                print(f"Failed to navigate: {e}")
                print("Frontend stdout:", frontend_process.stdout.read() if frontend_process.stdout else "None")
                print("Frontend stderr:", frontend_process.stderr.read() if frontend_process.stderr else "None")
                sys.exit(1)

            # Wait for content
            page.wait_for_selector("text=Welcome.")

            # Check for the footer text
            footer_text_locator = page.locator("text=Powered by Google Gemini and LangChain LangGraph.")
            expect(footer_text_locator).to_be_visible()

            # Check class
            class_attr = footer_text_locator.get_attribute("class")
            print(f"Footer text classes: {class_attr}")

            if "text-neutral-400" in class_attr:
                print("SUCCESS: Footer text has 'text-neutral-400' class.")
            else:
                print(f"FAILED: Footer text does not have 'text-neutral-400'. Found: {class_attr}")
                sys.exit(1)

            # Take screenshot
            page.screenshot(path=SCREENSHOT_PATH)
            print(f"Screenshot saved to {SCREENSHOT_PATH}")

            browser.close()

    finally:
        frontend_process.terminate()
        frontend_process.wait()

if __name__ == "__main__":
    verify_welcome_contrast()
