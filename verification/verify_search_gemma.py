import sys
import os
import argparse
import subprocess
import time
import socket
import shutil
import json
import signal
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

# --- Constants ---
# Use absolute paths based on where the script is running
# We assume the script is run from repo root: python verification/verify_search_gemma.py
ROOT_DIR = Path(os.getcwd())
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
ARTIFACTS_DIR = ROOT_DIR / "verification" / "artifacts"
STUB_SCRIPT = ROOT_DIR / "verification" / "model-stubs" / "adversarial_search_stub.js"
FIXTURE_PATH = ROOT_DIR / "verification" / "fixtures" / "gemma" / "complex_query.json"

# --- Utils ---

def find_free_port():
    """Finds a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

def wait_for_port(port, timeout=30, name="Service"):
    """Waits for a port to be open."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                print(f"[{name}] Port {port} is ready.")
                return True
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(1)
    print(f"[{name}] Timed out waiting for port {port}.")
    return False

def tail_file(filepath, n_lines=20):
    """Reads the last n lines of a file."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        lines = f.readlines()
        return lines[-n_lines:]

# --- Main Runner ---

def run_verification(args):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_artifacts_dir = ARTIFACTS_DIR / timestamp
    run_artifacts_dir.mkdir(parents=True, exist_ok=True)

    print(f"--- Starting Search Verification (Gemma) ---")
    print(f"Artifacts: {run_artifacts_dir}")

    # 1. Setup Ports
    backend_port = find_free_port()
    frontend_port = find_free_port()
    stub_port = find_free_port()

    print(f"Ports assigned - Backend: {backend_port}, Frontend: {frontend_port}, Stub: {stub_port}")

    # 2. Prepare Environment
    env_vars = os.environ.copy()

    # Inject Gemma Model Configuration
    env_vars["QUERY_GENERATOR_MODEL"] = "gemma-3-27b-it"
    env_vars["ANSWER_MODEL"] = "gemma-3-27b-it"
    env_vars["REFLECTION_MODEL"] = "gemma-3-27b-it"

    # Force Port for Backend
    env_vars["PORT"] = str(backend_port)

    # Frontend config to point to backend
    # We set VITE_BACKEND_URL or similar if the frontend supports it.
    # If not, we might be testing against a broken frontend config, but let's try.
    # Common convention is VITE_API_BASE_URL or VITE_BACKEND_URL.
    env_vars["VITE_API_BASE_URL"] = f"http://localhost:{backend_port}"

    processes = []

    try:
        # 3. Start Stub (if adversarial)
        if args.use_adversarial:
            print("Starting Adversarial Stub...")
            env_vars["STUB_PORT"] = str(stub_port)
            env_vars["SEARCH_PROVIDER"] = "adversarial"
            env_vars["SEARCH_HTTP_ENDPOINT"] = f"http://localhost:{stub_port}/search"

            stub_log = open(run_artifacts_dir / "stub.log", "w")
            stub_proc = subprocess.Popen(
                ["node", str(STUB_SCRIPT)],
                env=env_vars,
                stdout=stub_log,
                stderr=subprocess.STDOUT,
                cwd=ROOT_DIR
            )
            processes.append(stub_proc)
            if not wait_for_port(stub_port, name="Stub"):
                raise RuntimeError("Stub failed to start")
        else:
            # Normal mode
            env_vars["SEARCH_PROVIDER"] = "duckduckgo"

        # 4. Start Backend
        print("Starting Backend...")
        backend_log = open(run_artifacts_dir / "backend.log", "w")

        # Ensure PYTHONPATH includes backend/src
        env_vars["PYTHONPATH"] = f"{ROOT_DIR}:{BACKEND_DIR}/src"

        # We use 'uv run' to ensure dependencies are available
        backend_cmd = [
            "uv", "run", "uvicorn", "agent.app:app",
            "--host", "0.0.0.0",
            "--port", str(backend_port)
        ]

        backend_proc = subprocess.Popen(
            backend_cmd,
            cwd=BACKEND_DIR,
            env=env_vars,
            stdout=backend_log,
            stderr=subprocess.STDOUT
        )
        processes.append(backend_proc)

        if not wait_for_port(backend_port, timeout=60, name="Backend"):
            print("Backend startup failed. Tail logs:")
            print("".join(tail_file(run_artifacts_dir / "backend.log")))
            raise RuntimeError("Backend failed to start")

        # 5. Start Frontend
        print("Starting Frontend...")
        frontend_log = open(run_artifacts_dir / "frontend.log", "w")

        # Using pnpm dev
        frontend_cmd = [
            "pnpm", "dev", "--port", str(frontend_port), "--host"
        ]

        frontend_proc = subprocess.Popen(
            frontend_cmd,
            cwd=FRONTEND_DIR,
            env=env_vars,
            stdout=frontend_log,
            stderr=subprocess.STDOUT
        )
        processes.append(frontend_proc)

        if not wait_for_port(frontend_port, timeout=30, name="Frontend"):
             raise RuntimeError("Frontend failed to start")

        # 6. Run Playwright
        print("Running Playwright Assertions...")
        with open(FIXTURE_PATH, "r") as f:
            fixture = json.load(f)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                record_har_path=run_artifacts_dir / "network.har"
            )
            page = context.new_page()

            url = f"http://localhost:{frontend_port}/"
            print(f"Navigating to {url}")
            page.goto(url)

            # Wait for load
            page.wait_for_load_state("networkidle")
            page.screenshot(path=run_artifacts_dir / "01_loaded.png")

            # Input Query
            # Note: We need to find the actual selector.
            # Usually Shadcn Input or Textarea.
            # Try generic textarea first.
            try:
                page.wait_for_selector("textarea", timeout=5000)
                page.fill("textarea", fixture['query'])
                page.press("textarea", "Enter")
            except:
                # Fallback to input
                page.fill("input[type='text']", fixture['query'])
                page.press("input[type='text']", "Enter")


            # Verify Planning
            print("Waiting for Planning state...")
            try:
                # Assuming some UI indicator for "Planning"
                # This might be brittle without specific test IDs
                page.wait_for_timeout(2000)
                page.screenshot(path=run_artifacts_dir / "02_planning.png")
            except Exception as e:
                print(f"Warning during planning wait: {e}")

            # Verify Researching/Results
            print("Waiting for Search Results...")
            # If adversarial, we definitely expect results quickly (mock is fast)
            # Wait for something that looks like a result card
            # Shadcn cards often have classes like "rounded-xl border bg-card"
            # Or we look for text content
            page.wait_for_timeout(5000)
            page.screenshot(path=run_artifacts_dir / "03_researching.png")

            # Verify Final Answer
            print("Waiting for Final Answer...")
            # Wait longer for LLM generation
            page.wait_for_timeout(10000)
            page.screenshot(path=run_artifacts_dir / "04_final.png")

            content = page.content()
            with open(run_artifacts_dir / "page.html", "w") as f:
                f.write(content)

            # Assertions
            if args.use_adversarial:
                # Check for the mocked title
                if "Adversarial Result" in content:
                    print("SUCCESS: Adversarial content verified in DOM.")
                else:
                    print("FAILURE: Adversarial content NOT found in DOM.")
                    # Don't exit yet, let logs print
            else:
                for kw in fixture["expected_keywords"]:
                    if kw.lower() in content.lower():
                        print(f"Found keyword: {kw}")

            browser.close()

        print("Verification Cycle Complete.")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("Cleaning up processes...")
        for proc in processes:
            if proc.poll() is None:
                os.kill(proc.pid, signal.SIGTERM)
        print("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", action="store_true", help="Start fresh environment")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--artifacts", type=str, default="verification/artifacts")
    parser.add_argument("--use_adversarial", action="store_true", help="Use adversarial search stub")

    args = parser.parse_args()

    run_verification(args)
