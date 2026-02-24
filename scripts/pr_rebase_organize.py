#!/usr/bin/env python3
"""
PR Rebase and Reorganization Script

This script systematically processes PRs #236-#274 to:
1. Enable git rerere (reuse recorded resolution) for conflict resolution
2. Check each PR for conflicts, CI failures, and actionable comments
3. Attempt to rebase onto latest main
4. Track required changes

Prerequisites:
- gh CLI authenticated
- Git configured with rerere enabled
- Clean working directory

Usage:
    python scripts/pr_rebase_organize.py [--dry-run] [--pr-number N]
"""

import subprocess
import json
import sys
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import time

# Configuration
PR_START = 236
PR_END = 274

@dataclass
class PRAuditResult:
    """Results from auditing a single PR."""
    number: int
    title: str
    url: str
    branch: str
    base_branch: str
    state: str
    is_draft: bool
    mergeable: str
    merge_state: str
    ci_status: str
    ci_failures: list
    actionable_comments: list
    has_conflicts: bool
    needs_rebase: bool
    needs_changes: bool
    rebase_success: Optional[bool] = None
    conflict_files: list = None
    
    def __post_init__(self):
        self.conflict_files = self.conflict_files or []


def run_command(cmd: list, cwd: str = None, check: bool = False) -> tuple:
    """Run a shell command and return (success, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=120,
            encoding='utf-8',
            errors='replace'  # Replace undecodable characters
        )
        return result.returncode == 0, result.stdout or "", result.stderr or ""
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def run_gh(args: list) -> Optional[dict]:
    """Run gh CLI command and parse JSON output."""
    success, stdout, stderr = run_command(["gh"] + args)
    if success and stdout.strip():
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return None
    return None


def enable_rerere():
    """Enable git rerere for conflict resolution tracking."""
    print("=" * 60)
    print("ENABLING GIT RERERE")
    print("=" * 60)
    
    # Enable rerere globally and locally
    commands = [
        ["git", "config", "--global", "rerere.enabled", "true"],
        ["git", "config", "--global", "rerere.autoupdate", "true"],
        ["git", "config", "--global", "rerere.memorylimit", "1000000"],
    ]
    
    for cmd in commands:
        success, _, _ = run_command(cmd)
        status = "✓" if success else "✗"
        print(f"  {status} {' '.join(cmd[3:])}")
    
    # Verify
    success, stdout, _ = run_command(["git", "config", "rerere.enabled"])
    print(f"\n  Rerere enabled: {stdout.strip()}")
    print()


def fetch_all_branches():
    """Fetch all remote branches."""
    print("Fetching all remote branches...")
    success, _, stderr = run_command(
        ["git", "fetch", "--all", "--prune"],
        check=True
    )
    if success:
        print("  ✓ Fetch complete")
    else:
        print(f"  ✗ Fetch failed: {stderr}")
    return success


def ensure_clean_working_directory() -> bool:
    """Check if working directory is clean."""
    success, stdout, _ = run_command(["git", "status", "--porcelain"])
    if stdout.strip():
        print("ERROR: Working directory is not clean!")
        print("Please commit or stash changes before running this script.")
        return False
    return True


def get_pr_details(pr_number: int) -> Optional[PRAuditResult]:
    """Get detailed PR information and analyze it."""
    pr = run_gh([
        "pr", "view", str(pr_number),
        "--json", "number,title,state,mergeable,mergeStateStatus,"
                  "statusCheckRollup,comments,reviewDecision,url,isDraft,"
                  "headRefName,baseRefName"
    ])
    
    if not pr:
        return None
    
    # Analyze CI status
    status_rollup = pr.get("statusCheckRollup", [])
    ci_status = "UNKNOWN"
    ci_failures = []
    
    if status_rollup:
        failures = [c for c in status_rollup 
                   if c.get("state") in ["FAILURE", "ERROR", "TIMED_OUT"]]
        successes = [c for c in status_rollup if c.get("state") == "SUCCESS"]
        
        if failures:
            ci_status = "FAILURE"
            ci_failures = [{"context": f.get("context"), "state": f.get("state")}
                          for f in failures]
        elif successes and len(successes) == len(status_rollup):
            ci_status = "SUCCESS"
        else:
            ci_status = "PENDING"
    else:
        ci_status = "NO_CHECKS"
    
    # Analyze comments
    actionable_comments = []
    for comment in pr.get("comments", []):
        is_owner = comment.get("authorAssociation") == "OWNER"
        body = comment.get("body", "")
        has_action = any(w in body.lower() for w in 
                        ["fix", "update", "change", "resolve", "@jules"])
        
        if is_owner and has_action:
            actionable_comments.append({
                "author": comment.get("author", {}).get("login", ""),
                "body": body[:150],
                "created": comment.get("createdAt")
            })
    
    mergeable = pr.get("mergeable", "UNKNOWN")
    
    return PRAuditResult(
        number=pr.get("number"),
        title=pr.get("title"),
        url=pr.get("url"),
        branch=pr.get("headRefName", ""),
        base_branch=pr.get("baseRefName", "main"),
        state=pr.get("state"),
        is_draft=pr.get("isDraft", False),
        mergeable=mergeable,
        merge_state=pr.get("mergeStateStatus", "UNKNOWN"),
        ci_status=ci_status,
        ci_failures=ci_failures,
        actionable_comments=actionable_comments,
        has_conflicts=mergeable == "CONFLICTING",
        needs_rebase=mergeable in ["CONFLICTING", "UNKNOWN"],
        needs_changes=bool(ci_failures or actionable_comments)
    )


def attempt_rebase(pr: PRAuditResult, dry_run: bool = True) -> tuple:
    """
    Attempt to rebase PR branch onto main.
    Returns (success, conflict_files).
    """
    if dry_run:
        return True, []
    
    original_branch = ""
    success, stdout, _ = run_command(["git", "branch", "--show-current"])
    original_branch = stdout.strip()
    
    # Checkout PR branch
    success, _, stderr = run_command(
        ["git", "checkout", pr.branch]
    )
    if not success:
        return False, []
    
    # Attempt rebase
    success, stdout, stderr = run_command(
        ["git", "rebase", pr.base_branch]
    )
    
    conflict_files = []
    if not success:
        # Get conflict files
        _, conflict_output, _ = run_command(
            ["git", "diff", "--name-only", "--diff-filter=U"]
        )
        conflict_files = conflict_output.strip().split('\n')
        conflict_files = [f for f in conflict_files if f]
        
        # Abort rebase
        run_command(["git", "rebase", "--abort"])
    
    # Return to original branch
    if original_branch:
        run_command(["git", "checkout", original_branch])
    
    return success, conflict_files


def process_pr(pr_number: int, dry_run: bool = True) -> Optional[PRAuditResult]:
    """Process a single PR and return audit results."""
    print(f"\n{'='*60}")
    print(f"PR #{pr_number}")
    print("=" * 60)
    
    pr = get_pr_details(pr_number)
    if not pr:
        print("  Status: NOT FOUND or ERROR")
        return None
    
    # Display PR info
    print(f"  Title: {pr.title}")
    print(f"  Branch: {pr.branch}")
    print(f"  State: {pr.state} {'(DRAFT)' if pr.is_draft else ''}")
    print(f"  Mergeable: {pr.mergeable} ({pr.merge_state})")
    print(f"  CI Status: {pr.ci_status}")
    
    # Check for issues
    issues = []
    if pr.has_conflicts:
        issues.append("⚠️ MERGE CONFLICTS")
    if pr.ci_failures:
        issues.append(f"❌ CI FAILURES ({len(pr.ci_failures)})")
    if pr.actionable_comments:
        issues.append(f"💬 ACTIONABLE COMMENTS ({len(pr.actionable_comments)})")
    if pr.is_draft:
        issues.append("📝 DRAFT")
    
    if issues:
        print(f"  Issues: {', '.join(issues)}")
    else:
        print("  Issues: None ✅")
    
    # Show details if needed
    if pr.ci_failures:
        print("  CI Failures:")
        for f in pr.ci_failures[:3]:
            print(f"    - {f['context']}: {f['state']}")
    
    if pr.actionable_comments:
        print("  Actionable Comments:")
        for c in pr.actionable_comments[:2]:
            print(f"    - [{c['author']}]: {c['body'][:50]}...")
    
    # Attempt rebase if needed
    if pr.needs_rebase:
        print(f"  Rebase: {'DRY RUN - would attempt' if dry_run else 'Attempting...'}")
        if not dry_run:
            success, conflicts = attempt_rebase(pr, dry_run)
            pr.rebase_success = success
            pr.conflict_files = conflicts
            if success:
                print("    ✓ Rebase successful")
            else:
                print(f"    ✗ Rebase failed, conflicts in: {conflicts}")
        else:
            print("    (use --no-dry-run to attempt rebase)")
    
    return pr


def generate_report(results: list, output_path: Path):
    """Generate a detailed report of all PRs."""
    report = []
    report.append("# PR Audit and Rebase Report")
    report.append(f"\nGenerated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"\n## Summary\n")
    
    total = len([r for r in results if r])
    conflicts = [r for r in results if r and r.has_conflicts]
    ci_failures = [r for r in results if r and r.ci_failures]
    drafts = [r for r in results if r and r.is_draft]
    actionable = [r for r in results if r and r.actionable_comments]
    ready = [r for r in results if r and not any([
        r.has_conflicts, r.ci_failures, r.is_draft, r.actionable_comments
    ])]
    
    report.append(f"- Total PRs analyzed: {total}")
    report.append(f"- Ready to merge: {len(ready)}")
    report.append(f"- With merge conflicts: {len(conflicts)}")
    report.append(f"- With CI failures: {len(ci_failures)}")
    report.append(f"- Draft PRs: {len(drafts)}")
    report.append(f"- With actionable comments: {len(actionable)}")
    
    report.append("\n## PRs by Status\n")
    
    # Ready PRs
    if ready:
        report.append("### ✅ Ready to Merge\n")
        for r in sorted(ready, key=lambda x: x.number):
            report.append(f"- #{r.number}: {r.title}")
    
    # Conflict PRs
    if conflicts:
        report.append("\n### ⚠️ Merge Conflicts\n")
        for r in sorted(conflicts, key=lambda x: x.number):
            report.append(f"- #{r.number}: {r.title}")
            report.append(f"  - Branch: `{r.branch}`")
            if r.conflict_files:
                report.append(f"  - Conflicts: {', '.join(r.conflict_files[:5])}")
    
    # CI Failures
    if ci_failures:
        report.append("\n### ❌ CI Failures\n")
        for r in sorted(ci_failures, key=lambda x: x.number):
            report.append(f"- #{r.number}: {r.title}")
            for f in r.ci_failures[:3]:
                report.append(f"  - {f['context']}: {f['state']}")
    
    # Draft PRs
    if drafts:
        report.append("\n### 📝 Draft PRs\n")
        for r in sorted(drafts, key=lambda x: x.number):
            report.append(f"- #{r.number}: {r.title}")
    
    # Actionable Comments
    if actionable:
        report.append("\n### 💬 Requires Action\n")
        for r in sorted(actionable, key=lambda x: x.number):
            report.append(f"- #{r.number}: {r.title}")
            for c in r.actionable_comments[:2]:
                report.append(f"  - [{c['author']}]: {c['body'][:80]}...")
    
    report.append("\n## Recommended Actions\n")
    report.append("""
