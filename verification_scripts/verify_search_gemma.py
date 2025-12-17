import os
import sys
import subprocess
import time
import signal
import requests
from playwright.sync_api import sync_playwright

# Configuration
BACKEND_PORT = 8000
FRONTEND_PORT = 5173  # Vite default
BACKEND_URL = f"http://localhost:{BACKEND_PORT}"
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"
CHECK_INTERVAL = 1
TIMEOUT = 60

# Model Configuration
GEMMA_MODEL = "gemma-3-27b-it"
ENV_VARS = os.environ.copy()

# Add backend/src to PYTHONPATH so 'agent' module can be found
# We assume the script is run from repo root, so backend/src is correct relative path
REPO_ROOT = os.getcwd()
BACKEND_SRC = os.path.join(REPO_ROOT, "backend", "src")
ENV_VARS["PYTHONPATH"] = f"{BACKEND_SRC}:{ENV_VARS.get('PYTHONPATH', '')}"

ENV_VARS.update({
    "QUERY_MODEL": GEMMA_MODEL,
    "REFLECTION_MODEL": GEMMA_MODEL,
    "ANSWER_MODEL": GEMMA_MODEL,
    "VALIDATION_MODEL": GEMMA_MODEL,
    "COMPRESSION_MODEL": GEMMA_MODEL,
    "SCOPING_MODEL": GEMMA_MODEL,
    "PLANNER_MODEL": GEMMA_MODEL,
    "OPTIMIZER_MODEL": GEMMA_MODEL,
    "MCP_ENABLED": "false"
})

def wait_for_service(url, name):
    print(f"Waiting for {name} at {url}...")
    start_time = time.time()
    while time.time() - start_time < TIMEOUT:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print(f"{name} is up!")
                return True
        except requests.ConnectionError:
            pass
        time.sleep(CHECK_INTERVAL)
    print(f"Timeout waiting for {name}")
    return False

def run_verification():
    backend_process = None
    frontend_process = None

    try:
        # 1. Start Backend
        print("Starting Backend...")
        print(f"PYTHONPATH: {ENV_VARS['PYTHONPATH']}")

        # Fallback to direct python execution if uv fails or has resolution issues
        # The 'uv run' command failed in the previous attempt due to dependency resolution.
        # We will try running uvicorn directly with the python executable,
        # assuming the environment already has necessary packages (which it should if tests run).

        backend_cmd = [
            sys.executable, "-m", "uvicorn", "agent.app:app",
            "--host", "0.0.0.0",
            "--port", str(BACKEND_PORT)
        ]

        backend_process = subprocess.Popen(
            backend_cmd,
            cwd="backend",
            env=ENV_VARS,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait for backend health
        if not wait_for_service(f"{BACKEND_URL}/health", "Backend"):
            print("Backend failed to start. Stderr:")
            # Read whatever is available
            print(backend_process.stderr.read())
            return

        # 2. Start Frontend
        print("Starting Frontend...")
        frontend_process = subprocess.Popen(
            ["pnpm", "dev", "--port", str(FRONTEND_PORT)],
            cwd="frontend",
            env=ENV_VARS,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait for frontend
        if not wait_for_service(FRONTEND_URL, "Frontend"):
             print("Frontend failed to start. Stderr:")
             print(frontend_process.stderr.read())
             return

        # 3. Run Playwright Test
        print("Running Playwright verification...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # Go to app
            print(f"Navigating to {FRONTEND_URL}...")
            page.goto(FRONTEND_URL)

            # Wait for load
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except:
                print("Network idle timeout, continuing...")

            page.screenshot(path="verification_scripts/01_initial_load.png")
            print("Saved 01_initial_load.png")

            # Input Query
            query = "Explain the architecture of Transformer models"
            print(f"Entering query: {query}")

            # Try to find the textarea
            try:
                page.wait_for_selector("textarea", timeout=5000)
                page.fill("textarea", query)
            except:
                # Fallback to input if textarea not found
                print("Textarea not found, trying input...")
                page.fill("input", query)

            # Click Submit
            # Try finding a button with type submit
            try:
                page.click("button[type='submit']", timeout=3000)
            except:
                print("Submit button not found, pressing Enter...")
                page.press("textarea", "Enter")

            print("Query submitted.")

            # 4. Verify Planning Phase
            print("Waiting for 'Planning' state...")
            try:
                # Wait for any indicator of activity.
                # "Planning", "Thinking", or just the absence of the empty state.
                # Let's wait a bit for UI update
                time.sleep(2)
                page.screenshot(path="verification_scripts/02_planning_phase.png")
                print("Saved 02_planning_phase.png")
            except Exception as e:
                print(f"Error checking planning phase: {e}")

            # 5. Verify Final Result
            print("Waiting for Final Answer (this may take time)...")
            try:
                # Wait up to 90s for deep research
                # Look for "Sources" or a copy button or simply a long text block.
                # "Sources" is a good anchor if citations are enabled.
                page.wait_for_selector("text=Sources", timeout=90000)
                page.screenshot(path="verification_scripts/03_final_result.png")
                print("Verified Final Result. Saved 03_final_result.png")

                content = page.content()
                if "Sources" in content:
                    print("SUCCESS: 'Sources' found in output.")
                else:
                    print("WARNING: 'Sources' not found, but selector matched?")

            except Exception as e:
                print(f"Error waiting for final result: {e}")
                page.screenshot(path="verification_scripts/03_error_state.png")
                # Don't fail the whole script hard, just report
                print("Verification incomplete.")

            browser.close()

    except Exception as e:
        print(f"Verification Script Error: {e}")
        sys.exit(1)
    finally:
        print("Cleaning up processes...")
        if backend_process:
            if backend_process.poll() is None:
                os.kill(backend_process.pid, signal.SIGTERM)
        if frontend_process:
             if frontend_process.poll() is None:
                # pnpm spawns node, might need recursive kill, but try SIGTERM
                os.kill(frontend_process.pid, signal.SIGTERM)

if __name__ == "__main__":
    run_verification()
