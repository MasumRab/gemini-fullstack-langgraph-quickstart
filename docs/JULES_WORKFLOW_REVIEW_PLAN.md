# Jules GitHub Workflow Review and Repair Plan

Date: 2026-07-20  
Representative repository: `MasumRab/gemini-fullstack-langgraph-quickstart`  
Status: evolved-workflow regression audit and revised implementation plan; no workflow repairs have been applied by this review

## 1. Objective and scope

Review the recently added Jules pull-request workflows for:

- GitHub Actions YAML and expression validity;
- Jules REST API v1alpha request/response compatibility;
- correct propagation of the pull-request base, head, SHA, changed files, and feedback into the Jules prompt;
- session creation, polling, activity extraction, and failure reporting;
- duplicate-session, fork, pagination, timeout, and prompt-injection risks;
- consistency across repositories that received the shared workflow set.

The original first-pass scope was five shared workflows. The evolved scope is all eight Jules workflows now deployed in the representative repository:

1. `.github/workflows/jules-pr-address-comments.yml`
2. `.github/workflows/jules-pr-auto-fix.yml`
3. `.github/workflows/jules-pr-automerge-label.yml`
4. `.github/workflows/jules-pr-force-review.yml`
5. `.github/workflows/jules-pr-rebuild.yml`
6. `.github/workflows/jules-pr-resolve-conflicts.yml`
7. `.github/workflows/jules-pr-review.yml`
8. `.github/workflows/jules-pr-walkthrough.yml`

The review and force-review workflows are treated as one behavior family. Auto-fix, conflict resolution, walkthrough, rebuild, address-comments, and automerge-label are reviewed separately because they have different branch, trust, mutation, and output requirements.

## 2. Repository inventory and propagation scope

The current deployed eight-file sets are byte-for-byte identical in:

- `EmailIntelligence`;
- `gemini-fullstack-langgraph-quickstart`;
- `kaggle-notebooks-analysis`.

`gemini-cli-prompt-library` is not in that family: it currently has only the original five workflow names, all five have uncommitted edits, and its current `jules-pr-review.yml` contains a duplicate lexical `const fs` declaration that prevents the GitHub Script from compiling. It must not receive a blind copy while those user edits are unresolved.

There is also a newer template/documentation family under `jules/docs/actions/workflows` and staged copies under `EmailIntelligence/docs/actions/workflows` and `kaggle-notebooks-analysis/docs/actions/workflows`. These add session-cap handling and bounded create requests, and fix the deployed rebuild file's duplicate declarations, but they are not byte-identical to the deployed workflows. They still retain several logic defects documented in Section 11. A template is therefore not considered canonical merely because it is newer.

## 3. Evidence used

- Current workflow source and relevant commit history through `78e8041`.
- Local YAML parsing with PyYAML. All files parse as YAML; PyYAML's YAML 1.1 interpretation of `on` as a boolean is expected and is not a GitHub Actions error.
- Official Jules REST API documentation for sessions, states, sources, and activities. The API remains `v1alpha` and explicitly warns that definitions may change.
- A local conflicting-branch reproduction of the exact `git merge-tree` command.
- CodeRabbit CLI `0.6.4`, authenticated, reviewing committed workflow changes from `4e4b8dab` through `HEAD`.

## 4. Baseline-to-intent traceability

The Google and community implementations are comparison baselines, not target architectures. A difference must not be removed merely because it is nonstandard. Every repair must answer four questions:

1. What behavior did the baseline provide?
2. Why was that behavior rejected or changed?
3. What observable behavior was the custom workflow intended to provide instead?
4. Does the current implementation actually provide it without breaking the Jules or GitHub contracts?

Git history establishes two stages:

- Commit `2a6d8a8` introduced the five-workflow family. Review and force-review initially called `sanjay3290/jules-pr-reviewer@v1`; auto-fix, walkthrough, and conflict resolution were already custom higher-level workflows.
- Commit `3dbf907` deliberately removed the community reviewer from review and force-review and replaced it with direct API orchestration. Its stated reasons were the community action's 80 KB diff truncation and lack of the desired PR-discussion context. Later commits added source-PR stability monitoring and late-commit instructions.

No official Google or common community implementation provides this exact five-workflow family. Force review and walkthrough are custom capabilities. Conflict resolution deliberately differs from Google's generated conflict-detection convention by asking Jules to reimplement the PR intent on the current base after a stability watch.

### 4.1 Shared orchestration principles that must be preserved

The custom workflows collectively intend to:

- control session use through PR events and explicit labels rather than automatically invoke Jules for every possible event;
- call the Jules REST API directly so the workflow can build richer prompts, poll activities, post custom results, and coordinate labels/statuses;
- avoid placing a complete potentially truncated PR diff in the initial prompt;
- give Jules a changed-file inventory, then have it inspect relevant files individually in its repository sandbox;
- include bounded existing PR discussion and line-level review feedback while excluding circular bot output;
- use the actual PR base/head state and detect drift before producing stale work;
- distinguish automatic review from a manually forced review;
- provide walkthrough output as a maintained PR comment rather than a code-producing task;
- avoid spending a Jules session on conflict resolution while the source PR is still changing or once conflicts have resolved organically;
- produce a new PR for mutating operations, while review and walkthrough remain analytical;
- expose deterministic GitHub-side outcomes through labels, comments, PR reviews, and commit statuses.

Repairs may strengthen validation, safety, and API compatibility, but must not replace these principles with the simpler Google/community invocation model.

### 4.2 Review: community action to custom file-list-first reviewer

**Baseline behavior:** the initial workflow delegated review to `sanjay3290/jules-pr-reviewer@v1`, which obtained a PR diff, truncated large input, created a non-mutating Jules review session, parsed a structured verdict, and set `jules/review`.

