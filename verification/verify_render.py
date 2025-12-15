from playwright.sync_api import sync_playwright

def verify_app_render():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            # Navigate to the app served by backend
            page.goto("http://localhost:8000/app/")

            # Wait for the app to load (look for a key element, e.g., thread or input)
            # Based on the code, there's likely an input field or a main container
            # Let's wait for something generic first or check title
            page.wait_for_load_state("networkidle")

            # Take a screenshot
            page.screenshot(path="verification/app_render.png")
            print("Screenshot saved to verification/app_render.png")

        except Exception as e:
            print(f"Error: {e}")
            # Take screenshot of error state
            page.screenshot(path="verification/error_state.png")
        finally:
            browser.close()

if __name__ == "__main__":
    verify_app_render()
