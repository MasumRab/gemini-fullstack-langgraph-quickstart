# Upstream Divergence Report

## Summary
This report documents the differences between the current HEAD and `upstream/main` (google-gemini/gemini-fullstack-langgraph-quickstart).

**Strategic Recommendation:**
**Do NOT merge `upstream/main` directly.**
The recommended workflow is to **target specific commits** (cherry-pick) for bug fixes or dependency updates. Merging the full upstream HEAD is strongly discouraged because the architectures have diverged significantly.

## Key Findings

### 1. Architectural Changes
The current codebase has significantly evolved the backend architecture:
- **Modularization:** Logic has been extracted from `graph.py` into `nodes.py`, `router.py`, and `registry.py`.
- **Variants:** New graph implementations exist in `backend/src/agent/graphs/` (`linear.py`, `supervisor.py`).
- **Legacy Preservation:** The original graph structure is preserved in `_graph.py` (legacy) and `graph.py` (Parallel variant).

### 2. New Features
- **RAG & Persistence:** Added `rag_nodes.py` and `persistence.py`.
- **Testing:** Significant addition of tests in `backend/tests/`.
- **Documentation:** Extensive documentation added in `docs/` and root markdown files (`ROADMAP.md`, `INTEGRATION_STRATEGY.md`).

### 3. Conflict Hotspots
If merging upstream updates, expect conflicts in:
- `backend/src/agent/graph.py`: This file has been heavily modified to use the new `nodes.py` imports.
- `backend/src/agent/state.py`: Likely modified to support new state fields.
- `frontend/src/App.tsx` & `ChatMessagesView.tsx`: UI modifications for the enhanced agent.

## Implementation Guide
For specific instructions on how to sync selected changes, refer to:
[docs/tasks/UPSTREAM_SYNC_COMMANDS.md](../docs/tasks/UPSTREAM_SYNC_COMMANDS.md)

## Files Added (Not in Upstream)
- `backend/src/agent/nodes.py`
- `backend/src/agent/router.py`
- `backend/src/agent/registry.py`
- `backend/src/agent/graphs/*`
- `docs/*`
- `tests/*`

## Files Modified
- `backend/src/agent/graph.py`
- `backend/src/agent/configuration.py`
- `backend/src/agent/state.py`
- `frontend/src/App.tsx`
