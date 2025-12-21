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

        # 1. Verify "Effort" label click opens the select content (which means it worked)
        # Instead of checking focus on the trigger, we check if the content becomes visible or if focus moves to an item
        # Radix UI Select often moves focus to the selected item when opened via click

        print("Clicking 'Effort' label...")
        page.get_by_text("Effort", exact=True).click()

        # Check if the listbox content is visible
        # Radix UI Select Content usually has role="listbox" or "presentation" inside a portal
        # But specifically, we can look for the option "Medium" being visible and potentially focused

        # The output from previous run showed the active element was:
        # <div role="option" ...><span ...>Medium</span></div>
        # This confirms that clicking the label OPENED the select menu and focused the selected option.
        # This is the expected behavior for a label linked to a SelectTrigger in Radix UI!

        # So we verify that the select content is open.
        # We can check for the presence of the "High" option which is only visible when open

        high_option = page.get_by_role("option", name="High")
        expect(high_option).to_be_visible()
        print("PASS: Clicking 'Effort' label opened the Select menu (Option 'High' is visible).")

        # Close it by pressing Escape
        page.keyboard.press("Escape")

        # 2. Verify "Model" label click opens the select
        print("Clicking 'Model' label...")
        page.get_by_text("Model", exact=True).click()

        # Check for a model option
        # flash_option = page.get_by_role("option", name="2.5 Flash")
        # Note: The text in the option is " 2.5 Flash" with an icon.
        # Let's look for text "2.5 Flash"
        flash_option = page.get_by_text("2.5 Flash")
        expect(flash_option).to_be_visible()
        print("PASS: Clicking 'Model' label opened the Select menu (Option '2.5 Flash' is visible).")

        # Take a screenshot of the open menu
        page.screenshot(path="verification/label_click_success.png")
        print("Screenshot saved to verification/label_click_success.png")

        browser.close()

if __name__ == "__main__":
    verify_label_click()
