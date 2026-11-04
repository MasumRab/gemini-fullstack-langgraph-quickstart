#!/usr/bin/env python3
"""
Post @jules feedback comments to PRs for sessions awaiting user feedback.

Usage:
    export GITHUB_TOKEN=ghp_xxx
    python -m tools.sessions.post_pr_feedback --session 14823980629961743161
    python -m tools.sessions.post_pr_feedback --all-awaiting
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.store.jules_store import JulesSessionStore


def get_github_token() -> str:
    """Get GitHub token from environment."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN or GH_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)
    return token


def get_pr_info_from_session(session: Dict) -> Optional[Dict]:
    """Extract PR info from session data."""
    pr_url = session.get("pr_url", "")
    if not pr_url or pr_url == "N/A":
        return None
    
    # Parse: https://github.com/owner/repo/pull/123
    import re
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url)
    if not match:
        return None
    
    return {
        "owner": match.group(1),
        "repo": match.group(2),
        "number": int(match.group(3)),
        "url": pr_url,
    }


def get_session_context(store: JulesSessionStore, session_id: str) -> Dict:
    """Get full context for a session including activities."""
    session = store.get_session(session_id)
    if not session:
        return {}
    
    activities = []
    sid = session_id.replace("sessions/", "")
    with store._conn() as conn:
        rows = conn.execute(
            "SELECT * FROM activities WHERE session_id=? ORDER BY create_time ASC",
            (sid,)
        ).fetchall()
        activities = [dict(r) for r in rows]
    
    # Get latest agent message
    latest_agent_msg = None
    latest_user_msg = None
    for a in reversed(activities):
        if a.get("activity_type") == "agentMessaged" and not latest_agent_msg:
            latest_agent_msg = a.get("summary", "")
        if a.get("activity_type") == "userMessaged" and not latest_user_msg:
            latest_user_msg = a.get("summary", "")
        if latest_agent_msg and latest_user_msg:
            break
    
    return {
        "session": session,
        "activities": activities,
        "latest_agent_message": latest_agent_msg,
        "latest_user_message": latest_user_msg,
        "activity_count": len(activities),
    }


def generate_feedback_comment(session_id: str, context: Dict) -> str:
    """Generate a @jules comment with context summary and recommended action."""
    session = context.get("session", {})
    title = session.get("title", "Unknown")
    state = session.get("state", "UNKNOWN")
    repo = session.get("repo", "")
    activity_count = context.get("activity_count", 0)
    latest_agent = context.get("latest_agent_message") or ""
    latest_user = context.get("latest_user_message") or ""
    
    # Determine what the agent needs
    state_lower = state.lower()
    if "plan_approval" in state_lower:
        action = "Please review the generated plan and reply with **@jules approve** to proceed, or provide guidance on changes needed."
        category = "Plan Approval Needed"
    elif "user_feedback" in state_lower:
        if "select" in latest_agent.lower() and ("pr" in latest_agent.lower() or "pull request" in latest_agent.lower()):
            action = "Agent needs guidance on which PR to work on. Reply with **@jules work on PR #XXX** or specify selection criteria."
            category = "PR Selection Needed"
        elif latest_agent.strip().endswith("?"):
            action = f"Agent asked: *{latest_agent[:200]}* Reply with **@jules** followed by your answer."
            category = "Question Pending"
        else:
            action = "Agent is awaiting feedback. Reply with **@jules** followed by your guidance (e.g., 'proceed with the fix', 'focus on X instead', 'create PR')."
            category = "Feedback Needed"
    elif "paused" in state_lower:
        action = "Session is paused. Reply with **@jules resume** to continue, or provide new guidance."
        category = "Paused"
    elif "failed" in state_lower:
        action = "Session failed. Reply with **@jules retry** to attempt again, or **@jules investigate** for details."
        category = "Failed"
    else:
        action = "Reply with **@jules** followed by your instructions."
        category = "Awaiting Input"
    
    # Build the comment
    comment = f"""## 🤖 Jules Session Feedback

**Session:** `{session_id}`
**Title:** {title}
**State:** {state}
**Repository:** {repo}
**Activities:** {activity_count}

### Context Summary
{category}

**Latest agent message:**
> {latest_agent[:500] if latest_agent else "*No agent message in local store*"}

**Latest user message:**
> {latest_user[:300] if latest_user else "*No user message in local store*"}

### Recommended Action
{action}

---
*This comment was generated from the local Jules session store. Reply with `@jules <your message>` to send guidance to the agent.*
"""
    return comment


def post_pr_comment(owner: str, repo: str, pr_number: int, body: str, token: str) -> bool:
    """Post a comment to a GitHub PR."""
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = {"body": body}
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        print(f"  ✅ Posted comment to {owner}/{repo}#{pr_number}")
        return True
    else:
        print(f"  ❌ Failed to post comment: {response.status_code} - {response.text}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Post @jules feedback to PRs for awaiting sessions")
    parser.add_argument("--session", help="Specific session ID to process")
    parser.add_argument("--all-awaiting", action="store_true", help="Process all sessions awaiting feedback")
    parser.add_argument("--dry-run", action="store_true", help="Show comments without posting")
    parser.add_argument("--list", action="store_true", help="List sessions with PRs awaiting feedback")
    args = parser.parse_args()
    
    store = JulesSessionStore()
    
    # Get sessions with PRs in awaiting states
    awaiting_states = ["AWAITING_USER_FEEDBACK", "AWAITING_PLAN_APPROVAL", "PAUSED"]
    sessions_with_prs = []
    
    for state in awaiting_states:
        sessions = store.list_sessions(state=state, limit=100)
        for s in sessions:
            pr_info = get_pr_info_from_session(s)
            if pr_info:
                sessions_with_prs.append((s, pr_info))
    
    if args.list:
        print(f"\n{'Session ID':<22} {'State':<28} {'PR':<10} {'Repo':<35} Title")
        print("-" * 110)
        for session, pr_info in sessions_with_prs:
            session_id = session.get("session_id", "")[:21]
            state = session.get("state", "")[:27]
            pr_str = f"#{pr_info['number']}"
            repo = pr_info['repo'][:34]
            title = session.get("title", "")[:40]
            print(f"{session_id:<22} {state:<28} {pr_str:<10} {repo:<35} {title}")
        return
    
    if not sessions_with_prs:
        print("No sessions with PRs in awaiting states.")
        return
    
    # Filter to specific session if requested
    if args.session:
        sessions_with_prs = [(s, p) for s, p in sessions_with_prs if s.get("session_id") == args.session]
        if not sessions_with_prs:
            print(f"Session {args.session} not found or has no PR.")
            return
    
    token = get_github_token() if not args.dry_run else ""
    
    for session, pr_info in sessions_with_prs:
        session_id = session.get("session_id", "")
        print(f"\n📋 Processing {session_id} -> {pr_info['owner']}/{pr_info['repo']}#{pr_info['number']}")
        
        context = get_session_context(store, session_id)
        comment = generate_feedback_comment(session_id, context)
        
        if args.dry_run:
            print("--- DRY RUN: Comment preview ---")
            print(comment)
            print("--- End preview ---")
        else:
            success = post_pr_comment(
                pr_info["owner"], pr_info["repo"], pr_info["number"], comment, token
            )
            if success:
                # Optionally store a note in the local DB
                store.set_notes(session_id, f"PR feedback posted to #{pr_info['number']} at {pr_info['url']}")


if __name__ == "__main__":
    main()