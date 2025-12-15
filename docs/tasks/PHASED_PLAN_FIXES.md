# Phased Plan: Backend-Frontend Connection & Visualization Fixes

## Issues Identified

### Major Blocking Issues
1.  **Backend Missing Dependency**: `duckduckgo-search` is mandatory for search nodes but was missing from `backend/pyproject.toml`.
2.  **Frontend Broken Dependency**: `@langchain/langgraph-sdk` version `0.0.28` has a known issue (missing `./react` export) preventing the dev server from starting.
3.  **Frontend Missing Tooling**: `playwright` was missing from `frontend/package.json`, preventing visualization tasks.
4.  **Backend Environment**: The backend environment required `pytest-asyncio` and `asyncio_mode = "auto"` for proper testing.

### Minor Issues
1.  **Potential Protobuf Conflict**: `google-ai-generativelanguage` needs to be `>=0.9.0` to avoid conflicts with `langgraph-api`'s protobuf requirements.
2.  **Tailwind Configuration**: `vite.config.ts` handles Tailwind v3 correctly, but there was confusion regarding v4 plugins (not present).

---

## Phased Plan

### Phase 1: Backend Stabilization (Completed)
*   **Goal**: Ensure backend dependencies are complete and environment is testable.
*   **Actions**:
    *   Add `duckduckgo-search` to `backend/pyproject.toml`.
    *   Add `pytest-asyncio` and configure `asyncio_mode = "auto"` in `backend/pyproject.toml`.
    *   Verify `google-ai-generativelanguage>=0.9.0`.
    *   Install and verify dependencies.

### Phase 2: Frontend Dependency Fixes (In Progress)
*   **Goal**: Ensure frontend starts and has necessary tooling.
*   **Actions**:
    *   Upgrade `@langchain/langgraph-sdk` to `^0.0.29` (or later) in `frontend/package.json`.
    *   Add `playwright` to `frontend/package.json` for future E2E testing/visualization.

### Phase 3: Verification Setup
*   **Goal**: Validate the fixes.
*   **Actions**:
    *   Use `verification_scripts/` for Python-based Playwright verification (standard workflow).
    *   Ensure backend and frontend can communicate (e.g., proxy settings in `vite.config.ts` match backend port 8000).

### Phase 4: Future Improvements
*   **Goal**: Permanent E2E Tests.
*   **Actions**:
    *   Implement TypeScript-based Playwright tests in `frontend/tests/` using the installed Node dependency.
