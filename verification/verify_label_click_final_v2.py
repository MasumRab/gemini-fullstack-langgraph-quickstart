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

        # 1. Verify "Effort" label click
        print("Clicking 'Effort' label...")
        page.get_by_text("Effort", exact=True).click()
        high_option = page.get_by_role("option", name="High")
        expect(high_option).to_be_visible()
        print("PASS: Clicking 'Effort' label opened the Select menu (Option 'High' is visible).")

        # Close it by pressing Escape
        page.keyboard.press("Escape")

        # 2. Verify "Model" label click
        print("Clicking 'Model' label...")
        page.get_by_text("Model", exact=True).click()

        # We need a more specific locator to avoid strict mode violations (finding duplicates)
        # The option text is " 2.5 Flash"
        # Let's verify that the dropdown content is visible

        # Look for the dropdown content container or a specific item
        # The error said it found 2 elements. One might be the hidden select option?
        # Let's use get_by_role('option') which targets the visible UI elements usually

        # "2.5 Pro" is another option
        pro_option = page.get_by_role("option", name="2.5 Pro")
        expect(pro_option).to_be_visible()
        print("PASS: Clicking 'Model' label opened the Select menu (Option '2.5 Pro' is visible).")

        # Take a screenshot of the open menu
        page.screenshot(path="verification/label_click_success.png")
        print("Screenshot saved to verification/label_click_success.png")

        browser.close()

if __name__ == "__main__":
    verify_label_click()
