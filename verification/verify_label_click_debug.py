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
             page.screenshot(path="verification/failed_load.png")
             return

        # Debug: Dump HTML to see what's actually there
        print(page.content())

        # 1. Verify "Effort" label click focuses the select
        # Click the label text "Effort"
        page.get_by_text("Effort", exact=True).click()

        # Wait a tiny bit for focus transition
        page.wait_for_timeout(100)

        # Check if the select trigger (which is a button) receives focus
        effort_trigger = page.locator("#effort-select")

        # Debug: Check if element exists
        if effort_trigger.count() > 0:
             print("Element #effort-select found")
             print(f"Is visible: {effort_trigger.is_visible()}")
             print(f"Is enabled: {effort_trigger.is_enabled()}")
             # Force focus to see if it works manually
             # effort_trigger.focus()
        else:
             print("Element #effort-select NOT found")

        try:
            expect(effort_trigger).to_be_focused(timeout=2000)
            print("PASS: Clicking 'Effort' label focused the Effort select.")
        except AssertionError as e:
            print(f"FAIL: {e}")
            page.screenshot(path="verification/effort_fail.png")

        browser.close()

if __name__ == "__main__":
    verify_label_click()
