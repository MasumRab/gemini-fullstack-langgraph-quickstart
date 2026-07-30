#!/usr/bin/env python3
"""Jules Session Manager - CLI tool to manage Jules sessions via REST API.
Usage:
    python .kilo/commands/jules-manager.py list [pageSize]
    python .kilo/commands/jules-manager.py session SESSION_ID
    python .kilo/commands/jules-manager.py send SESSION_ID "Your message"
    python .kilo/commands/jules-manager.py approve SESSION_ID
"""

import os
import sys
import json

try:
    import requests
except ImportError:
    print("Error: 'requests' library not installed. Run: pip install requests")
    sys.exit(1)

API_BASE = "https://jules.googleapis.com/v1alpha"
API_KEY = os.environ.get("JULES_API_KEY")

if not API_KEY:
    print("Error: JULES_API_KEY not set. Generate at https://jules.google.com/settings#api")
    sys.exit(1)

HEADERS = {"x-goog-api-key": API_KEY, "Content-Type": "application/json"}


def api_call(path, method="GET", data=None):
    url = f"{API_BASE}/{path}"
    try:
        response = requests.request(method, url, headers=HEADERS, json=data, timeout=30)
    except requests.exceptions.Timeout:
        print("Error: API request timed out after 30s")
        sys.exit(1)
    if not response.ok:
        print(f"API Error ({response.status_code}): {response.text}")
        sys.exit(1)
    try:
        return response.json()
    except (json.JSONDecodeError, ValueError):
        print(f"Error: API returned non-JSON response: {response.text[:200]}")
        sys.exit(1)

def cmd_list(page_size=20):
    try:
        data = api_call(f"sessions?pageSize={page_size}")
        for session in data.get("sessions", []):
            pr_url = ""
            for output in session.get("outputs", []):
                if "pullRequest" in output:
                    pr_url = output["pullRequest"].get("url", "")
            print(f"{session['name']}: {session['state']}")
            if pr_url:
                print(f"  PR: {pr_url}")
    except Exception as e:
        print(f"Error: {e}")


def cmd_session(session_id):
    if not session_id.startswith("sessions/"):
        session_id = f"sessions/{session_id}"
    try:
        data = api_call(session_id)
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")


def cmd_send(session_id, message):
    if not session_id.startswith("sessions/"):
        session_id = f"sessions/{session_id}"
    try:
        api_call(f"{session_id}:sendMessage", method="POST", data={"prompt": message})
        print("Message sent")
    except Exception as e:
        print(f"Error: {e}")


def cmd_approve(session_id):
    if not session_id.startswith("sessions/"):
        session_id = f"sessions/{session_id}"
    try:
        api_call(f"{session_id}:approvePlan", method="POST", data={})
        print("Plan approved")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: jules-manager.py <list|session|send|approve> [args]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list":
        if len(sys.argv) > 2:
            try:
                page_size = int(sys.argv[2])
                if page_size <= 0:
                    print(f"Error: pageSize must be positive, got {page_size}")
                    sys.exit(1)
                cmd_list(page_size)
            except ValueError:
                print(f"Error: pageSize must be a number, got '{sys.argv[2]}'")
                sys.exit(1)
        else:
            cmd_list()
    elif cmd == "session" and len(sys.argv) > 2:
        cmd_session(sys.argv[2])
    elif cmd == "send" and len(sys.argv) > 3:
        cmd_send(sys.argv[2], sys.argv[3])
    elif cmd == "approve" and len(sys.argv) > 2:
        cmd_approve(sys.argv[2])
    else:
        print(f"Unknown command or missing args: {cmd}")
        sys.exit(1)