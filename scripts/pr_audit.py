#!/usr/bin/env python3
"""
PR Audit Script - Systematically check PRs #236-#274 for:
- CI status
- Merge conflicts
- Comments requiring action
- Draft status
"""

import subprocess
import json
import sys
from pathlib import Path

# PR range to audit
PR_START = 236
PR_END = 274

def run_gh_command(args: list) -> dict | None:
    """Run a gh CLI command and return JSON output."""
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        return None
    except Exception as e:
        print(f"Error running gh command: {e}")
        return None

def get_pr_details(pr_number: int) -> dict | None:
    """Get detailed PR information."""
    return run_gh_command([
        "pr", "view", str(pr_number),
        "--json", "number,title,state,mergeable,mergeStateStatus,"
                  "statusCheckRollup,comments,reviewDecision,url,isDraft,headRefName,baseRefName"
    ])

def analyze_pr(pr: dict) -> dict:
    """Analyze a PR and return summary."""
    analysis = {
        "number": pr.get("number"),
        "title": pr.get("title"),
        "url": pr.get("url"),
        "state": pr.get("state"),
        "is_draft": pr.get("isDraft", False),
        "mergeable": pr.get("mergeable", "UNKNOWN"),
        "merge_state": pr.get("mergeStateStatus", "UNKNOWN"),
        "review_decision": pr.get("reviewDecision", "NONE"),
        "ci_status": "UNKNOWN",
        "ci_failures": [],
        "actionable_comments": [],
        "needs_attention": False,
        "attention_reasons": []
    }
    
    # Check CI status
    status_rollup = pr.get("statusCheckRollup", [])
    if status_rollup:
        failures = [c for c in status_rollup if c.get("state") in ["FAILURE", "ERROR", "TIMED_OUT"]]
        successes = [c for c in status_rollup if c.get("state") == "SUCCESS"]
        
        if failures:
            analysis["ci_status"] = "FAILURE"
            analysis["ci_failures"] = [
                {"context": f.get("context"), "state": f.get("state")}
                for f in failures
            ]
            analysis["needs_attention"] = True
            analysis["attention_reasons"].append("CI failures detected")
        elif successes and len(successes) == len(status_rollup):
            analysis["ci_status"] = "SUCCESS"
        else:
            analysis["ci_status"] = "PENDING"
            analysis["needs_attention"] = True
            analysis["attention_reasons"].append("CI pending")
    else:
        analysis["ci_status"] = "NO_CHECKS"
        analysis["needs_attention"] = True
        analysis["attention_reasons"].append("No CI checks configured")
    
    # Check mergeability
    if analysis["mergeable"] == "CONFLICTING":
        analysis["needs_attention"] = True
        analysis["attention_reasons"].append("Merge conflicts detected")
    elif analysis["mergeable"] == "UNKNOWN":
        analysis["needs_attention"] = True
        analysis["attention_reasons"].append("Mergeability unknown")
    
    # Check comments for actionable items
    comments = pr.get("comments", [])
    for comment in comments:
        author = comment.get("author", {}).get("login", "")
        body = comment.get("body", "")
        
        # Look for actionable comments
        is_owner_request = comment.get("authorAssociation") == "OWNER"
        has_jules_mention = "@jules" in body.lower()
        has_action_words = any(word in body.lower() for word in 
                              ["fix", "update", "change", "resolve", "please", "need"])
        
        if is_owner_request and (has_jules_mention or has_action_words):
            analysis["actionable_comments"].append({
                "author": author,
                "body": body[:200] + "..." if len(body) > 200 else body,
                "created": comment.get("createdAt")
            })
    
    if analysis["actionable_comments"]:
        analysis["needs_attention"] = True
        analysis["attention_reasons"].append("Actionable comments present")
    
    # Draft status
    if analysis["is_draft"]:
        analysis["attention_reasons"].append("Draft PR")
    
    return analysis

def main():
    """Main audit function."""
    print("=" * 80)
    print(f"PR AUDIT REPORT: #{PR_START} - #{PR_END}")
    print("=" * 80)
    print()
    
    results = []
    
    for pr_num in range(PR_START, PR_END + 1):
        print(f"Checking PR #{pr_num}...", end=" ", flush=True)
        pr_data = get_pr_details(pr_num)
        
        if pr_data is None:
            print("NOT FOUND or ERROR")
            continue
        
        analysis = analyze_pr(pr_data)
        results.append(analysis)
        
        status_icon = "✅" if not analysis["needs_attention"] else "⚠️"
        draft_icon = "📝" if analysis["is_draft"] else ""
        print(f"{status_icon} {analysis['state']} {draft_icon}")
    
    print()
    print("=" * 80)
    print("PRs REQUIRING ATTENTION")
    print("=" * 80)
    
    needs_attention = [r for r in results if r["needs_attention"]]
    
    for pr in sorted(needs_attention, key=lambda x: x["number"]):
        print(f"\n### PR #{pr['number']}: {pr['title']}")
        print(f"URL: {pr['url']}")
        print(f"State: {pr['state']} {'(DRAFT)' if pr['is_draft'] else ''}")
        print(f"Mergeable: {pr['mergeable']} ({pr['merge_state']})")
        print(f"CI Status: {pr['ci_status']}")
        
        if pr['ci_failures']:
            print("CI Failures:")
            for f in pr['ci_failures']:
                print(f"  - {f['context']}: {f['state']}")
        
        if pr['actionable_comments']:
            print("Actionable Comments:")
            for c in pr['actionable_comments']:
                print(f"  - [{c['author']}]: {c['body'][:100]}...")
        
        print(f"Attention Reasons: {', '.join(pr['attention_reasons'])}")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total PRs checked: {len(results)}")
    print(f"PRs needing attention: {len(needs_attention)}")
    print(f"PRs in good state: {len(results) - len(needs_attention)}")
    
    # Categorize
    conflicts = [r for r in needs_attention if r['mergeable'] == 'CONFLICTING']
    ci_failures = [r for r in needs_attention if r['ci_status'] == 'FAILURE']
    drafts = [r for r in results if r['is_draft']]
    
    print(f"\nBreakdown:")
    print(f"  - Merge conflicts: {len(conflicts)} ({[r['number'] for r in conflicts]})")
    print(f"  - CI failures: {len(ci_failures)} ({[r['number'] for r in ci_failures]})")
    print(f"  - Draft PRs: {len(drafts)} ({[r['number'] for r in drafts]})")
    
    # Save detailed results
    output_file = Path(__file__).parent.parent / "reports" / "pr_audit_detailed.json"
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to: {output_file}")

if __name__ == "__main__":
    main()