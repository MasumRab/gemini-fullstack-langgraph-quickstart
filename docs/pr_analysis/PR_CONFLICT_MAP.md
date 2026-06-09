# PR Conflict Map & Merge Order

## Summary

| Status | Count |
|--------|-------|
| MERGEABLE | 11 |
| CONFLICTING | 19 |

## Mergeable PRs (Ready to merge)

- PR #349: `jules-4486936059047711087-e991cb85` (+255 -164, 54 files)
- PR #350: `agent-cleanup-task-11790186057934001697` (+1442 -931, 62 files)
- PR #353: `chore/linear-repo-health-audit-16015195601436770027` (+100 -11, 10 files)
- PR #356: `agent-repo-maintenance-2773016427995540587` (+10 -3, 3 files)
- PR #364: `cto/resolve-accessibility-rebase` (+755 -48, 8 files)
- PR #365: `cto/resolve-conflicts-merge-8-prs-rerere` (+804 -116, 15 files)
- PR #368: `agent-cleanup-ruff-fixes-8631250892007985202` (+186 -104, 38 files)
- PR #369: `jules-899862534564244020-0ad7c785` (+201 -47, 10 files)
- PR #370: `agent-maintenance-todo-cleanup-16753839092582531381` (+240 -80, 15 files)
- PR #371: `recovery-critical-fixes` (+44 -12, 8 files)
- PR #372: `fix/trusted-proxy-late-binding-917366035391238728` (+153 -219, 5 files)

## Conflicting PRs (Need resolution)

- PR #346: `jules-kaggle-gemma-integration-9750286105324430980` (+5530 -3262, 101 files)
- PR #347: `jules-15198152699149131080-b0bfadc2` (+1619 -1027, 78 files)
- PR #289: `sentinel-logging-enhancement-4918278467349114335` (+1331 -372, 52 files)
- PR #290: `maintenance/cleanup-and-organization-8179461817397132422` (+553 -9171, 96 files)
- PR #354: `feat/render-free-tier-lite-mode-6186272092202799273` (+539 -436, 52 files)
- PR #340: `render-free-tier-gemma-api-18323209961354138092` (+498 -1142, 17 files)
- PR #352: `feat/render-free-tier-lite-mode-11438400044889294952` (+424 -18, 11 files)
- PR #351: `jules/linear-audit-report-14651602167598398032` (+394 -492, 51 files)
- PR #310: `sentinel/fix-ip-spoofing-ratelimit-2166097941151715551` (+360 -255, 25 files)
- PR #348: `jules-consolidate-examples-notebooks-2105168770599836167` (+281 -354, 23 files)
- PR #297: `bolt/lazy-load-search-providers-5660363663322280167` (+82 -70, 3 files)
- PR #308: `fix-test-suite-stability-3968941239566233894` (+64 -8, 3 files)
- PR #307: `bolt-lazy-search-init-47180017976503727` (+54 -47, 2 files)
- PR #302: `fix-extended-tests-configuration-16683645347065683212` (+40 -0, 2 files)
- PR #283: `palette/activity-timeline-semantics-2717574023185544628` (+39 -8570, 3 files)
- PR #288: `palette-activity-timeline-semantic-list-11022930860156776867` (+37 -17, 2 files)
- PR #287: `bolt-optimize-string-concatenation-6997016135442389858` (+12 -9, 2 files)
- PR #296: `palette-activity-timeline-semantic-list-6726386105313152954` (+1 -0, 1 files)
- PR #275: `palette-ux-improvement-welcome-footer-contrast-17142042357956849385` (+1 -1, 1 files)

## Merge Order Recommendation

1. Merge clean PRs first (#349, #350, #353, #356, #364, #365, #368, #369, #370, #371, #372)
2. Resolve large conflicting PRs (#346, #347) - require careful review
3. Address smaller conflicting PRs in priority order (sentinel/bolt > antigravity/fix > others)
