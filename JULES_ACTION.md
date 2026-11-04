# Jules Action Recommendations – Gemini Full‑Stack LangGraph QuickStart

## Project Overview
This repo is a starter kit that combines Google’s Gemini LLM with LangGraph to build agent‑based applications. It contains:
- Backend (FastAPI/Node) API definitions
- Frontend (React/Vue) UI components
- Example agent configurations and test harnesses
- Dockerfiles / docker‑compose for local development
- Documentation in `docs/` and a `README.md` that should reflect the current project structure.

Typical contributions involve:
- Adding or modifying API endpoints
- Updating frontend components
- Adjusting LangGraph agent definitions
- Updating dependencies (npm, pip) and ensuring linting/formatting passes
- Keeping documentation in sync with code changes

Because work is often delivered via PRs that touch multiple language stacks, the **Advanced Jules PR Reviewer** remains the most effective tool: it can comment on specific lines in JavaScript, TypeScript, Python, YAML, or Dockerfiles, auto‑resolve its comments, and only analyse the changed diff on each push.

### Recommended Workflow (Advanced PR Reviewer)
Create `.github/workflows/jules-advanced-pr-review.yml`:

```yaml
name: Jules Advanced PR Review – Gemini‑LangGraph
on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]

concurrency:
  group: jules-review-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read
      statuses: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Load environment (mise + .env)
        run: |
          eval "$(mise activate bash)"
          source ~/.env

      - name: Run Jules Advanced PR Review
        uses: thalesraymond/jules-pr-reviewer@v1
        with:
          jules_api_key: ${{ secrets.JULES_API_KEY }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
          rules_file: .github/jules-review-rules.md   # optional but recommended
          extra_instructions: |
            This repository is a Gemini‑LangGraph full‑stack starter kit.
            Focus on:
              • Backend API correctness – validate request/response schemas, authentication middleware, and error handling.
              • Frontend bundle size – watch for large dependencies that bloat the payload.
              • LangGraph agent definitions – ensure nodes have proper typing, error handling, and deterministic state transitions.
              • Dockerfile / docker‑compose best practices – use non‑root users, multi‑stage builds, and pin exact base image versions.
              • Documentation consistency – the README and docs/ must reflect the current folder structure and API signatures.
              • Follow existing linting/formatting configs (.eslintrc.js, prettier.config.js, ruff configuration, etc.).
          timeout_minutes: 45
```

#### Optional Rule File (`.github/jules-review-rules.md`)
A useful starter set:

```markdown
# Jules Review Rules – Gemini‑LangGraph QuickStart

## Blocking
* Missing Dockerfile or docker‑compose.yml when a service declares a container dependency.
* API endpoints lacking authentication/authorization middleware.

## Warn
* Frontend bundle size > 2 MB (check webpack output or similar).
* Backend routes that return raw exception stack traces to the client.
* Use of TypeScript `any` without justification.

## Info
* Missing JSDoc on exported functions.
* Inconsistent naming between React component filenames and their exported names.
```

### When to Use Other Jules Actions
| Action | When it makes sense | Quick Adaptation |
|--------|--------------------|------------------|
| **Jules Invoke** (generic) | Routine maintenance: dependency updates, linting, docs refresh, running the full test suite. | Use the generic Invoke template (see below) with a prompt such as “Run `npm outdated` and `pip list --outdated`, open a PR to update any package with CVSS ≥ 7.0; ensure ESLint/Prettier and Ruff/Black pass; verify the README matches the current structure; run the test suite and propose fixes for any failures.” |
| **Jules PR Comment** | After a scheduled maintenance job (e.g., nightly dependency update) you want Jules to leave a summary comment on the PR that triggered the update. | Capture the session ID from the Invoke step and call the `jules-pr-comment` workflow (or copy its step) with that ID and the PR number. |
| **Send Feedback to Jules** | Enable maintainers to teach Jules from their review comments (e.g., correcting a false positive). | Add the `send-feedback-to-jules` workflow and list the maintainer usernames in `feedback_users`. |

---

## Reasoning & Context
* The Advanced Reviewer’s **incremental diff** means that when you only change a single TypeScript file, Jules only sees that file’s diff – keeping the prompt tiny and the cost low.
* Line‑level feedback works across all file types present in the repo (`.ts`, `.tsx`, `.js`, `.py`, `.yaml`, `.dockerfile`, `.md`), which is essential for a full‑stack project.
* Auto‑resolve keeps the PR clean when you push a fix for a flagged line (e.g., adding missing auth middleware).
* The `extra_instructions` block summarises the project’s most important conventions (backend auth, frontend bundle size, LangGraph typing, Docker best practices, docs sync) so Jules does not have to infer them from scratch.
* The rule file lets you enforce project‑specific policies (e.g., “missing Dockerfile is blocking”) with the appropriate severity, guaranteeing that Jules’ verdict aligns with your gatekeeping strategy.
* All workflows reuse the existing `mise`‑managed environment and the `~/.env` secret, guaranteeing that Jules sees the same tool versions and API keys as a local developer.