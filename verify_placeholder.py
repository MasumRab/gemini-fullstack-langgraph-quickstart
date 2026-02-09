from playwright.sync_api import sync_playwright, expect
import sys

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        # Go to frontend
        print("Navigating to http://localhost:5173/app/...")
        page.goto("http://localhost:5173/app/")

        # Wait for the input to be visible
        print("Waiting for textarea...")
        # The textarea has aria-label="Chat input"
        textarea = page.get_by_role("textbox", name="Chat input")
        expect(textarea).to_be_visible(timeout=10000)

        # Check for the class name
        class_attr = textarea.get_attribute("class")
        print(f"Textarea classes: {class_attr}")

        if "placeholder-neutral-400" in class_attr:
            print("SUCCESS: Found placeholder-neutral-400")
        else:
            print(f"FAILURE: Did not find placeholder-neutral-400. Found: {class_attr}")
            sys.exit(1)

        # Screenshot
        page.screenshot(path="verification_screenshot.png")
        print("Screenshot saved to verification_screenshot.png")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
