# Optimized Prompt for Context Awareness System

This document contains the reconstructed prompt that would have achieved the "Active Context" feature implementation efficiently in a single pass, avoiding common pitfalls like missing dependencies, path errors, and capitalization inconsistencies.

---

## The Request

**Role:** Senior DevOps & Tooling Engineer

**Task:** Implement a "Context Awareness System" to prevent our AI agents (Bolt, Sentinel, Palette) from duplicating work or creating code conflicts with currently open Pull Requests.

### 1. The Context Updater Script (`scripts/update_active_context.py`)
Create a robust Python script to fetch the current development state.

*   **Design Decision - NO CLI TOOLS:** You **must not** use the `gh` CLI tool. It is not guaranteed to be installed in all execution environments.
*   **Design Decision - NO SCRAPING:** Do not attempt to use Playwright or web scraping as a workaround if the API fails; it is too brittle.
*   **Dependencies:** Use Python's `requests` library and the official GitHub REST API.
*   **Repo Detection:**
    *   First check `GITHUB_REPOSITORY` env var.
    *   Fallback to `subprocess.run(["git", "config", ...])` (safely, no `shell=True`) to parse the remote URL.
*   **Authentication:** Read `GITHUB_TOKEN`.
*   **API Logic (Comprehensive Coverage):**
    *   Fetch **ALL** open PRs. You must implement **pagination** (follow `Link` headers or iterate pages) to ensure no PRs are missed.
    *   For **EVERY** PR, fetch the complete list of **modified files** (also paginated if the file list is large).
    *   **Robustness:** Use `timeout=10` for all requests. Handle `requests.RequestException` gracefully.
*   **Output:** Write to `docs/ACTIVE_CONTEXT.md`.
    *   Format: A Markdown list/table of PRs and their "locked" files.
    *   **Branding:** Use "GitHub" (Capital H) in all text.
*   **Degraded Mode (Graceful Failure):** Ensure the `docs/` directory exists (`os.makedirs`) before writing. If the `GITHUB_TOKEN` is missing, the system should degrade gracefully. Do not crash. Instead, write a clear placeholder: `*GitHub Token missing - Context unavailable*`. This signals to the agents that context is temporarily unavailable, allowing them to proceed blindly rather than halting execution entirely.

### 2. Backend Integration (`backend/src/agent/nodes.py`)
Update the agent's planning logic to read this context.

*   **File:** `backend/src/agent/nodes.py`
*   **Function:** `_get_active_context()`
*   **Path Resolution:** Use `pathlib.Path`. Resolve the path **relative to the module file** (e.g., `parents[3]`), NOT the current working directory.
*   **Safety:** **Truncate** the content to 4000 characters to prevent overflowing the LLM's context window.
*   **Injection:** Pass this context string into the `generate_plan` prompt.

### 3. Agent Task Prompts (`docs/tasks/`)
Create/Update the specific persona prompts to enforce the protocol.

*   **New Task:** `docs/tasks/05_ARCHIVIST_TASK.md` (Runs the update script).
*   **Updated Tasks:** `06_BOLT_TASK.md`, `07_SENTINEL_TASK.md`, `08_PALETTE_TASK.md`.
*   **Protocol:** Add a **"0. 🧠 KNOWLEDGE CHECK"** step to the top of the "Daily Process" for each agent:
    *   "READ `docs/ACTIVE_CONTEXT.md`."
    *   "CHECK if your target files are listed as modified."
    *   "IF LOCKED: **STOP** or choose a different task. Do not create conflicts."
*   **Consistency:**
    *   Journal paths must use lowercase `.jules/` (e.g., `.jules/palette.md`).
    *   Use hyphenated adjectives where appropriate (e.g., "High-priority issues").

### 4. Verification
*   **Unit/Integration Tests:**
    *   Add tests to `backend/tests/test_nodes.py` that:
        *   Mock the `ACTIVE_CONTEXT.md` file content.
        *   Assert that the prompt payload constructed in `generate_plan` **contains** the injected `active_context` content.
    *   Add integration tests for the script (mocking `requests`) to verify:
        *   **Pagination:** Mock a multi-page GitHub API response (using `Link` headers) and assert all files/PRs are aggregated.
        *   **Failures:** Assert correct handling of missing tokens and timeouts (Degraded Mode).
*   **Manual Verification:**
    *   Run the script locally to confirm it handles missing tokens without crashing.
    *   Check generated `docs/ACTIVE_CONTEXT.md` for correct formatting and capitalization.
