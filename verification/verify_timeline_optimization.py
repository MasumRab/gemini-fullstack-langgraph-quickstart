import time
import os
import signal
import subprocess
import requests
from playwright.sync_api import sync_playwright

def wait_for_server(url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(url)
            return True
        except requests.ConnectionError:
            time.sleep(1)
    return False

def verify_timeline(page):
    print("Navigating to app...")
    page.goto("http://localhost:5173/app/")

    # Wait for the chat input to be visible
    page.get_by_placeholder("What would you like to research?").wait_for(state="visible")

    # Type a message
    page.get_by_placeholder("What would you like to research?").fill("test message")

    # Take a screenshot of the initial state
    page.screenshot(path="verification/initial_state.png")
    print("Initial screenshot taken.")

if __name__ == "__main__":
    # Start backend
    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = f"{os.getcwd()}:{os.getcwd()}/backend/src"
    backend_process = subprocess.Popen(
        ["python", "-m", "uvicorn", "agent.app:app", "--port", "8000"],
        cwd="backend",
        env=backend_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Start frontend
    frontend_process = subprocess.Popen(
        ["pnpm", "dev"],
        cwd="frontend",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:
        if wait_for_server("http://localhost:8000/health") and wait_for_server("http://localhost:5173/app/"):
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                verify_timeline(page)
                browser.close()
        else:
            print("Servers failed to start.")
    finally:
        os.kill(backend_process.pid, signal.SIGTERM)
        os.kill(frontend_process.pid, signal.SIGTERM)
