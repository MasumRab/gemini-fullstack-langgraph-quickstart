#!/usr/bin/env python3
"""
Jules PR Triage for gemini-fullstack-langgraph-quickstart
Builds file overlap conflict map and recommends merge order.
Usage:
    python jules_pr_triage.py --repo MasumRab/gemini-fullstack-langgraph-quickstart --report
"""

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path("docs/pr_analysis/individual")
CONFLICT_REPORT = Path("docs/pr_analysis/PR_CONFLICT_MAP.md")


def run_gh_api(endpoint):
    """Run gh api and return parsed JSON."""
    result = subprocess.run(
        ["gh", "api", endpoint],
        capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout) if result.stdout.strip() else None


def get_all_open_prs(repo):
    """Fetch all open PRs for the repo."""
    result = subprocess.run(
        ["gh", "pr", "list", "--repo", repo, "--state", "open",
         "--json", "number,title,headRefName,mergeable,additions,deletions,changedFiles,url"],
        capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def get_pr_files(pr_num, repo):
    """Get list of files changed in a PR."""
    result = subprocess.run(
        ["gh", "pr", "view", str(pr_num), "--repo", repo, "--json", "files"],
        capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        return set()
    data = json.loads(result.stdout)
    return {f["path"] for f in data.get("files", [])}


def get_priority_branch(branch_name):
    """Determine priority based on branch naming convention."""
    if branch_name.startswith("sentinel/") or "security" in branch_name.lower():
        return 1  # CRITICAL
    if branch_name.startswith("bolt/") or "performance" in branch_name.lower() or "optimization" in branch_name.lower():
        return 2  # HIGH
    if branch_name.startswith("antigravity/") or branch_name.startswith("fix/") or "bug" in branch_name.lower():
        return 2  # HIGH
    if "test" in branch_name.lower() or "validation" in branch_name.lower():
        return 3  # MEDIUM
    return 4  # LOW


def build_overlap_map(prs, repo):
    """Build file overlap matrix between PRs."""
    pr_files = {}
    for pr in prs:
        pr_files[pr["number"]] = get_pr_files(pr["number"], repo)

    overlaps = {}
    for p1 in prs:
        for p2 in prs:
            if p1["number"] >= p2["number"]:
                continue
            p1_files = pr_files.get(p1["number"], set())
            p2_files = pr_files.get(p2["number"], set())
            overlap = p1_files & p2_files
            if overlap:
                overlaps[(p1["number"], p2["number"])] = len(overlap)

    return pr_files, overlaps


def generate_markdown_report(prs, pr_files, overlaps, repo):
    """Generate the conflict map markdown report."""
    lines = [
        "# PR Conflict Map & Merge Order",
        "",
        f"**Generated**: {datetime.now().isoformat()}",
        f"**Repository**: {repo}",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|--------|-------|",
    ]
    
    mergeable = sum(1 for p in prs if p.get("mergeable") == "MERGEABLE")
    conflicting = sum(1 for p in prs if p.get("mergeable") == "CONFLICTING")
    
    lines.extend([
        f"| MERGEABLE | {mergeable} |",
        f"| CONFLICTING | {conflicting} |",
    ])

    lines.extend([
        "",
        "## Merge Order Recommendation",
        "",
        "Ordered by: (priority) → (file count) → (overlap risk)",
        "",
    ])

    sorted_prs = sorted(prs, key=lambda p: (
        get_priority_branch(p["headRefName"]),
        p["changedFiles"]
    ))

    lines.append("| Order | PR # | Branch | Status | Files | +Lines | -Lines | Priority | Overlap Risk |")
    lines.append("|-------|------|--------|--------|-------|--------|--------|----------|------------|")

    for i, pr in enumerate(sorted_prs, 1):
        priority = get_priority_branch(pr["headRefName"])
        priority_label = ["", "CRITICAL", "HIGH", "MEDIUM", "LOW"][priority]
        
        overlap_count = sum(
            v for (a, b), v in overlaps.items() 
            if a == pr["number"] or b == pr["number"]
        )
        overlap_risk = "Low" if overlap_count == 0 else f"Med ({overlap_count})"

        status = pr.get("mergeable", "UNKNOWN")
        lines.append(
            f"| {i:<5} | {pr['number']:<4} | {pr['headRefName'][:25]:<25} | "
            f"{status:<10} | {pr.get('changedFiles', 0):<5} | {pr.get('additions', 0):<6} | "
            f"{pr.get('deletions', 0):<6} | {priority_label:<8} | {overlap_risk:<10} |"
        )

    lines.extend([
        "",
        "## High-Conflict PRs",
        "",
        "| PR # | Overlap Files | Other PRs |",
        "|------|---------------|-----------|",
    ])

    for (p1, p2), count in sorted(overlaps.items(), key=lambda x: -x[1]):
        if count > 0:
            lines.append(f"| {p1} | {count} | {p2} |")

    lines.extend([
        "",
        "## Large Changes (>50 files)",
        "",
    ])

    large_prs = [p for p in prs if p.get("changedFiles", 0) > 50]
    for pr in sorted(large_prs, key=lambda x: -x.get("changedFiles", 0)):
        lines.append(f"- PR #{pr['number']}: {pr['headRefName']} ({pr.get('changedFiles', 0)} files)")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="PR conflict map and merge order recommendation")
    parser.add_argument("--repo", default="MasumRab/gemini-fullstack-langgraph-quickstart",
                        help="GitHub repo in owner/name format")
    parser.add_argument("--report", action="store_true", help="Generate markdown report")
    args = parser.parse_args()

    print(f"Fetching open PRs from {args.repo}...")
    prs = get_all_open_prs(args.repo)
    print(f"Found {len(prs)} open PRs")

    print("Building file overlap map...")
    pr_files, overlaps = build_overlap_map(prs, args.repo)

    if args.report:
        CONFLICT_REPORT.parent.mkdir(parents=True, exist_ok=True)
        report = generate_markdown_report(prs, pr_files, overlaps, args.repo)
        CONFLICT_REPORT.write_text(report + "\n")
        print(f"Wrote conflict map to {CONFLICT_REPORT}")


if __name__ == "__main__":
    main()