---
name: jules-api
description: Reference and guidance for using the Jules REST API (v1alpha) to create sessions, manage activities, and interact with Jules through code.
---

# Jules API Skill

## Overview

This skill provides comprehensive documentation for interacting with the Jules REST API (v1alpha). Use it to automate coding tasks, build custom integrations, or programmatically manage Jules sessions.

## Quick Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/sessions` | POST | Create a new session |
| `/sessions` | GET | List recent sessions |
| `/sessions/{sessionId}` | GET | Get session details (includes PR URLs) |
| `/sessions/{sessionId}:sendMessage` | POST | Send message to unblock agent |
| `/sessions/{sessionId}:approvePlan` | POST | Approve pending plan |
| `/sessions/{sessionId}/activities` | GET | Get session chat history |

## Authentication

All requests require API key in `x-goog-api-key` header. Generate at: https://jules.google.com/settings#api

```bash
export JULES_API_KEY="your-key-here"
```

## Session States

| State | Description | Action |
|-------|-------------|--------|
| `QUEUED` | Waiting to be processed | Wait |
| `PLANNING` | Creating plan | Wait |
| `AWAITING_PLAN_APPROVAL` | Plan ready, needs approval | Call `approvePlan` |
| `AWAITING_USER_FEEDBACK` | Needs input | Call `sendMessage` |
| `IN_PROGRESS` | Actively working | Monitor via activities |
| `PAUSED` | Session paused | Check activities |
| `COMPLETED` | Task done | Check for PR |
| `FAILED` | Task failed | Review activities for error |

## Python Usage Pattern

```python
import os, requests

API_KEY = os.environ.get("JULES_API_KEY")
HEADERS = {"x-goog-api-key": API_KEY, "Content-Type": "application/json"}

# List sessions
r = requests.get("https://jules.googleapis.com/v1alpha/sessions?pageSize=20", headers=HEADERS)

# Get session (use name format: sessions/12345)
r = requests.get("https://jules.googleapis.com/v1alpha/sessions/abc123", headers=HEADERS)

# Send message
requests.post("https://jules.googleapis.com/v1alpha/sessions/abc123:sendMessage",
    headers=HEADERS, json={"prompt": "Your message"})

# Approve plan
requests.post("https://jules.googleapis.com/v1alpha/sessions/abc123:approvePlan",
    headers=HEADERS, json={})
```

## Finding PR from Session

Session outputs contain `pullRequest.url`:
```python
session = get_session("sessions/abc123")
for output in session.get("outputs", []):
    pr_url = output.get("pullRequest", {}).get("url")
    if pr_url:
        print(f"PR: {pr_url}")
```

## Reference Documentation
- [quickstart.md](references/quickstart.md) - Getting started guide
- [sessions.md](references/sessions.md) - Session management
- [activities.md](references/activities.md) - Activity log access
- [authentication.md](references/authentication.md) - Auth setup
- [overview.md](references/overview.md) - API concepts
- [sources.md](references/sources.md) - Repository sources
- [types.md](references/types.md) - Data models