1. **Merge Ready PRs**: Review and merge PRs that are ready
2. **Resolve Conflicts**: For each conflicting PR:
   ```bash
   git checkout <branch>
   git rebase main
   # Resolve conflicts (rerere will help)
   git rebase --continue
   git push --force-with-lease
   ```
3. **Fix CI Failures**: Address failing tests/checks
4. **Review Draft PRs**: Decide whether to complete or close
5. **Address Comments**: Handle actionable feedback
""")
    
    # Write report
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        f.write('\n'.join(report))
    
    return output_path


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="PR Rebase and Reorganization")
    parser.add_argument("--dry-run", action="store_true", default=True,
                       help="Only analyze, don't make changes")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false",
                       help="Actually perform rebases")
    parser.add_argument("--pr-number", type=int, default=None,
                       help="Process only this PR number")
    parser.add_argument("--start", type=int, default=PR_START,
                       help=f"Start PR number (default: {PR_START})")
    parser.add_argument("--end", type=int, default=PR_END,
                       help=f"End PR number (default: {PR_END})")
    args = parser.parse_args()
    
    print("=" * 60)
    print("PR REBASE AND REORGANIZATION SCRIPT")
    print("=" * 60)
    print(f"\nMode: {'DRY RUN (no changes)' if args.dry_run else 'LIVE (will make changes)'}")
    
    # Pre-flight checks
    if not args.dry_run:
        if not ensure_clean_working_directory():
            sys.exit(1)
        
        enable_rerere()
        fetch_all_branches()
    else:
        print("\n(Dry run mode - skipping pre-flight checks)")
    
    # Process PRs
    results = []
    
    if args.pr_number:
        prs_to_process = [args.pr_number]
    else:
        prs_to_process = range(args.start, args.end + 1)
    
    for pr_num in prs_to_process:
        result = process_pr(pr_num, dry_run=args.dry_run)
        results.append(result)
    
    # Generate report
    output_path = Path(__file__).parent.parent / "reports" / "pr_rebase_report.md"
    generate_report([r for r in results if r], output_path)
    
    print(f"\n{'='*60}")
    print("COMPLETE")
    print("=" * 60)
    print(f"\nReport saved to: {output_path}")


if __name__ == "__main__":
    main()