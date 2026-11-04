#!/usr/bin/env python3
"""
Fast PR Analysis - generates individual PR markdown files
Uses cached PR data to avoid gh CLI timeouts.
"""

from pathlib import Path

OUTPUT_DIR = Path("docs/pr_analysis/individual")

PR_DATA = {
    275: {"branch": "palette-ux-improvement-welcome-foot", "status": "CONFLICTING", "additions": 1, "deletions": 1, "files": 1},
    283: {"branch": "palette/activity-timeline-semantics", "status": "CONFLICTING", "additions": 39, "deletions": 8570, "files": 3},
    287: {"branch": "bolt-optimize-string-concatenation-", "status": "CONFLICTING", "additions": 12, "deletions": 9, "files": 2},
    288: {"branch": "palette-activity-timeline-semantic-", "status": "CONFLICTING", "additions": 37, "deletions": 17, "files": 2},
    289: {"branch": "sentinel-logging-enhancement-491827", "status": "CONFLICTING", "additions": 553, "deletions": 372, "files": 52},
    290: {"branch": "maintenance/cleanup-and-organizatio", "status": "CONFLICTING", "additions": 553, "deletions": 9171, "files": 96},
    296: {"branch": "palette-activity-timeline-semantic-", "status": "CONFLICTING", "additions": 1, "deletions": 0, "files": 1},
    297: {"branch": "bolt/lazy-load-search-providers-566", "status": "CONFLICTING", "additions": 82, "deletions": 70, "files": 3},
    302: {"branch": "fix-extended-tests-configuration-16", "status": "CONFLICTING", "additions": 40, "deletions": 0, "files": 2},
    307: {"branch": "bolt-lazy-search-init-4718001797650", "status": "CONFLICTING", "additions": 54, "deletions": 47, "files": 2},
    308: {"branch": "fix-test-suite-stability-3968941239", "status": "CONFLICTING", "additions": 64, "deletions": 8, "files": 3},
    310: {"branch": "sentinel/fix-ip-spoofing-ratelimit-", "status": "CONFLICTING", "additions": 360, "deletions": 310, "files": 25},
    340: {"branch": "render-free-tier-gemma-api-18323209", "status": "CONFLICTING", "additions": 498, "deletions": 1142, "files": 17},
    346: {"branch": "jules-kaggle-gemma-integration-9750", "status": "CONFLICTING", "additions": 5530, "deletions": 3262, "files": 101},
    347: {"branch": "jules-15198152699149131080-b0bfadc2", "status": "CONFLICTING", "additions": 1619, "deletions": 1027, "files": 78},
    348: {"branch": "jules-consolidate-examples-notebook", "status": "CONFLICTING", "additions": 281, "deletions": 354, "files": 23},
    349: {"branch": "jules-4486936059047711087-e991cb85", "status": "MERGEABLE", "additions": 255, "deletions": 164, "files": 54},
    350: {"branch": "agent-cleanup-task-1179018605793400", "status": "MERGEABLE", "additions": 1442, "deletions": 931, "files": 62},
    351: {"branch": "jules/linear-audit-report-146516021", "status": "CONFLICTING", "additions": 394, "deletions": 492, "files": 51},
    352: {"branch": "feat/render-free-tier-lite-mode-114", "status": "CONFLICTING", "additions": 424, "deletions": 18, "files": 11},
    353: {"branch": "chore/linear-repo-health-audit-1601", "status": "MERGEABLE", "additions": 100, "deletions": 11, "files": 10},
    354: {"branch": "feat/render-free-tier-lite-mode-618", "status": "CONFLICTING", "additions": 539, "deletions": 436, "files": 52},
    356: {"branch": "agent-repo-maintenance-277301642799", "status": "MERGEABLE", "additions": 10, "deletions": 3, "files": 3},
    364: {"branch": "cto/resolve-accessibility-rebase", "status": "MERGEABLE", "additions": 755, "deletions": 48, "files": 8},
    365: {"branch": "cto/resolve-conflicts-merge-8-prs-r", "status": "MERGEABLE", "additions": 804, "deletions": 116, "files": 15},
    368: {"branch": "agent-cleanup-ruff-fixes-8631250892", "status": "MERGEABLE", "additions": 201, "deletions": 47, "files": 38},
    369: {"branch": "jules-899862534564244020-0ad7c785", "status": "MERGEABLE", "additions": 240, "deletions": 80, "files": 10},
    370: {"branch": "agent-maintenance-todo-cleanup-1675", "status": "MERGEABLE", "additions": 44, "deletions": 12, "files": 15},
    371: {"branch": "recovery-critical-fixes", "status": "MERGEABLE", "additions": 360, "deletions": 371, "files": 8},
    372: {"branch": "fix/trusted-proxy-late-binding-9173", "status": "MERGEABLE", "additions": 153, "deletions": 219, "files": 5},
}


def get_priority(branch):
    if branch.startswith("sentinel/") or "security" in branch.lower():
        return "🔴 CRITICAL"
    if branch.startswith("bolt/"):
        return "🟠 HIGH (Performance)"
    if branch.startswith("antigravity/") or branch.startswith("fix/"):
        return "🟠 HIGH (Bugfix)"
    if "test" in branch.lower():
        return "🟡 MEDIUM"
    return "🔵 LOW (Feature/Chore)"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for pr_num, info in sorted(PR_DATA.items()):
        priority = get_priority(info["branch"])
        status_emoji = "✅" if info["status"] == "MERGEABLE" else "🔴"
        
        content = f"""# PR #{pr_num}: {info['branch']}

## Overview
- **Repository**: MasumRab/gemini-fullstack-langgraph-quickstart
- **PR Number**: {pr_num}
- **Branch**: {info['branch']}
- **Mergeable**: {status_emoji} {info['status']}
- **Additions**: +{info['additions']}
- **Deletions**: -{info['deletions']}
- **Changed Files**: {info['files']}
- **Priority**: {priority}

## Jules Repair Prompt

{f'''**Priority:** CRITICAL
**Issue:** Merge conflicts with base branch `main`

**Recovery Actions:**
1. `git fetch origin && git rebase origin/main`
2. Resolve merge conflict markers in affected files
3. Run: `cd backend && make lint && cd ../frontend && npm run lint`
4. Push and verify CI passes
''' if info['status'] == 'CONFLICTING' else ''}
"""
        output_file = OUTPUT_DIR / f"PR_{pr_num}.md"
        output_file.write_text(content)
        print(f"Wrote {output_file}")


if __name__ == "__main__":
    main()