**Reason for divergence:** avoid the 80 KB whole-diff limit, let Jules inspect files selectively, incorporate recent human discussion/review comments, and own posting/status behavior locally rather than depend on a third-party action.

**Intended custom behavior:** on eligible same-repository PR activity, create one analytical session against the exact PR head; provide base/head identity plus all changed-file names; instruct Jules to diff selected files against the base; include recent non-circular feedback; retrieve the final review; post it as a PR review; and map the exact verdict to `jules/review`.

**Current verdict:** **not successful end-to-end**. The third-party action was removed and the richer context/status path was implemented, so the architectural change occurred. However, the session starts from the base rather than the PR head, the diff instruction compares the base to itself, polling uses an invalid resource URL, and activity extraction uses nonexistent fields. The custom reviewer therefore cannot reliably see or return the review it was designed to produce.

**Repair constraint:** retain direct API orchestration and file-list-first inspection. Do not restore the community action or embed the full diff. Start from the immutable PR head, fetch/compare the base explicitly, and restore documented API polling/output handling.

### 4.3 Force review: explicit override of automatic-review exclusions

**Baseline behavior:** the initial force-review workflow reused the same community reviewer behind a `jules-force-review` label and removed the label afterward.

**Reason for divergence:** keep the custom review strategy while allowing a maintainer to review PRs intentionally excluded from automatic review, especially Jules-authored branches.

**Intended custom behavior:** use the same output contract and review quality as automatic review, but trigger only by label and do not apply the automatic `jules-*` branch exclusion. Consume the label exactly once and avoid duplicate sessions.

**Current verdict:** **partially implemented but functionally blocked** by the same session URL, activity schema, and base/head context defects as automatic review. It also lacks sufficient concurrency/idempotency protection.

**Repair constraint:** share behavior conceptually with review while preserving the trigger/exclusion difference. A repair must not make force-review subject to automatic review's Jules-branch skip.

### 4.4 Auto-fix: PR-feedback-driven repair rather than generic CI failure fixing

**Google baseline behavior considered:** Google's invocation examples create an `AUTO_CREATE_PR` session from a selected branch, commonly after a failed CI run, with a prompt and optional commit context.

**Reason for divergence:** trigger a targeted repair only when a maintainer labels an existing PR; include that PR's title, body, changed-file inventory, human discussion, and line-level review findings; and avoid automatic session consumption on every CI failure.

**Intended custom behavior:** create exactly one new repair PR whose starting point includes the labeled PR's current implementation, apply only the requested/reviewed fixes, verify them, and avoid losing or duplicating late commits.

**Current verdict:** **the label/context customization exists, but branch semantics do not satisfy the intent**. The session starts from the target/base branch, so Jules does not begin with the existing PR changes it is supposed to fix. Its `git diff target` instruction is clean from that starting point, and the late-commit check watches the target rather than the PR head.

**Repair constraint:** preserve label gating, selective file inspection, feedback context, and `AUTO_CREATE_PR`. Unless a contrary product requirement is documented, start from the current PR head and pin its SHA so the generated repair is layered on the code under review.

### 4.5 Walkthrough: custom non-mutating reviewer's guide

**Baseline behavior:** no authoritative Google or common community Jules workflow provides this label-triggered PR walkthrough capability.

**Reason for addition:** generate a reviewer-oriented narrative, architecture decisions, and conditional diagrams on demand; update one durable PR comment instead of creating code changes.

**Intended custom behavior:** from the exact PR head, inspect changed files relative to the base, include useful non-circular discussion, generate a complete final walkthrough, upsert the marker comment, and consume the trigger label without creating a PR.

**Current verdict:** **custom capability exists but cannot reliably work**. It starts from the base with only file metadata, uses invalid polling and activity extraction, enables `AUTO_CREATE_PR` despite being analytical, and can include its own prior output as feedback.

**Repair constraint:** keep the label-triggered upserted walkthrough and diagram heuristics. Remove PR automation, provide correct head/base context, and extract the documented final agent message.

### 4.6 Conflict resolution: stable-source reimplementation on current base

**Google/community baseline behavior considered:** conventional workflows detect a merge conflict through a trial merge or conflict tool and report it; they do not implement this repository family's stability watch plus Jules reimplementation strategy.

**Reason for divergence:** avoid spending a session while commits are still arriving, recheck whether conflicts disappeared organically, and—only if still necessary—ask Jules to understand the source PR's intent and reimplement it cleanly on the latest base instead of mechanically choosing conflict sides.

**Intended custom behavior:** correctly detect conflicts; watch and pin the source head; refresh both refs; skip session creation if now clean; otherwise create exactly one `AUTO_CREATE_PR` session from the current base with enough source-head context to reproduce only still-valid changes.

**Current verdict:** **the stability and reimplementation architecture is present, but its entry condition is broken**. The `git merge-tree | grep '^@@'` test classifies reproduced conflicts as clean, so the custom path is normally bypassed. If reached, late-commit instructions to rebase a base-derived reimplementation onto the original conflicting head contradict the reimplementation model.

**Repair constraint:** retain the stability watch, organic-resolution skip, and current-base reimplementation strategy. Use `merge-tree` exit status for detection and adopt a pin-and-restart policy on later head/base movement rather than rebasing the reimplementation onto the conflicting source branch.

### 4.7 Cross-repository identity versus repository-specific policy

Byte-identical orchestration across repositories is not itself a failure: one custom implementation was deliberately propagated through matching commits. The success test is whether the shared mechanics work against dynamic repository, base, head, SHA, labels, and Jules source values.

Repository-specific review knowledge is a separate layer. If specialized review criteria were part of the intended work, that layer is absent: the three complete workflow sets contain no repository-specific rules. It should be supplied through trusted base-branch policy files or bounded prompt sections, without forking the API/session mechanics unless branch topology truly differs.

