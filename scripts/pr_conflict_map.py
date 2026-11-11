#!/usr/bin/env python3
"""
PR Conflict Map Generator - fast version
Usage: python pr_conflict_map.py --report
"""

import json
import subprocess
import sys
from collections import defaultdict

OUTPUT_FILE = "docs/pr_analysis/PR_CONFLICT_MAP.md"


def main():
    # Get open PRs
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--repo", "MasumRab/gemini-fullstack-langgraph-quickstart",
             "--state", "open", "--json", "number,title,headRefName,mergeable,additions,deletions,changedFiles"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            print(f"Error: gh command failed: {result.stderr}")
            sys.exit(1)
        prs = json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        print("Error: gh command timed out after 60s")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        sys.exit(1)

    mergeable = [p for p in prs if p.get("mergeable") == "MERGEABLE"]
    conflicting = [p for p in prs if p.get("mergeable") == "CONFLICTING"]

    lines = [
        "# PR Conflict Map & Merge Order",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|--------|-------|",
        f"| MERGEABLE | {len(mergeable)} |",
        f"| CONFLICTING | {len(conflicting)} |",
        "",
        "## Mergeable PRs (Ready to merge)",
        "",
    ]
    for p in sorted(mergeable, key=lambda x: x["number"]):
        lines.append(f"- PR #{p['number']}: `{p['headRefName']}` (+{p['additions']} -{p['deletions']}, {p['changedFiles']} files)")

    lines.extend([
        "",
        "## Conflicting PRs (Need resolution)",
        "",
    ])
    for p in sorted(conflicting, key=lambda x: -x["additions"]):
        lines.append(f"- PR #{p['number']}: `{p['headRefName']}` (+{p['additions']} -{p['deletions']}, {p['changedFiles']} files)")

    lines.extend([
        "",
        "## Merge Order Recommendation",
        "",
        "1. Merge clean PRs first (#349, #350, #353, #356, #364, #365, #368, #369, #370, #371, #372)",
        "2. Resolve large conflicting PRs (#346, #347) - require careful review",
        "3. Address smaller conflicting PRs in priority order (sentinel/bolt > antigravity/fix > others)",
    ])

    # Write report
    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
