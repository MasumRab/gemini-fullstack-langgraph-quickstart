# Jules Actions Traceability: gemini-fullstack-langgraph-quickstart

Date: 2026-07-08
Repo: `MasumRab/gemini-fullstack-langgraph-quickstart`
Local repo name checked: `gemini-fullstack-langgraph-quickstart`
Status: recommendation record; workflows not yet installed by this document.

## Existing local evidence

Relevant existing files found locally:

- `.Jules/TASKS.md`
- `.Jules/antigravity.md`
- `.Jules/bolt.md`
- `.Jules/palette.md`
- `.Jules/sentinel.md`
- `.JULES_ARCHIVE.md`
- `AGENTS.md` mentions `JULES_API_KEY`.
- `scripts/jules_tools/jules_pr_context.py`
- `scripts/jules_tools/jules_pr_triage.py`
- Current workflows: `pr-check.yml`, `push-check.yml`, `validate-env.yml`, `dependabot-auto-merge.yml`.

No dedicated `jules_actions.md`, `.github/jules-review-rules.md`, or Jules GitHub Actions workflows were found during inspection.

## Suitability assessment

This repo is a strong fit for Jules PR review and targeted Jules invocation. It has frontend/backend integration, Gemini/LangGraph behavior, environment validation, upstream drift risk, and existing Jules task/journaling conventions.

The repo already uses `pull_request_target` for Dependabot auto-merge. Jules workflows should not copy that pattern; Jules review should use `pull_request` and skip forks by default.

## Recommended Jules Actions

| Action/workflow | Recommendation | Purpose |
|---|---:|---|
| Advanced Jules PR Reviewer | Adopt | Semantic fullstack review, env/secrets review, API-contract review. |
| Backlog/stale PR sweep | Adopt weekly/manual | Classify stale agent/Jules/cleanup branches and upstream-drift risk. |
| Jules Invoke | Adopt | Manual/label-gated CI repair, upstream sync, test generation, env validation fixes. |
| Jules PR Comment / metadata | Optional/adopt if Jules PRs are common | Publish session context on Jules-authored PRs. |
| Send Feedback to Jules | Adopt if Jules-authored PRs are common | Send human reviews back to existing Jules sessions. |

## Review focus

A repo-specific Jules review should focus on:

- frontend/backend API compatibility,
- LangGraph agent behavior,
- Gemini model configuration and API-key handling,
- rate limiting and model availability,
- dependency/version drift from upstream,
- async/search/tool integration behavior,
- tests for changed behavior,
- `.env.example` correctness without real secrets.

## Recommended workflow files

- `.github/workflows/jules-pr-review.yml`
- `.github/workflows/jules-backlog-review.yml` optional but useful
- `.github/workflows/jules-invoke.yml`
- `.github/workflows/jules-feedback.yml` if Jules-authored PRs are common
- `.github/workflows/jules-pr-metadata.yml` if Jules-authored PRs are common
- `.github/jules-review-rules.md`

## Safeguards

- Use `pull_request`, not `pull_request_target`, for Jules review.
- Skip forks by default.
- Do not expose `GEMINI_API_KEY` or add real secrets to examples.
- Do not broaden auth/CORS/network exposure without explicit task scope.
- Prefer small PRs over broad generated cleanup.
- If syncing upstream, isolate upstream changes from local customizations.
- Use `fail_on: blocking` rather than `any`.

## Suggested first implementation order

1. Add `.github/jules-review-rules.md`.
2. Add advisory `jules-pr-review.yml`.
3. Add manual `jules-invoke.yml`.
4. Add metadata/feedback workflows only if Jules-authored PRs are frequent.
5. Add backlog sweep if stale PR count remains high.

## Open questions

- Should Jules review be required by branch protection or advisory only?
- Which local scripts should Jules be allowed to run during backlog triage?
- Which maintainers should be in `feedback_users`?
