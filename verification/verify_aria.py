from playwright.sync_api import sync_playwright

def verify_accessibility(page):
    # Navigate to the app (assuming default vite port 5173)
    page.goto("http://localhost:5173")

    # Wait for the input form to be visible
    page.wait_for_selector("form")

    # Check for the Textarea with the new aria-label
    textarea = page.get_by_label("Search query")
    if not textarea.is_visible():
        raise AssertionError("❌ Textarea with aria-label='Search query' NOT found.")
    
    print("✅ Textarea with aria-label='Search query' found.")

    # To check the stop button, we might need to be in a loading state,
    # but the button is rendered conditionally based on `isLoading`.
    # However, the InputForm component renders the Stop button OR the Search button.
    # Initially it is NOT loading, so we see the Search button.
    # The search button is inside the form.

    # Let's take a screenshot of the initial state
    page.screenshot(path="verification/input_form_initial.png")
    print("📸 Screenshot taken: verification/input_form_initial.png")

    # We can inspect the DOM to verify the aria-label is present on the textarea
    # verifying properties
    aria_label = textarea.get_attribute("aria-label")
    print(f"Textarea aria-label: {aria_label}")

if __name__ == "__main__":
    import sys
    success = True
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            verify_accessibility(page)
        except Exception as e:
            print(f"Verification failed: {e}")
            success = False
        finally:
            browser.close()
    
    if not success:
        sys.exit(1)
