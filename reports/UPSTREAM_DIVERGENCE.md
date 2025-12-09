# Upstream Divergence Report

## Summary
This report documents the differences between the current HEAD and `upstream/main` (google-gemini/gemini-fullstack-langgraph-quickstart).

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

## Recommendations
- **Do not merge directly.** The architectures have diverged.
- **Cherry-pick specific upstream fixes.** If upstream fixes bugs in the basic setup (e.g., build tools, basic configuration), apply them manually.
- **Maintain `_graph.py` as a reference.** This file seems to serve as a snapshot of the original logic.

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
