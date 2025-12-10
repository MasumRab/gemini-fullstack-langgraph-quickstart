# Upstream Pick List

**Generated:** (Current Date)
**Comparison:** HEAD vs upstream/main

## Summary
A comprehensive review of the divergence between the current codebase and the upstream repository (`google-gemini/gemini-fullstack-langgraph-quickstart`) reveals that the current HEAD is significantly ahead in terms of architecture and features.

The upstream repository serves as a "Quickstart" foundation, whereas this repository has evolved into a "Pro/Research" variant with:
1.  **Modular Architecture:** Logic extracted from `graph.py` into `nodes.py`, `router.py`, `registry.py`.
2.  **Advanced Features:** Planning Mode, MCP Integration, Persistence, RAG.
3.  **Frontend Enhancements:** Support for planning artifacts and complex state.

## Candidate Items for Cherry-Picking
*No significant items identified.*

Most differences in upstream are regressions relative to HEAD (e.g., missing planning logic, monolithic graph definition).

### Dependencies
- **Action:** Monitor `backend/pyproject.toml` in upstream for version bumps to `google-genai` or `langgraph`.
- **Current Status:** HEAD includes additional dependencies (`langchain-mcp-adapters`, `mcp`) required for new features.

### Logic
- **Action:** None. Upstream logic in `graph.py` is monolithic; porting changes would require manual extraction to `nodes.py`.
- **Current Status:** `backend/src/agent/prompts.py` is identical.

## Recommendation
Continue to treat `upstream` as a reference for the "Quickstart" baseline but do not attempt automatic merges. Future synchronization should be done manually by inspecting specific bug fixes in the upstream commit log.