EmailIntelligence is a separate completeness question. Its current `scientific` checkout contains only auto-fix and conflict resolution. That does not show that those two files are standard; they are the same custom files. It does show that review, force-review, and walkthrough were not propagated to that checkout. Whether this was originally intentional because Gemini covered those roles must be resolved before adding the repaired files.

### 4.8 Acceptance rule for every proposed change

Before implementation, each edit must be classified as one of:

- **Contract repair:** required to make the intended custom behavior conform to the current Jules/GitHub API, such as resource paths and activity fields.
- **Intent repair:** required because the implementation contradicts its stated custom behavior, such as starting a PR review from the base branch.
- **Safety hardening:** preserves behavior while preventing injection, duplicate sessions, stale results, fork failures, or unbounded calls.
- **Policy change:** alters when Jules runs, what it is allowed to produce, or what constitutes success. These changes require explicit approval and must not be smuggled in as bug fixes.

The implementation review must reject any edit whose only justification is “this matches Google/community convention.”

## 5. Confirmed issues

### P0: polling constructs invalid Jules session URLs

Affected: review, force-review, walkthrough.

The create call extracts `.id`, for example `31415926535897932384`, but polling calls:

```text
GET /v1alpha/${SESSION_ID}
GET /v1alpha/${SESSION_ID}/activities
```

The API requires:

```text
GET /v1alpha/sessions/${SESSION_ID}
GET /v1alpha/sessions/${SESSION_ID}/activities
```

As written, successful session creation is followed by repeated 404 responses interpreted as `UNKNOWN`, ending in a timeout. This prevents the review/walkthrough result from being posted correctly.

Options:

- **A — recommended:** extract `.name` (the canonical `sessions/{id}` resource name), validate it against `^sessions/[^/]+$`, and call `/v1alpha/${SESSION_NAME}` and `/v1alpha/${SESSION_NAME}/activities`.
- **B:** retain `.id` and add `/sessions/` to every subsequent URL.
- **C:** accept `.name` with a fallback to `"sessions/" + .id` for alpha API compatibility. This is the most tolerant option but adds a small amount of parsing logic.

Recommendation: option C while the API is alpha, with strict rejection if neither value is valid.

### P0: activity output extraction uses fields that do not exist

Affected: review, force-review, walkthrough.

The workflows currently select activities with `.type == "agentMessaged"` and read `.message`. The official activity union has no `type` field. Agent output is represented as:

```json
{
  "agentMessaged": {
    "agentMessage": "..."
  }
}
```

The current `jq` expression therefore always falls back to `Review unavailable` or `No message`, even if a session completed and returned a valid final message.

Options:

- **A — minimum:** select activities where `.agentMessaged.agentMessage` is present and read that value.
- **B — recommended:** request up to 100 activities, sort/select by `createTime`, and read the last non-empty `.agentMessaged.agentMessage`.
- **C:** follow `nextPageToken` until all activities are read, then select the newest agent message. This is maximally correct but likely unnecessary for short review sessions.

Recommendation: option B initially; add pagination only if observed sessions exceed 100 activities.

### P0: review and walkthrough sessions do not reliably contain the PR changes

Affected: review, force-review, walkthrough; auto-fix is related.

Review and force-review create a Jules session with `startingBranch: baseRef`, omit the PR number and head branch from the prompt, and instruct Jules to run `git diff ${baseRef} -- <filepath>`. A session cloned at the base branch has no working-tree diff from that same base. The changed-file names supplied by the GitHub API do not provide file content or the PR patch.

Walkthrough also starts from the base branch and gives only changed-file metadata, so its requested architectural explanation can be based on unchanged base files rather than the PR implementation.

Auto-fix names the head branch but also starts from the target/base branch and uses the same base-relative diff instruction. If “auto-fix” is intended to repair the existing PR, this instead creates a separate change from the base without first loading the PR's current code.

Options:

- **A — recommended for same-repository PRs:** start Jules from `pr.head.ref`; include PR number, head ref, head SHA, base ref, and explicit `git diff origin/${baseRef}...HEAD -- <filepath>` instructions. Fetch/verify the base before diffing.
- **B:** continue starting from the base, but instruct Jules to fetch `pr.head.ref` and diff `origin/${baseRef}...origin/${headRef}`. This depends on Jules having remote branch access and is more error-prone.
- **C:** embed patches in the prompt. This avoids branch ambiguity but reintroduces prompt-size/truncation problems and is unsuitable for large PRs.

Recommendation: option A for review, force-review, walkthrough, and auto-fix. Review/walkthrough sessions should use no PR automation because they are read-only. Auto-fix should start from the PR head if the desired result is a follow-up PR containing fixes on top of the current PR; alternatively, the product decision can explicitly retain base-start behavior and rename/reword the workflow as “reimplement fix from base.”

### P0: merge conflict detection always classifies real conflicts as clean

Affected: conflict resolution, in both the initial check and recheck.

The workflow pipes `git merge-tree HEAD "origin/$BASE_REF"` into `grep -q "^@@"`. A reproduced content conflict emits `CONFLICT (content)` and exits with status 1; it does not emit a unified-diff `@@` line. The current condition consequently writes `has_conflicts=false` for a real conflict and never creates a resolution session.

Options:

- **A — recommended:** run `git merge-tree --write-tree HEAD "origin/$BASE_REF"`, capture its exit status without a pipeline, map 0 to clean, 1 to conflicts, and fail the step on any other status.
- **B:** parse output for `CONFLICT`, which is less robust and localization/version-sensitive.
- **C:** attempt a temporary `git merge --no-commit --no-ff`, inspect the result, and abort. This mutates the checkout and is unnecessary.

