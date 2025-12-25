from playwright.sync_api import sync_playwright

def verify_focus_rings():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            print("Navigating to app...")
            page.goto("http://localhost:5173/")

            # Wait for content to load
            page.wait_for_selector("text=Welcome")

            print("Testing New Search button focus...")
            # Navigate to New Search button (it's hidden by default if !hasHistory, so we might need to simulate history or check other buttons)
            # Actually, New Search only shows if hasHistory is true.
            # But "Stop Generating" only shows if isLoading.
            # "Copy" only shows on messages.

            # The "Effort" and "Model" selects are always visible.
            # The "Stop Generating" button is NOT visible initially.

            # Let's test the Input Form inputs which I touched (aria-hidden on labels).

            # Focus on Effort Select Trigger
            page.click("label[for='effort-select']")
            page.keyboard.press("Escape") # Close select if opened

            # Focus on Model Select Trigger
            page.click("label[for='model-select']")
            page.keyboard.press("Escape")

            # Take a screenshot of the form area
            page.locator("form").screenshot(path="verification/form_focus.png")

            # To test "New Search" button, we need history.
            # We can force the state or just mock the component?
            # Or type something to submit.

            print("Submitting a query to generate history...")
            page.fill("textarea", "Hello")
            page.keyboard.press("Enter")

            # Wait for "Stop Generating" to appear (isLoading=true)
            # It might appear briefly.
            try:
                stop_btn = page.locator("button[aria-label='Stop generating']")
                stop_btn.wait_for(state="visible", timeout=5000)
                stop_btn.focus()
                page.locator("form").screenshot(path="verification/stop_button_focus.png")
                print("Captured Stop Button focus")
            except:
                print("Could not catch Stop Button")

            # After response (or if we cancel), we might have history?
            # If we cancel, we might not have history depending on logic.
            # Let's wait a bit.

            # Actually, to verify the CSS changes, I can also just inspect the computed styles or trust the visual if I can trigger it.

            print("Completed verification script")

        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="verification/error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    verify_focus_rings()
