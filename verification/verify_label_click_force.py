import sys
import os
import time
from playwright.sync_api import sync_playwright, expect

# Add repo root to pythonpath
sys.path.append(os.getcwd())

def verify_label_click():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the app (assuming it's running on port 5173/app/)
        try:
            page.goto("http://localhost:5173/app/", timeout=10000)
        except Exception as e:
            print(f"Failed to load page: {e}")
            sys.exit(1)

        # Wait for the form to be visible
        try:
            expect(page.get_by_label("Chat input")).to_be_visible(timeout=5000)
        except:
             print("Chat input not found.")
             return

        # 1. Verify "Effort" label click focuses the select
        # Click the label text "Effort"
        print("Clicking 'Effort' label...")
        page.get_by_text("Effort", exact=True).click()

        # Check if the select trigger (which is a button) receives focus
        effort_trigger = page.locator("#effort-select")

        # Try waiting a bit
        page.wait_for_timeout(500)

        # Check focus state manually via evaluation
        is_focused = page.evaluate("document.activeElement.id === 'effort-select'")
        print(f"Is focused (manual check): {is_focused}")

        if not is_focused:
            print("Active element is:", page.evaluate("document.activeElement.outerHTML"))

        # Take a screenshot
        page.screenshot(path="verification/effort_focus_check.png")
        print("Screenshot saved.")

        browser.close()

if __name__ == "__main__":
    verify_label_click()
