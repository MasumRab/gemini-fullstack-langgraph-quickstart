from playwright.sync_api import sync_playwright

def verify_setup():
    """
    Simple verification script to ensure Playwright is working in the environment.
    Since we cannot easily spin up the full frontend/backend stack in this environment
    without blocking, we will verify that Playwright can launch a browser.
    """
    print("Verifying Playwright setup...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # Just go to a dummy page or blank
            page.goto("about:blank")
            print("Playwright launched successfully.")
            browser.close()
    except Exception as e:
        print(f"Playwright verification failed: {e}")
        exit(1)

if __name__ == "__main__":
    verify_setup()
