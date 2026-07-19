#!/usr/bin/env python3
"""Jules PR Context Aggregator for gemini-fullstack-langgraph-quickstart
Extracts comprehensive PR context (comments, CI, conflicts, diff size) to inform Jules recovery prompts.
Requires `gh` CLI to be authenticated.
Usage:
    python jules_pr_context.py <PR_NUMBER>
    python jules_pr_context.py 346 --json
"""

import argparse
import json
import subprocess
import sys

REPO = "MasumRab/gemini-fullstack-langgraph-quickstart"


def run_gh_cmd(args):
    """Run a gh command and return stdout."""
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True, text=True, timeout=30
        )
    except subprocess.TimeoutExpired:
        print("Error: gh command timed out after 30s")
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()
def main():
    parser = argparse.ArgumentParser(
        description="Extract comprehensive PR context for Jules recovery."
    )
    parser.add_argument("pr_number", help="The PR number")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    print(f"Fetching context for PR #{args.pr_number}...")

    pr_info_str = run_gh_cmd([
        "pr", "view", args.pr_number, "--repo", REPO,
        "--json", "number,title,state,mergeable,mergeStateStatus,additions,deletions,changedFiles,url,headRefName,baseRefName"
    ])
    if not pr_info_str:
        print(f"Error: Could not fetch PR #{args.pr_number}")
        sys.exit(1)

    pr_info = json.loads(pr_info_str)
    checks = run_gh_cmd(["pr", "checks", args.pr_number, "--repo", REPO])
    comments = run_gh_cmd(["pr", "view", args.pr_number, "--repo", REPO, "--json", "comments"])

    if args.json:
        print(json.dumps({"pr_info": pr_info, "checks": checks, "comments": comments}, indent=2))
        return

    print("\n" + "=" * 60)
    print("PR CONTEXT SUMMARY")
    print("=" * 60)

    print(f"\n[PR INFO]")
    print(f"Title: {pr_info.get('title')}")
    print(f"Branch: {pr_info.get('headRefName')}")
    print(f"Base: {pr_info.get('baseRefName')}")
    print(f"State: {pr_info.get('state')}")
    print(f"Mergeable: {pr_info.get('mergeable')}")
    print(f"Files Changed: {pr_info.get('changedFiles')}")
    print(f"Additions: +{pr_info.get('additions')} | Deletions: -{pr_info.get('deletions')}")

    print(f"\n[CI CHECKS]")
    if checks:
        print(checks)
    else:
        print("No CI checks or all passing")

    print(f"\n[URL]")
    print(f"https://github.com/{REPO}/pull/{args.pr_number}")


if __name__ == "__main__":
    main()