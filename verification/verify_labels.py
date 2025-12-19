
import os
import sys
import time
import subprocess
from playwright.sync_api import sync_playwright, expect

def verify_labels():
    repo_root = os.getcwd()
    frontend_dir = os.path.join(repo_root, "frontend")

    # Start backend
    backend_env = {**os.environ, "PYTHONPATH": os.path.join(repo_root, "backend", "src")}
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "agent.app:app", "--port", "8000"],
        cwd=os.path.join(repo_root, "backend"),
        env=backend_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Start frontend
    frontend_process = subprocess.Popen(
        ["pnpm", "dev", "--port", "5173"],
        cwd=frontend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:
        # Wait for services
        time.sleep(10)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Go to app
            page.goto("http://localhost:5173/app/")

            # Wait for load
            page.wait_for_selector("text=Welcome.", timeout=30000)

            # 1. Verify "Effort" label
            print("Testing Effort label...")
            page.locator("label", has_text="Effort").click()
            # Wait for option
            effort_option = page.locator('div[role="option"]').filter(has_text="High").first
            expect(effort_option).to_be_visible()
            print("SUCCESS: Effort menu opened.")

            # Close menu
            page.keyboard.press("Escape")
            time.sleep(0.5)

            # 2. Verify "Model" label
            print("Testing Model label...")
            page.locator("label", has_text="Model").click()
            # Wait for option
            model_option = page.locator('div[role="option"]').filter(has_text="2.5 Pro").first
            expect(model_option).to_be_visible()
            print("SUCCESS: Model menu opened.")

            # Screenshot
            page.screenshot(path="verification/labels_verified.png")

            browser.close()

    finally:
        backend_process.terminate()
        frontend_process.terminate()

if __name__ == "__main__":
    verify_labels()
