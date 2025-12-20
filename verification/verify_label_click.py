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
            print("Make sure the frontend dev server is running!")
            sys.exit(1)

        # Wait for the form to be visible
        try:
            expect(page.get_by_label("Chat input")).to_be_visible(timeout=5000)
        except:
             print("Chat input not found. App might not be fully loaded.")
             page.screenshot(path="verification/failed_load.png")
             return

        # 1. Verify "Effort" label click focuses the select
        # Click the label text "Effort"
        page.get_by_text("Effort", exact=True).click()

        # Check if the select trigger (which is a button) receives focus
        effort_trigger = page.locator("#effort-select")
        expect(effort_trigger).to_be_focused()
        print("PASS: Clicking 'Effort' label focused the Effort select.")

        # 2. Verify "Model" label click focuses the select
        page.get_by_text("Model", exact=True).click()

        # Check focus
        model_trigger = page.locator("#model-select")
        expect(model_trigger).to_be_focused()
        print("PASS: Clicking 'Model' label focused the Model select.")

        # Take a screenshot of the form with focus on model
        page.screenshot(path="verification/label_focus_verification.png")
        print("Screenshot saved to verification/label_focus_verification.png")

        browser.close()

if __name__ == "__main__":
    verify_label_click()
