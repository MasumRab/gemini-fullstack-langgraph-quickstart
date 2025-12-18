#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import signal
import requests
import shutil
import json
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

# Config (override with env vars)
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8123"))
FRONTEND_PORT = int(os.environ.get("FRONTEND_PORT", "5173"))
BACKEND_URL = f"http://localhost:{BACKEND_PORT}"
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"
CHECK_INTERVAL = float(os.environ.get("CHECK_INTERVAL", "1"))
TIMEOUT = int(os.environ.get("TIMEOUT", "60"))
GEMMA_MODEL = os.environ.get("VERIFICATION_MODEL", "gemma-3-27b-it")
ARTIFACT_DIR = Path(os.environ.get("ARTIFACT_DIR", "verification/artifacts")) / datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

# Prepare env
ENV_VARS = os.environ.copy()
REPO_ROOT = Path.cwd()
BACKEND_SRC = REPO_ROOT / "backend" / "src"
ENV_VARS["PYTHONPATH"] = f"{REPO_ROOT}:{BACKEND_SRC}:{ENV_VARS.get('PYTHONPATH','')}"
ENV_VARS.update({
    "QUERY_MODEL": GEMMA_MODEL,
    "REFLECTION_MODEL": GEMMA_MODEL,
    "ANSWER_MODEL": GEMMA_MODEL,
    "VALIDATION_MODEL": GEMMA_MODEL,
    "COMPRESSION_MODEL": GEMMA_MODEL,
    "SCOPING_MODEL": GEMMA_MODEL,
    "PLANNER_MODEL": GEMMA_MODEL,
    "OPTIMIZER_MODEL": GEMMA_MODEL,
    "MCP_ENABLED": "false",
    "VITE_API_URL": BACKEND_URL,
})

def wait_for_service(url, name, timeout=TIMEOUT):
    print(f"[wait] Waiting for {name} at {url} (timeout={timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                print(f"[wait] {name} is up")
                return True
        except requests.RequestException:
            pass
        time.sleep(CHECK_INTERVAL)
    print(f"[wait] Timeout waiting for {name}")
    return False

def write_stream_to_file(stream, path):
    try:
        with open(path, "w", encoding="utf-8") as f:
            if stream:
                f.write(stream.read())
    except Exception as e:
        print(f"[log] Failed to write stream to {path}: {e}")

def start_process(cmd, cwd, env, stdout_path, stderr_path):
    # Start in new process group so we can kill children
    with open(stdout_path, "w", encoding="utf-8") as out, open(stderr_path, "w", encoding="utf-8") as err:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=env,
            stdout=out,
            stderr=err,
            preexec_fn=os.setsid
        )
    return proc

def kill_process_group(proc):
    try:
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, signal.SIGTERM)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass

