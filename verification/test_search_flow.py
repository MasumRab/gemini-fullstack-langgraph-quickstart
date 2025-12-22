import os
import subprocess
import time
import signal
import sys
import requests
from playwright.sync_api import sync_playwright

def test_full_search_flow():
    print("Starting verification test...", flush=True)

    backend_log = open("backend.log", "w")
    frontend_log = open("frontend.log", "w")

    print("Starting backend (langgraph dev)...", flush=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    env["REQUIRE_PLANNING_CONFIRMATION"] = "false"
    if "GEMINI_API_KEY" not in env:
        print("WARNING: GEMINI_API_KEY not found in environment!", flush=True)

    backend_process = subprocess.Popen(
        ["langgraph", "dev", "--no-browser", "--port", "2024", "--host", "127.0.0.1"],
        cwd="backend",
        env=env,
        stdout=backend_log,
        stderr=backend_log,
        preexec_fn=os.setsid
    )

    print("Starting frontend...", flush=True)
    frontend_process = subprocess.Popen(
        ["pnpm", "dev", "--port", "5173"],
        cwd="frontend",
        stdout=frontend_log,
        stderr=frontend_log,
        preexec_fn=os.setsid
    )

    try:
        print("Waiting for backend health check (up to 45s)...", flush=True)
        backend_healthy = False
        for i in range(45):
            try:
                r = requests.get("http://127.0.0.1:2024/health", timeout=1)
                if r.status_code == 200:
                    print("Backend is healthy!", flush=True)
                    backend_healthy = True
                    break
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(1)

            if backend_process.poll() is not None:
                print("Backend process died early!", flush=True)
                raise Exception("Backend failed to start")

        if not backend_healthy:
            print("Backend health check timed out.", flush=True)
            raise Exception("Backend did not start in time")

        print("Waiting for frontend to be ready (fixed 5s)...", flush=True)
        time.sleep(5)

        with sync_playwright() as p:
            print("Launching browser...", flush=True)
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            print("Navigating to frontend...", flush=True)
            page.goto("http://localhost:5173", timeout=30000)

            print("Page loaded.", flush=True)

            # Since Trigger 1 is "Gemma 3", we are already on the correct model!
            # No need to change it.
            print("Model is already Gemma 3.", flush=True)

            input_selector = 'textarea[aria-label="Chat input"]'
            page.wait_for_selector(input_selector, timeout=10000)

            print("Focusing and typing query...", flush=True)
            page.focus(input_selector)

            query = "What is the capital of France?"
            page.keyboard.type(query, delay=50)

            time.sleep(1)

            submit_selector = "button:has-text('Search')"
            page.click(submit_selector)

            print("Waiting for response...", flush=True)
            try:
                page.wait_for_selector("text=Paris", timeout=60000)
                print("Found 'Paris' in response!", flush=True)
            except Exception as e:
                print("Did not find expected text 'Paris'. Taking error screenshot.", flush=True)
                page.screenshot(path="verification_scripts/error_no_response.png")
                raise e

            page.screenshot(path="verification_scripts/2_search_result.png")
            print("Test passed successfully!", flush=True)
            browser.close()

    except Exception as e:
        print(f"Test failed: {e}", flush=True)
    finally:
        print("Cleaning up processes...", flush=True)
        try:
            os.killpg(os.getpgid(backend_process.pid), signal.SIGTERM)
        except:
            pass
        try:
            os.killpg(os.getpgid(frontend_process.pid), signal.SIGTERM)
        except:
            pass
        backend_log.close()
        frontend_log.close()
        print("Done.", flush=True)

if __name__ == "__main__":
    test_full_search_flow()
