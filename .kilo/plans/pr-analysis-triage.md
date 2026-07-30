# Plan: PR Analysis & Triage for gemini-fullstack-langgraph-quickstart

## Goal
Implement PR triage system to analyze all 31 open PRs, detect file overlaps, recommend merge order, and generate repair prompts for conflicting PRs.

## Current State (2026-06-08)
- **31 open PRs** in MasumRab/gemini-fullstack-langgraph-quickstart
- **7 MERGEABLE**: #349, #350, #353, #356, #364, #365, #368, #369, #370, #371, #372
- **24 CONFLICTING**: #275, #283, #287, #288, #289, #290, #296, #297, #302, #307, #308, #310, #340, #346, #347, #348, #351, #352, #354
- **0 UNKNOWN** (all PRs now have determined mergeable status)

- **Reference tools exist** in kaggle-notebooks-analysis:
  - `pr_analysis.sh` - generates individual PR markdown with repair prompts
  - `jules_pr_context.py` - extracts PR metrics, CI status, comments
  - `jules_rebase_orchestrator.py` - queue-based rebase with merge-tree validation

## Proposed Implementation

### 1. Create `scripts/pr_analysis.sh` for gemini repo
Adapt from kaggle's `pr_analysis.sh` to:
- Accept `--repo MasumRab/gemini-fullstack-langgraph-quickstart`
- Analyze all 31 open PRs (or specific sets)
- Generate markdown files in `docs/pr_analysis/individual/`
- Include Jules repair prompts for CONFLICTING PRs
- Extract any Jules session links from PR bodies/comments

### 2. Create `scripts/jules_tools/jules_pr_triage.py` for gemini repo
Build file-overlap conflict map to:
- Fetch all open PRs via `gh pr list`
- Compute file overlap between each pair of PR branches
- Assign priority tiers (security > bugs > tests > features > chores)
- Recommend merge order based on:
  1. Smaller changes first (lower risk)
  2. Less overlap first
  3. Priority tier ordering

### 3. Create `scripts/jules_tools/jules_pr_context.py` for gemini repo
Extract PR metadata for Jules recovery prompts:
- PR title, author, files changed
- CI check status (passing/failing/pending)
- Review comments and threads
- Mergeable status

### 4. Update `docs/PR_CONFLICT_REVIEW.md` with current status
Replace outdated 2025-12-12 snapshot with:
- Current PR counts and statuses
- Notable conflicts (PR #283 -8570 deletions, #346 #347 large changes)
- Recommended merge order

## Key Differences from kaggle repo
- **No stacked PRs** - all diverge from main (simpler graph topology)
- **Different agents** - sentinel, bolt, antigravity instead of generic labels
- **Different file types** - .tsx, .py, .ipynb, .md mix

## Commands to Run (after implementation)

```bash
# Analyze all open PRs
./scripts/pr_analysis.sh --repo MasumRab/gemini-fullstack-langgraph-quickstart --pr-set "$(gh pr list --repo MasumRab/gemini-fullstack-langgraph-quickstart --state open --json number | jq -r '.[].number' | tr '\n' ' ')"

# Get conflict map and merge order
python scripts/jules_tools/jules_pr_triage.py --repo MasumRab/gemini-fullstack-langgraph-quickstart --report

# Check specific PR context
python scripts/jules_tools/jules_pr_context.py 346
```

## Estimated Effort
- Copy & adapt scripts: ~15 minutes
- Run analysis: ~1 minute
- Review results: ~10 minutes

## Risks
- Large PRs (#283 -8570 deletions, #346 +5530 lines) may have complex conflicts
- Some PRs may have deleted valuable code (like PR #16 in old doc)