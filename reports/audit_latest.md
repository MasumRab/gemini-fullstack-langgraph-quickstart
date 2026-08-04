# Repository Health Audit Report
**Date**: 2026-03-24

## Status
**Action Required**

## Findings
The repository audit discovered 2 PRs needing attention:

1. **[PR #348] refactor: consolidate examples and notebooks to backend directory**
   - **Branch**: `jules-consolidate-examples-notebooks-2105168770599836167`
   - **Issues**: Has pending `CHANGES_REQUESTED` review state and experienced CI Failures.

2. **[PR #346] Add Kaggle models integration plan and scaffold**
   - **Branch**: `jules-kaggle-gemma-integration-9750286105324430980`
   - **Issues**: Detected `failure` states in recent workflow runs for the branch.

## Actions
Created Linear issues in project `Repo Health` to track resolution:
- **Created Issue MAS-41**: [Review Blockers & CI Failure: [PR #348]](https://linear.app/masumai/issue/MAS-41)
- **Created Issue MAS-42**: [Fix CI Failure: [PR #346]](https://linear.app/masumai/issue/MAS-42)

Additional GitHub Discovery generated: `pr_summary.json` and `runs_summary.json` locally.