def run_verification():
    backend_proc = None
    frontend_proc = None
    exit_code = 0

    try:
        # Backend
        print("[run] Starting backend (langgraph_cli dev)...")
        backend_stdout = ARTIFACT_DIR / "backend.stdout.log"
        backend_stderr = ARTIFACT_DIR / "backend.stderr.log"
        # Use python -m langgraph_cli dev to run the standard server
        backend_cmd = [sys.executable, "-m", "langgraph_cli", "dev", "--host", "0.0.0.0", "--port", str(BACKEND_PORT), "--no-browser"]
        backend_proc = start_process(backend_cmd, cwd=REPO_ROOT / "backend", env=ENV_VARS, stdout_path=backend_stdout, stderr_path=backend_stderr)

        if not wait_for_service(f"{BACKEND_URL}/ok", "Backend", timeout=TIMEOUT):
            print("[error] Backend failed to start; see logs")
            exit_code = 2
            return exit_code

        # Frontend
        print("[run] Starting frontend (pnpm dev)...")
        frontend_stdout = ARTIFACT_DIR / "frontend.stdout.log"
        frontend_stderr = ARTIFACT_DIR / "frontend.stderr.log"
        if not shutil.which("pnpm"):
            print("[error] pnpm not found in PATH")
            exit_code = 3
            return exit_code

        frontend_proc = start_process(["pnpm", "dev", "--port", str(FRONTEND_PORT)], cwd=REPO_ROOT / "frontend", env=ENV_VARS, stdout_path=frontend_stdout, stderr_path=frontend_stderr)

        if not wait_for_service(FRONTEND_URL, "Frontend", timeout=TIMEOUT):
            print("[error] Frontend failed to start; see logs")
            exit_code = 4
            return exit_code

        # Playwright
        print("[run] Running Playwright verification...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            har_path = str(ARTIFACT_DIR / "network.har")
            context = browser.new_context(record_har_path=har_path)
            page = context.new_page()

            console_errors = []
            def on_console(msg):
                if msg.type == "error":
                    console_errors.append(msg.text)
                # also write all console messages to file
                with open(ARTIFACT_DIR / "browser_console.log", "a", encoding="utf-8") as f:
                    f.write(f"[{msg.type}] {msg.text}\n")
            page.on("console", on_console)

            # Vite serves at /app/ base path
            target_url = f"{FRONTEND_URL}/app/" if not FRONTEND_URL.endswith("/app/") else FRONTEND_URL
            print(f"[run] Navigating to {target_url}")
            page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                print("[warn] networkidle timeout, continuing")

            page.screenshot(path=str(ARTIFACT_DIR / "01_initial_load.png"))

            # Input query robustly
            query = "Explain the architecture of Transformer models"
            print(f"[run] Entering query: {query}")
            locator = None
            # Prefer textarea or role=textbox
            for sel in ["textarea", "role=textarea", "role=textbox", "input[type='text']"]:
                try:
                    locator = page.locator(sel)
                    locator.wait_for(timeout=2000)
                    locator.fill(query)
                    break
                except Exception:
                    locator = None
            if locator is None:
                print("[error] No input element found to type query")
                exit_code = 5
                return exit_code

            # Submit: try button[type=submit], then Enter on the same locator
            try:
                btn = page.locator("button[type='submit']")
                btn.wait_for(timeout=2000)
                btn.click()
            except Exception:
                try:
                    locator.press("Enter")
                except Exception:
                    print("[warn] Could not submit query via button or Enter")

            page.screenshot(path=str(ARTIFACT_DIR / "02_after_submit.png"))

            # Wait for planning indicator or results
            print("[run] Waiting for planning or results...")
            # Try multiple anchors: "Planning", "Thinking", "Sources", result container
            anchors = ["text=Planning", "text=Thinking", "text=Sources", ".final-answer", ".results", ".agent-output"]
            found = False
            start = time.time()
            max_wait = int(os.environ.get("FINAL_WAIT", "90"))
            while time.time() - start < max_wait:
                for a in anchors:
                    try:
                        if page.locator(a).count() > 0:
                            found = True
                            break
                    except Exception:
                        pass
                if found:
                    break
                time.sleep(1)
            page.screenshot(path=str(ARTIFACT_DIR / "03_final_state.png"))

            if not found:
                print("[warn] No expected anchors found in final state")
                exit_code = 6
            else:
                print("[run] Found expected UI anchor")

            # Fail if console errors occurred
            if console_errors:
                print("[error] Browser console errors detected:")
                for e in console_errors:
                    print("  -", e)
                exit_code = 7

            # Save page HTML
            with open(ARTIFACT_DIR / "page.html", "w", encoding="utf-8") as f:
                f.write(page.content())

            context.close()
            browser.close()

    except Exception as e:
        print(f"[exception] {e}")
        exit_code = 1
    finally:
        print("[run] Cleaning up processes...")
        if frontend_proc and frontend_proc.poll() is None:
            try:
                kill_process_group(frontend_proc)
            except Exception:
                frontend_proc.kill()
        if backend_proc and backend_proc.poll() is None:
            try:
                kill_process_group(backend_proc)
            except Exception:
                backend_proc.kill()

        # Dump last logs for convenience
        for p in [ARTIFACT_DIR / "backend.stderr.log", ARTIFACT_DIR / "backend.stdout.log", ARTIFACT_DIR / "frontend.stderr.log", ARTIFACT_DIR / "frontend.stdout.log"]:
            if p.exists():
                print(f"[log] --- {p.name} ---")
                print(p.read_text(encoding="utf-8", errors="ignore")[:4000])

        print(f"[run] Artifacts saved to: {ARTIFACT_DIR}")
        return exit_code

if __name__ == "__main__":
    code = run_verification()
    sys.exit(code)