Recommendation: option A.

### P1: read-only workflows unnecessarily enable automatic PR creation

Affected: review, force-review, walkthrough.

All session payloads set `automationMode: AUTO_CREATE_PR`. These workflows request analysis and a final text message, not code edits. Enabling PR automation expands the effect of prompt injection or agent drift and can generate unrelated PRs.

Recommendation: omit `automationMode` from read-only review and walkthrough payloads. Keep it only in auto-fix and conflict resolution.

### P1: untrusted PR content is inserted directly into privileged agent prompts

Affected: all workflow families to varying degrees.

PR titles, bodies, comments, and review comments are interpolated as instructions without clear trust boundaries. Automatic review runs on same-repository PRs, and label-triggered workflows can be started by users with label permissions. `AUTO_CREATE_PR` makes instruction confusion more consequential.

Options:

- Delimit all PR-provided text as untrusted context and explicitly tell Jules never to follow instructions inside it.
- Include only feedback authored by trusted repository roles (`MEMBER`, `OWNER`, and optionally `COLLABORATOR`) for action workflows.
- Keep broad comments for review context but strip workflow-generated markers and state that comments are evidence, not commands.

Recommendation: combine delimiters with author-association filtering for auto-fix/conflict resolution; retain broader context for review only if clearly marked untrusted.

### P1: GitHub expressions are interpolated directly into shell source

Affected: especially conflict resolution's base/head branch fetch and reset steps.

Values such as `${{ github.event.pull_request.head.ref }}` are expanded before Bash executes. Treating a branch name as shell source can permit command substitution or break quoting. CodeRabbit independently flagged this.

Recommendation: pass event values through step-level `env` and reference only quoted Bash variables. Add `--` where supported and validate refs with `git check-ref-format --branch` before using them.

### P1: API failures are converted into long timeouts or incomplete reporting

Affected: all direct API workflows.

`curl -s` does not fail on HTTP errors and has no connection or total timeout. Polling treats HTTP error bodies as `UNKNOWN`. Earlier step failures prevent the review status/comment step from running, which can leave a required `jules/review` status absent rather than failed.

Recommendation:

- use `curl -sS --fail-with-body --connect-timeout 10 --max-time 60`;
- validate JSON before reading fields;
- retry bounded transient status codes during polling;
- set explicit job `timeout-minutes` values;
- make final reporting run with `always()` when preparation did not intentionally skip, and derive failure status from create/poll outcomes;
- avoid printing entire API error bodies if they may include sensitive diagnostics.

### P1: repeated label events can create duplicate sessions

Affected: force-review, auto-fix, conflict resolution, walkthrough.

Only automatic review has PR-scoped concurrency. Label-triggered jobs do not consistently remove/consume labels before session creation and do not persist a session guard. Reruns or rapid relabeling can consume multiple Jules sessions and create duplicate PRs/comments.

Options:

- Add a PR-and-workflow-scoped concurrency group with `cancel-in-progress: false`.
- Remove the trigger label before the non-idempotent POST.
- Search for a durable marker containing a session resource name before creating a session.
- Use all three for robust idempotency.

Recommendation: use all three for auto-fix and conflict resolution; concurrency plus label consumption is sufficient for review/walkthrough if duplicate creation remains observable through a marker comment.

### P1: fork behavior is inconsistent and mostly fails late

Affected: auto-fix, conflict resolution, walkthrough.

Review workflows explicitly skip forks. Other workflows attempt to check out/fetch the head ref from `origin` and later call Jules with a secret that is unavailable to `pull_request` events from forks. Conflict resolution also assumes the head branch exists in the base repository.

Recommendation: detect forks before checkout/session creation, post a clear trusted-token-free notice where permissions permit, remove/consume the trigger label, and exit without calling Jules. Do not switch to `pull_request_target` because that would increase secret and checkout risk.

### P1: review status fails open when no verdict can be parsed

Affected: review and force-review.

If a session is marked completed but no valid `VERDICT:` token is extracted, status defaults to success. An API schema mismatch, truncated result, or malformed model response can therefore satisfy a required status without a usable review.

Recommendation: treat a missing/unknown verdict as an error or neutral/pending outcome according to the desired branch-protection policy. If only success/failure statuses are used, fail closed with `failure` and a clear description.

### P2: GitHub API pagination and ordering are inconsistent

Affected: all workflow families.

- `pulls.listFiles` is not paginated and defaults to the first 30 files, making file counts, changed-file context, and large-PR strategy incomplete.
- Issue-comment listing does not support the supplied `direction` argument; slicing the returned array can retain the oldest comments instead of the newest.
- Walkthrough searches only the first page for its existing marker and can create duplicate comments.
- Marker filters differ: walkthrough does not exclude its own `<!-- jules-walkthrough -->` marker.

Recommendation: use `github.paginate` for changed files and marker lookup; explicitly sort filtered comments by `created_at` descending before taking 10; centralize the same marker list text in each file (without introducing a cross-workflow helper).

### P2: late-commit instructions do not match the branch model

Affected: auto-fix and conflict resolution.

Auto-fix currently starts on the target branch but checks only whether that target advanced, not whether the labeled PR head advanced. Conflict resolution starts on the base and reimplements source changes, then instructs Jules to rebase the reimplementation onto `origin/${headRef}`. Rebasing a base-derived reimplementation onto the original conflicting head can duplicate the very changes being reimplemented or restore the conflict.

Options for conflict resolution:

