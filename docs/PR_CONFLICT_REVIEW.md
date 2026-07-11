# Open PR Conflict Review

> **Generated**: 2026-06-08
> **Purpose**: Document conflicts and issues in open PRs before merge

---

## Summary

| Status | Count |
|--------|-------|
| MERGEABLE | 11 |
| CONFLICTING | 20 |

---

## Mergeable PRs (Ready)

| PR | Title | Status | Risk |
|----|-------|--------|------|
| #349 | jules-4486936059047711087-e991cb85 | MERGEABLE | Low (+255 lines) |
| #350 | agent-cleanup-task-1179018605793400 | MERGEABLE | Medium (+1442 lines) |
| #353 | chore/linear-repo-health-audit-1601 | MERGEABLE | Low (+100 lines) |
| #356 | agent-repo-maintenance-277301642799 | MERGEABLE | Low (+10 lines) |
| #364 | cto/resolve-accessibility-rebase | MERGEABLE | Medium (+755 lines) |
| #365 | cto/resolve-conflicts-merge-8-prs-r | MERGEABLE | Medium (+804 lines) |
| #368 | agent-cleanup-ruff-fixes-8631250892 | MERGEABLE | Low (+201 lines) |
| #369 | jules-899862534564244020-0ad7c785 | MERGEABLE | Low (+240 lines) |
| #370 | agent-maintenance-todo-cleanup-1675 | MERGEABLE | Low (+44 lines) |
| #371 | recovery-critical-fixes | MERGEABLE | Medium (+360 lines) |
| #372 | fix/trusted-proxy-late-binding-9173 | MERGEABLE | Medium (+153 lines) |

---

## Conflicting PRs (Need Resolution)

### Priority 1: Security (sentinel)
| PR | Branch | Files | Delta | Action |
|----|--------|-------|-------|--------|
| #310 | sentinel/fix-ip-spoofing-ratelimit- | 31 files | +360/-31 | High priority - security |
| #289 | sentinel-logging-enhancement-491827 | 553 files | +553/-372 | High priority - logging |

### Priority 2: Performance (bolt)
| PR | Branch | Files | Delta | Action |
|----|--------|-------|-------|--------|
| #297 | bolt/lazy-load-search-providers-566 | 82 files | +82/-70 | Optimize search providers |
| #287 | bolt-optimize-string-concatenation- | 12 files | +12/-9 | String optimization |
| #307 | bolt-lazy-search-init-4718001797650 | 54 files | +54/-47 | Search init |

### Priority 3: Large Changes (Require careful review)
| PR | Branch | Files | Delta | Action |
|----|--------|-------|-------|--------|
| #283 | palette/activity-timeline-semantics | 39 files | -8570 deletions | Large removal - verify intent |
| #346 | jules-kaggle-gemma-integration-9750 | 346 files | +5530/-3262 | Largest addition - careful review |
| #347 | jules-15198152699149131080-b0bfadc2 | 347 files | +1619/-1027 | Jules integration |
| #290 | maintenance/cleanup-and-organizatio | 553 files | -9171 deletions | Large cleanup |

### Priority 4: Other
| PR | Branch | Files | Action |
|----|--------|-------|--------|
| #275 | palette-ux-improvement-welcome-foot | 2 files | UX improvement |
| #288 | palette-activity-timeline-semantic- | 37 files | Duplicate of #283? |
| #296 | palette-activity-timeline-semantic- | 1 file | Duplicate of #283? |
| #302 | fix-extended-tests-configuration-16 | 40 files | Test config |
| #308 | fix-test-suite-stability-3968941239 | 64 files | Test stability |
| #340 | render-free-tier-gemma-api-18323209 | 498 files | Gemma API |
| #348 | jules-consolidate-examples-notebook | 281 files | Examples |
| #351 | jules/linear-audit-report-146516021 | 394 files | Audit report |
| #352 | feat/render-free-tier-lite-mode-114 | 424 files | Lite mode |
| #354 | feat/render-free-tier-lite-mode-618 | 539 files | Lite mode variant |

---

## Merge Order Recommendation

1. **First batch (low risk)**: #356, #353, #370, #372, #368, #369, #349
2. **Second batch (medium risk)**: #350, #364, #365, #371
3. **After conflict resolution**: All CONFLICTING PRs above

---

## Action Items

- [ ] Review duplicate PRs (#283, #288, #296) - may conflict with each other
- [ ] Inspect large deletions (#283 -8570, #290 -9171) for unintended removals
- [ ] Rebase sentinel PRs (#310, #289) with priority
- [ ] Rebase bolt PRs (#297, #287, #307) for performance improvements
- [ ] Carefully review #346 (largest PR) before merging
