# Types Reference

This page documents all data types used in the Jules REST API.

## Core Resources

### Session
A session represents a unit of work where Jules executes a coding task.
- `name`: Output only. The full resource name.
- `id`: Output only. The session ID.
- `prompt`: The task description for Jules to execute.
- `title`: Optional title.
- `state`: Output only. Current state of the session.
- `url`: Output only. URL to view the session in the Jules web app.
- `sourceContext`: The source repository and branch context.
- `requirePlanApproval`: Input only. If true, plans require explicit approval.
- `automationMode`: Input only. Automation mode for the session.
- `outputs`: Output only. Results of the session (e.g., pull requests).
- `createTime`: Output only. When the session was created.
- `updateTime`: Output only. When the session was last updated.

### SessionState (Enum)
- `STATE_UNSPECIFIED`
- `QUEUED`
- `PLANNING`
- `AWAITING_PLAN_APPROVAL`
- `AWAITING_USER_FEEDBACK`
- `IN_PROGRESS`
- `PAUSED`
- `FAILED`
- `COMPLETED`

### AutomationMode (Enum)
- `AUTOMATION_MODE_UNSPECIFIED`
- `AUTO_CREATE_PR`

### Activity
An activity represents a single event within a session.
- `name`: The full resource name.
- `id`: Output only. The activity ID.
- `originator`: 'user', 'agent', or 'system'.
- `description`: Output only. A description of this activity.
- `createTime`: Output only. When the activity was created.
- `artifacts`: Output only. Artifacts produced by this activity.
- `planGenerated`, `planApproved`, `userMessaged`, `agentMessaged`, `progressUpdated`, `sessionCompleted`, `sessionFailed`.

### Source
A source represents a connected repository.
- `name`: The full resource name.
- `id`: Output only. The source ID.
- `githubRepo`: GitHub repository details.

## Plans

### Plan
- `id`: Output only.
- `steps`: Output only.
- `createTime`: Output only.

### PlanStep
- `id`: Output only.
- `index`: Output only. 0-based index.
- `title`: Output only.
- `description`: Output only.

## Artifacts

### Artifact
- `changeSet`: Code changes produced.
- `bashOutput`: Command output produced.
- `media`: Media file produced.

### ChangeSet
- `source`: The source this change set applies to.
- `gitPatch`: The patch in Git format.

### GitPatch
- `baseCommitId`: The commit ID the patch should be applied to.
- `unidiffPatch`: The patch in unified diff format.
- `suggestedCommitMessage`: A suggested commit message.

### BashOutput
- `command`, `output`, `exitCode`.

### Media
- `mimeType`, `data` (Base64).

## GitHub Types

### GitHubRepo
- `owner`, `repo`, `isPrivate`, `defaultBranch`, `branches`.

### GitHubBranch
- `displayName`.

### GitHubRepoContext
- `startingBranch`.

## Context Types

### SourceContext
- `source`, `githubRepoContext`.

## Output Types

### SessionOutput
- `pullRequest`.

### PullRequest
- `url`, `title`, `description`.