- **A — recommended:** after the stability watch, pin the latest head SHA in the prompt. Jules starts from the current base and reimplements the delta from the pinned head. Before submission, fetch both refs; if either moved, stop and report that a fresh session is required rather than attempting an unsafe automatic rebase.
- **B:** start from the PR head and merge/rebase the current base, resolving conflicts in place. This preserves commit history more directly but may be harder for Jules and creates a new PR from a derived branch.
- **C:** keep the current reimplementation strategy but recalculate the original delta after a late head commit and reapply only the new delta. This is correct but prompt logic is complex.

Recommendation: option A for deterministic behavior and lower risk.

### P2: workflow cleanup and result semantics are inconsistent

- Force-review removes its label under `always()`, while walkthrough does not; auto-fix and conflict resolution do not consistently consume theirs.
- Walkthrough can post a timeout/failure text while the workflow itself succeeds.
- Failed sessions still attempt to extract an agent message without preferring failure details.
- `actions/checkout` is unused by payload-building steps in some workflows and can fail before a fork skip.

Recommendation: define per-workflow terminal semantics in the implementation: which failures should fail the check, which should post a comment, and when labels are removed. Remove checkout only where no local shell/git operation uses it.

## 6. CodeRabbit findings and disposition

CodeRabbit reported 12 findings. The following are accepted and incorporated above:

- session resource path mismatch;
- final review reporting should handle earlier failures;
- fork restrictions for conflict resolution;
- PR-scoped concurrency and duplicate-session guard;
- invalid `merge-tree`/`@@` conflict detection;
- moving GitHub expression values into `env` before shell use;
- bounded, failure-aware `curl` calls;
- walkthrough should filter its own marker;
- issue-comment ordering must not rely on unsupported `direction`;
- full pagination for walkthrough marker lookup;
- explicit job/API timeouts.

CodeRabbit also suggested removing walkthrough's checkout because the current payload build is API-driven. This is valid under the current base-branch design, but the recommended repair changes the Jules session to start from the PR head; the runner checkout is still not required for that API payload, so removal remains appropriate after fork detection is moved before any secret-dependent operation.

Important defects found independently and not surfaced by CodeRabbit include the invalid activity JSON path, missing PR-head context, inappropriate `AUTO_CREATE_PR` on read-only sessions, fail-open verdict parsing, incomplete changed-file pagination, and unsafe late-commit branch logic.

## 7. Recommended implementation sequence

### Phase 1: restore core API correctness

1. Normalize and validate the session resource name returned by create calls.
2. repair polling and activities URLs.
3. repair the activity `jq` path and select the latest agent message.
4. add HTTP failure handling, bounded timeouts, and JSON validation.
5. make terminal reporting reflect create/poll/API failures.

This phase should be implemented and tested before prompt or branch behavior changes so API transport failures are separable from agent-task failures.

### Phase 2: correct branch and prompt semantics

1. Include PR number, base ref, head ref, and immutable head SHA in every PR prompt.
2. start review, force-review, walkthrough, and (subject to the product decision) auto-fix sessions from the PR head.
3. use explicit three-dot base-to-head diff commands.
4. remove `AUTO_CREATE_PR` from read-only sessions.
5. mark PR content and comments as untrusted context.
6. replace unsafe conflict-resolution late-commit rebase instructions with a pin-and-restart policy.

### Phase 3: repair conflict detection and event safety

1. use `git merge-tree --write-tree` exit codes for both checks.
2. pass refs through `env`, validate them, and quote them.
3. skip forks consistently.
4. add label-workflow concurrency, label consumption, and durable duplicate guards.

### Phase 4: consistency and scale

1. paginate changed files and marker searches.
2. sort comments explicitly and align marker filters.
3. define uniform timeout/failure/cleanup behavior.
4. remove truly unused checkouts and outputs.

### Phase 5: propagate only after representative validation

1. copy the validated five-file set to `gemini-cli-prompt-library` and `kaggle-notebooks-analysis`.
2. confirm checksums remain identical after copying.
3. port only shared auto-fix/conflict fixes to `EmailIntelligence` first.
4. review `EmailIntelligence`'s distinct Gemini/review workflows separately instead of overwriting them.

## 8. Validation plan

### Static validation

- Run an Actions-aware validator such as `actionlint` once made available through `mise`; do not install it with an unmanaged package command.
- Parse YAML and inspect GitHub expressions.
- Run `shellcheck` on extracted `run:` scripts where practical.
- Run `git diff --check`.
- Verify no literal secrets or API keys appear in the diff.

### Deterministic local tests

- Fixture-test session responses containing `.name`, `.id`, malformed JSON, and HTTP errors.
- Fixture-test activity responses containing multiple `agentMessaged.agentMessage` entries and no agent message.
- Re-run the temporary conflicting-branch test and confirm status 1 maps to `has_conflicts=true`, status 0 maps to false, and other statuses fail.
- Generate payloads for representative same-repo and fork PR event fixtures and assert branch, SHA, source, prompt boundaries, and automation mode.
- Test a PR with more than 30 changed files and more than 30 comments.

### GitHub/Jules smoke tests

Use a disposable PR and labels, not a production change:

1. trigger walkthrough and verify the session starts from the PR head and posts the real final agent message;
2. trigger review and verify a valid verdict maps to the expected `jules/review` status;
3. force an API error and verify bounded failure plus a failed status/comment;
4. trigger a known merge conflict and verify exactly one resolution session is created;
5. relabel/rerun and verify the idempotency guard prevents duplicates;
6. verify a fork PR exits without secret use or misleading success.

## 9. Decisions required before implementation

1. **Auto-fix branch model:** should it repair on top of the current PR head (recommended), or intentionally reimplement the requested fix from the base into a separate PR?
2. **Review failure policy:** should missing verdict/API failure fail a required check (recommended) or remain advisory?
3. **Conflict-resolution drift:** should any late base/head movement restart the session (recommended) or attempt an automated rebase?
4. **Trusted feedback:** should action workflows accept only member/owner comments, or also collaborator comments?
5. **Rollout:** apply the repaired shared set to all three identical repositories in one pass after smoke testing, or stage one repository at a time?

