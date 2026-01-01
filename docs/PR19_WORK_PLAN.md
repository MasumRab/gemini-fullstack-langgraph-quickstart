# PR #19: MCP Persistence Wrapper - Work Plan

**Branch:** `jules-mcp-persistence-wrapper-2114800518725581450`
**Status:** Needs Review & Rebase

## Context
This PR introduces an MCP (Model Context Protocol) adapter for the persistence layer. Previous analysis indicated potential merge conflicts with `main` (approx 6 files).

## Action Items

- [ ] **Review Implementation**
    - Audit `backend/src/agent/mcp_config.py` (and related files)
    - Ensure it wraps existing persistence correctly without breaking changes.
    - [ ] **Fix Chunk ID Collisions in rag.py**: Add UUID to chunk IDs to prevent collisions.
    - [ ] **Complete MCP Async Stubs in mcp_config.py**: Implement `get_filesystem_tools` and add error handling.

- [ ] **Rebase & Resolve Conflicts**
    - Rebase current branch on `main`.
    - Fix expected conflicts in `backend/src/agent/nodes.py`, `rag.py`, etc.

- [ ] **Verification & Testing**
    - Run backend tests: `pytest backend/tests/`
    - [ ] **Update Test Assertions**: Fix `web_research_results` -> `web_research_result` and validation checks.
    - [ ] **Verify State Schema**: Ensure all nodes align with state keys.
    - Verify persistence still works (e.g., using `verify_agent_flow.py`).

- [ ] **Merge**
    - Once tests pass, merge to `main`.
