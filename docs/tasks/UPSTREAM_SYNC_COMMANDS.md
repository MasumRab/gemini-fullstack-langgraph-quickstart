# Upstream Sync Commands

**Goal:** Target specific relevant changes from `upstream/main` to cherry-pick into the local `main` branch, avoiding full merges that would revert architectural improvements.

## 1. Setup
Ensure the upstream remote is configured:
```bash
git remote add upstream https://github.com/google-gemini/gemini-fullstack-langgraph-quickstart
git fetch upstream
```

## 2. Identify Candidates
List commits in upstream that are not in your local history:
```bash
git log HEAD..upstream/main --oneline
```
*Note: This might show many commits if histories have diverged. Use `git diff HEAD upstream/main -- <filename>` to verify content differences.*

## 3. Specific Cherry-Pick Targets
*As of (Current Date), the following upstream commits have been analyzed:*

### A. Frontend Fixes (IME Support, UI Tweaks)
*   **Commit:** `3214a7e` (Merge PR #17 - Fix IME input)
*   **Status:** **ALREADY PRESENT** in HEAD. (Verified via `git diff`).
*   **Command (if needed in future):**
    ```bash
    git cherry-pick -m 1 3214a7e
    ```

### B. Prompt Updates
*   **Commit:** `e34e569` (Updates to prompt)
*   **Status:** **ALREADY PRESENT** or irrelevant. (Content matches).
*   **Command:**
    ```bash
    git cherry-pick e34e569
    ```

### C. Dependency Updates
*   **File:** `backend/pyproject.toml`
*   **Status:** HEAD includes strictly more dependencies (MCP). Upstream versions should be monitored.
*   **Command:** *Manual update recommended.*

## 4. Sync Workflow
To pick a specific new feature from upstream (e.g., a future bugfix `abc1234`):

1.  **Fetch:** `git fetch upstream`
2.  **Verify:** `git show abc1234`
3.  **Pick:**
    ```bash
    git cherry-pick abc1234
    ```
4.  **Resolve Conflicts:** If the file has been architecturally refactored (e.g., `graph.py` -> `nodes.py`), you must manually apply the logic change to the new file location.