## 10. Proposed definition of done

- All five representative workflows pass Actions-aware syntax validation.
- Review/walkthrough sessions operate on the immutable PR head and compare it to the intended base.
- Jules session polling uses valid resource names and bounded HTTP requests.
- Final agent output is extracted from the documented activity schema.
- Conflict checks correctly distinguish clean, conflicting, and command-error outcomes.
- Read-only workflows cannot create PRs.
- Fork and duplicate-trigger behavior is explicit and safe.
- Failure states cannot be reported as successful reviews.
- Representative smoke tests pass before byte-identical propagation to the other repositories.

## 11. Evolved-workflow regression audit (2026-07-20)

This section supersedes any historical “current verdict” above. The earlier sections are retained to show which defect each change was intended to repair and why the custom architecture exists.

### 11.1 Design evidence and changed decisions

`jules/docs/actions/workflows/CHANGELOG.md` confirms that the following are deliberate product behavior, not deviations to normalize back to Google/community examples:

- file-list-first inspection exists to avoid the community reviewer's 80 KB full-diff truncation;
- recent PR discussion and review comments are intended to be bounded prompt context;
- workflow markers are intended to prevent circular agent context;
- force review must not inherit automatic review's Jules-branch exclusion;
- walkthrough is analysis-only and maintains one marker comment;
- conflict resolution waits for a stable source PR, spends no session if conflicts disappear, and reimplements still-valid intent on the current base;
- auto-fix and conflict resolution are intended to survive late changes while conserving sessions.

Subsequent git history also records intentional evolution beyond the original changelog:

- commit `bec95a6` changed auto-fix from base/target start to PR-head start so fixes layer on the implementation under review;
- commit `771be25` separated read-only prompts from mutating prompts;
- mutating workflows now omit `AUTO_CREATE_PR` and explicitly instruct Jules to push/create a PR (or, for rebuild, push the existing branch). This is compatible with the current Jules API: omitted `automationMode` means no automatic PR.

These changes resolve the old ambiguity in Sections 4.4 and 8: PR-head auto-fix is now the documented implementation decision and should be preserved. The conflict resolver's base-start reconstruction is also intentional. However, documenting “rebase onto the source head” does not make that command correct: the source head is not the ancestor of the reconstructed branch, so the command cannot distinguish original source commits from late commits and can reintroduce the conflict.

### 11.2 Current official API contract

The official Jules REST reference remains available at `https://developers.google.com/jules/api/reference/rest/v1alpha/sessions` and confirms:

- `POST /v1alpha/sessions` returns `name: "sessions/{session}"` and a bare `id`;
- get-session is `/v1alpha/sessions/{session}`;
- activities are `/v1alpha/sessions/{session}/activities`;
- agent text is represented by `agentMessaged.agentMessage`;
- `githubRepoContext.startingBranch` is required;
- omitted or unspecified `automationMode` defaults to no automation;
- `AUTO_CREATE_PR` automatically creates a PR only when a final patch is generated.

The endpoint is therefore not currently deprecated in the way suspected for the separate Gemini endpoint. No Jules workflow should be removed or reverted on that basis.

### 11.3 Regression matrix

| Previously identified defect                 | Current status                               | Evidence and interpretation                                                                                                                                                                                    |
| -------------------------------------------- | -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Malformed session polling/activity URLs      | **Fixed**                                    | Pollers use `.name`, fall back to `sessions/${id}`, and call `/v1alpha/${SESSION_RESOURCE}`.                                                                                                                   |
| Wrong activity schema                        | **Fixed**                                    | Pollers select `.agentMessaged.agentMessage` and tolerate a missing activities array.                                                                                                                          |
| Review/walkthrough missing PR-head code      | **Fixed**                                    | Review, force-review, walkthrough, and auto-fix now start from `pr.head.ref`/`headRef`.                                                                                                                        |
| Broken conflict detector                     | **Resurfaced in a new form**                 | `merge-tree --write-tree` is correct, but Actions invokes Bash with `-e`; exit 1 terminates before `case $?` writes `has_conflicts=true`. A local exact-shell reproduction exited 1 without reaching the case. |
| Read-only workflows use `AUTO_CREATE_PR`     | **Fixed**                                    | Review, force-review, walkthrough, and rebuild analysis omit it; official API default is no automatic PR.                                                                                                      |
| First-30-files truncation                    | **Fixed**                                    | All changed-file inventory paths use `github.paginate`.                                                                                                                                                        |
| HTTP errors become long `UNKNOWN` loops      | **Partially fixed**                          | Poll GETs use `--fail-with-body` and bounds, but one transient error terminates the step and prevents terminal reporting.                                                                                      |
| Duplicate label sessions                     | **Partially fixed**                          | Concurrency and early label removal were added, but every removal error is swallowed; a duplicate/rerun can continue into another non-idempotent POST.                                                         |
| Fork handling                                | **Partially fixed**                          | Several builders detect forks, but auto-fix/walkthrough check only after checkout; conflict resolution has no fork guard; rebuild's second job is not gated by the first job's skip.                           |
| Shell injection through event refs           | **Partially fixed**                          | Runner shell steps now use quoted `env` values. Prompt-generated shell commands still interpolate unvalidated refs and titles.                                                                                 |
| Circular marker filtering                    | **Partially fixed**                          | Walkthrough's own marker was added where needed, but marker sets omit newer `jules-rebuild`, `jules-quota-exhausted`, and other workflow outputs or differ by file.                                            |
| Wrong newest-comment selection               | **Resurfaced / not fixed**                   | `issues.listComments` does not support `direction`; returned comments remain oldest-first before `.slice(0, 10)`. Review-comment ordering is separate and valid.                                               |
| Late-commit/start-branch mismatch            | **Partially fixed**                          | Auto-fix now starts on the PR head and checks target drift, but does not pin/check source-head drift. Conflict resolution still tells a base reconstruction to rebase onto the original conflicting source.    |
| Missing bounded HTTP calls                   | **Partially fixed**                          | Deployed session-creation POSTs remain unbounded; newer templates add POST bounds. No family has explicit job `timeout-minutes`.                                                                               |
| Missing concurrency/idempotency              | **Partially fixed**                          | PR-scoped concurrency exists, but there is no durable pre-POST marker/session guard.                                                                                                                           |
| Fail-open verdict behavior                   | **Partially fixed, with a new contract bug** | Missing/unknown verdict defaults to failure, but the prompt's required literal example is `[VERDICT]: approve`; the parser accepts the first marker, so unchanged template text can approve a review.          |
| Untrusted PR content treated as instructions | **Resurfaced / not fixed**                   | PR bodies, comments, review comments, and PR-head rule files enter privileged prompts without author filtering or explicit data boundaries.                                                                    |

