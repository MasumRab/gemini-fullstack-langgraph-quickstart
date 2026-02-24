# PR Rebase and Reorganization Plan

## Overview
Systematically check PRs #236-#274 for comments, CI failures, and conflicts, then rebase and reorganize with git rerere enabled.

## Prerequisites Setup

```bash
# Enable git rerere (reuse recorded resolution)
git config --global rerere.enabled true
git config --global rerere.autoupdate true

# Fetch all remote branches
git fetch --all --prune

# Ensure clean working directory
git status
```

## Step-by-Step Process

### Phase 1: Audit All PRs

For each PR in range #236-#274, check:

1. **PR Status** - OPEN, MERGED, CLOSED
2. **Mergeability** - Mergeable, CONFLICTING, UNKNOWN
3. **CI Status** - SUCCESS, FAILURE, PENDING
4. **Draft Status** - Draft or Ready
5. **Actionable Comments** - Owner requests for changes

```bash
# Quick audit command
gh pr view <PR_NUMBER> --json number,title,state,mergeable,mergeStateStatus,statusCheckRollup,comments,isDraft,url
```

### Phase 2: Categorize PRs

| Category | Action |
|----------|--------|
| ✅ Ready | CI passing, no conflicts, not draft → Review and merge |
| ⚠️ Conflicts | Has merge conflicts → Rebase onto main |
| ❌ CI Failures | Tests failing → Fix failing tests |
| 📝 Draft | Work in progress → Complete or close |
| 💬 Comments | Owner requested changes → Address feedback |

### Phase 3: Rebase Process

For each PR with conflicts or needing updates:

```bash
# 1. Checkout the PR branch
gh pr checkout <PR_NUMBER>

# 2. Fetch latest main
git fetch origin main

# 3. Rebase onto main (rerere will record resolutions)
git rebase origin/main

# 4. If conflicts occur, resolve them:
# - Edit conflicting files
# - git add <resolved-files>
# - git rebase --continue
# Rerere will remember the resolution for future rebases

# 5. Force push with lease (safer than force push)
git push --force-with-lease origin HEAD
```

### Phase 4: Batch Processing Script

Run the analysis script:
```bash
python scripts/pr_rebase_organize.py --dry-run
```

For live rebase (after review):
```bash
python scripts/pr_rebase_organize.py --no-dry-run
```

---

## PR Analysis Template

For each PR, document:

```markdown
### PR #<NUMBER>: <TITLE>

- **Branch**: `<branch-name>`
- **Status**: OPEN/MERGED/CLOSED
- **Draft**: Yes/No
- **Mergeable**: YES/CONFLICTING/UNKNOWN
- **CI Status**: SUCCESS/FAILURE/PENDING/NONE
- **Action Required**: <description>

#### Issues Found
- [ ] Merge conflicts in: <files>
- [ ] CI failures: <checks>
- [ ] Comments to address: <summary>

#### Resolution
- [ ] Rebase onto main
- [ ] Fix conflicts
- [ ] Fix CI failures
- [ ] Address comments
- [ ] Push and verify
```

---

## Quick Reference Commands

```bash
# View PR details
gh pr view <N>

# Checkout PR
gh pr checkout <N>

# Check CI status
gh pr checks <N>

# View PR diff
gh pr diff <N>

# Merge PR
gh pr merge <N> --squash

# Close PR
gh pr close <N>

# Enable rerere for repo
git config rerere.enabled true
```

---

## Next Steps

1. [ ] Run batch analysis script
2. [ ] Review categorized results
3. [ ] Process PRs in priority order:
   - Security (Sentinel) PRs first
   - Performance (Bolt) PRs second
   - UX/UI PRs third
   - Other PRs last
4. [ ] Document conflict resolutions
5. [ ] Update this report with results