### 11.4 New blockers introduced by the evolved workflows

#### A. Deployed rebuild cannot compile

The deployed `jules-pr-rebuild.yml` declares `const fs = require('fs')` twice in each of its two GitHub Script payload builders. JavaScript rejects both functions before execution. A local `AsyncFunction` compilation check reproduced both failures.

Options:

- **A — recommended:** remove the second declaration in each function and reuse the first binding.
- **B:** move one declaration to the top of each function. This is equivalent but creates a larger diff.

The newer documentation/template copy already implements option A. That correction should be ported to the deployed family after the broader patch is validated.

#### B. Address-comments is a no-op

`pulls.listReviewComments` returns review-comment records, not review-thread state. Those records do not have `state: PENDING`; that state belongs to pull-request review records. Filtering every comment with `rc.state === 'PENDING'` therefore produces an empty list and the workflow never tags Jules.

Options:

- **A — recommended:** use GitHub GraphQL `pullRequest.reviewThreads`, paginate threads/comments, filter `isResolved == false`, and reply once to the relevant unresolved thread.
- **B:** react only to the triggering `pull_request_review_comment` event without trying to infer resolution. This is smaller but can re-address already-resolved or superseded threads and does not satisfy the stated “all unresolved threads” design.
- **C:** process all REST review comments. Reject because REST comments cannot reliably represent thread resolution and can duplicate replies.

The newer template adds prior Jules marker context but retains the invalid `rc.state` filter, so it does not fix the blocker.

#### C. Automerge trusts a branch-name convention as identity

The hourly workflow adds `automerge` when either the author login equals `jules` or the head branch begins `jules-`. A fork author controls their branch name and can satisfy the second test. If Mergify or repository rules trust this label, the workflow elevates an untrusted naming convention into merge authorization. It also reads only the first 100 open PRs.

Options:

- **A — recommended minimum:** paginate open PRs, require a same-repository head, and require a trusted Jules bot/app identity or a trusted provenance label written by a privileged workflow.
- **B:** require only the trusted Jules account/app identity and remove branch-prefix trust. This is safest if all valid Jules PRs have stable author identity.
- **C:** retain branch-prefix matching but require same-repository head. This blocks fork spoofing but still lets any repository writer create a matching branch, so it is weaker than A/B.

#### D. Rebuild write phase is not gated by valid analysis

The analysis poll exits successfully for both `COMPLETED` and `FAILED`, and timeout also leaves a text file. The second job has no dependency condition for fork skip or successful analysis. Once the syntax blocker is removed, it can start a write session using “Analysis unavailable” or timeout text, and can reach a fork-incompatible checkout.

Options:

- **A — recommended:** expose `skip` and `session_state` as analyze-job outputs and require same-repository PR plus `session_state == COMPLETED` before the rebuild job. Reject empty/placeholder analysis.
- **B:** collapse both phases into one job so step outputs directly gate the write phase. This simplifies gating but is a larger structural change and loses intentional two-job separation.

#### E. Repository rules silently fail to load in auto-fix and conflict resolution

Both scripts call `fs.existsSync` before a later lexical `const fs` declaration. The resulting temporal-dead-zone `ReferenceError` is swallowed by the optional-file `catch`, so the workflow runs but silently omits repository rules. The divergent `gemini-cli-prompt-library` review copy has a more severe duplicate declaration and cannot compile.

Options:

- **A — minimum contract repair:** move `const fs = require('fs')` before first use and remove the later declaration.
- **B — recommended trust repair:** read rule files from the trusted PR base SHA/ref via the GitHub API, preserving file priority. This avoids treating a PR-head policy file as privileged instructions.

#### F. Review prompt can manufacture an approval

Review and force-review tell Jules to reproduce a template containing the literal line `[VERDICT]: approve`, then parse the first matching verdict marker. This is not a neutral example: a model that follows the template without replacing the value can approve despite findings.

Options:

- **A — recommended:** use `[VERDICT]: <approve|comment|block>`, define the decision criteria, parse exactly one marker from the `## Verdict` section, and fail on zero or multiple markers.
- **B:** require a small JSON output object and parse it strictly. This is more robust but changes the human-readable output contract and requires careful separation from the posted review.

### 11.5 Validation evidence

- PyYAML parsed every current deployed workflow in all four repositories.
- `actionlint v1.7.7` found no Actions YAML/expression error in the representative eight-file set or newer template set; it reported only one unused loop variable warning in rebuild and one redirect style warning in walkthrough. Actions-aware YAML validation alone does not compile embedded GitHub Script JavaScript.
- A separate Node `AsyncFunction` compile check found both deployed rebuild duplicate declarations and the divergent `gemini-cli-prompt-library` review duplicate declaration.
- A temporary conflicting git fixture confirmed `git merge-tree --write-tree` returns 1 and prints `CONFLICT`; running the workflow's exact command/case sequence under `bash --noprofile --norc -e -o pipefail` exits before the case.
- CodeRabbit CLI `0.6.5` reviewed the evolved committed eight-file family from `2a6d8a8` and returned 19 findings. It independently confirmed automerge trust/pagination, label idempotency, fork timing, trusted rules loading, POST timeouts, auto-fix's `fs` ordering, issue-comment ordering, rebuild syntax/gating, and address-comments' nonexistent `state` field. It did not catch the `bash -e` conflict regression, so that local reproduction remains necessary evidence.

## 12. Revised implementation plan

No workflow edits should be propagated until Phase 1 passes deterministic validation. Every change below preserves the custom architecture and is classified as contract repair, intent repair, or safety hardening—not a return to Google/community defaults.

### Phase 1 — restore executable core paths

1. Repair both conflict checks using `if git merge-tree ...; then ... else rc=$? ... fi`; reject unexpected statuses. Prefer this to broad `set +e` because it suppresses `errexit` only for the expected status-producing command.
2. Remove both duplicate `fs` declarations in deployed rebuild.
3. Move/fetch `fs` correctly for auto-fix and conflict resolution; use trusted-base GitHub API loading if included in the same patch.
4. Replace address-comments' REST `state` filter with paginated GraphQL review threads.
5. Neutralize the verdict template and make parser cardinality/section checks fail closed.

Acceptance checks:

- all GitHub Script bodies compile as async JavaScript;
- conflict fixture maps exit 0 to clean, 1 to conflict, and all other values to failure;
- address-comments fixtures distinguish resolved and unresolved threads;
- verdict fixtures reject zero, duplicate, contradictory, and placeholder markers.

### Phase 2 — make mutation and trust boundaries explicit

1. Harden automerge provenance and paginate open PRs.
2. Gate rebuild write phase on same-repository PR and completed, non-placeholder analysis.
3. Move fork classification before checkout in auto-fix and walkthrough; add it to conflict resolution; propagate it across rebuild jobs.
4. Treat only trusted repository-role feedback as instructions for mutating workflows. Keep other PR text as clearly delimited untrusted evidence.
5. Load repository policy from the trusted base, not the PR head.
6. Validate branch refs before placing them into generated shell examples; avoid interpolating PR titles into executable command text.

### Phase 3 — correct ordering, drift, markers, and idempotency

1. Paginate issue comments, sort by `created_at` descending, then filter and slice.
2. Align marker sets per workflow purpose, including rebuild and quota markers, while intentionally allowing walkthrough context only where the changelog requires it.
3. Make label removal an atomic claim: continue on successful removal; treat 404 as already consumed and skip; rethrow other errors.
4. Add a durable pre-POST marker/session guard for mutating workflows. Do not retry non-idempotent session creation blindly.
5. Pin the auto-fix source head SHA and detect both source-head and target movement.
6. Replace conflict resolution's source-head rebase with a pinned-SHA comparison. If the source moved, stop/restart reconstruction rather than replaying the original conflicting branch onto reconstructed work.

### Phase 4 — bounded transport and terminal reporting

1. Port bounded POST calls from the newer templates to deployed workflows.
2. Add explicit job `timeout-minutes` appropriate to watch plus poll duration.
3. Retry only idempotent GET/list operations for bounded transient failures.
4. Run review/force-review final reporting under `always()` after a non-skip prepare, derive status from create/poll state, and make required commit-status write failures visible.
5. Paginate activities or explicitly verify the API's page-order/limit guarantee before relying on the last item of the first 100.

### Phase 5 — validate one family, then reconcile repositories

1. Apply and validate the patch first in `gemini-fullstack-langgraph-quickstart`.
2. Run PyYAML, `actionlint`, embedded-JavaScript compilation, shell fixtures, prompt/verdict fixtures, and `git diff --check`.
3. Run CodeRabbit on the resulting diff and manually disposition each finding; do not execute reviewer-supplied commands automatically.
4. Smoke-test with disposable same-repository PRs: review, forced review, walkthrough, real merge conflict, address-comment thread, rebuild failure gating, relabel/rerun, and fork skip.
5. After validation, copy the same deployed files to `EmailIntelligence` and `kaggle-notebooks-analysis`, then verify checksums.
6. Reconcile `gemini-cli-prompt-library` separately against its five uncommitted files. Preserve user changes, add the three missing workflows only after repository policy is confirmed, and never overwrite its worktree wholesale.
7. Promote the validated deployed files back into `jules/docs/actions/workflows`; then update staged documentation copies so there is one traceable template family rather than competing “newer” copies.

### Revised definition of done

- The eight intended workflows are present where policy requires them and have a documented checksum/version map.
- Current official Jules resources, states, and activities are handled without relying on obsolete fields.
- Every embedded GitHub Script compiles before deployment.
- Real conflicts enter the stability/reconstruction path under Actions' actual Bash flags.
- Read-only sessions cannot create PRs; write sessions use their explicitly documented manual push/PR behavior.
- Address-comments operates on unresolved review threads rather than nonexistent REST state.
- Automerge cannot be granted from a spoofed fork branch name.
- Rebuild cannot write after skipped, failed, timed-out, or empty analysis.
- Verdict/status parsing cannot approve from example text or malformed output.
- Recent context is actually recent, marker filtering matches each workflow's intent, and untrusted content is data rather than policy.
- Fork, label replay, rerun, API failure, and late-commit behavior are deterministic and observable.
- Representative smoke tests pass before cross-repository propagation.
