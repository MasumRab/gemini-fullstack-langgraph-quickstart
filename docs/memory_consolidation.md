# Canonical Memory Set (Active/Valid)

## Architecture & Core
- **Structure:** Python backend (FastAPI/LangGraph) + React frontend (Vite).
- **Graph:** `backend/src/agent/graph.py` defines a Parallel Agent workflow; `_graph.py` is not in `main`.
- **State:** `OverallState` (in `state.py`) aggregates `web_research_result` (list of strings) using `operator.add`.
- **RAG:** `backend/src/agent/rag.py` implements `DeepSearchRAG` using **FAISS** and `sentence-transformers`. (No ChromaDB/Dual-write in `main`).
- **Planning:** Planning commands (`/plan`, etc.) are handled by `planning_router.py`.

## Dependencies & Environment
- **Python:** Supports 3.12/3.13. `environment.yml` prioritizes `pytorch` and `conda-forge`.
- **Google:** `google-ai-generativelanguage>=0.9.0` is required in `pyproject.toml` to satisfy `protobuf` constraints.
- **LangChain:** `langchain-text-splitters` is explicitly required.
- **Colab:** `notebooks/colab_setup.ipynb` handles environment detection and package uninstallation (tensorflow/grpcio-status) fixes.

## Features & Configuration
- **MCP:** Configured in `backend/src/agent/mcp_config.py` via `MCPSettings` (env vars: `MCP_ENABLED`, `MCP_ENDPOINT`).
- **Observability:** `LangfuseCallbackHandler` is conditionally imported in `backend/src/observability/langfuse.py`.
- **Testing:** Uses `pytest` with `unittest.mock` for LLM clients.
- **Search:** `web_research` node outputs formatted strings; no dedicated `SearchRouter` or `backend/src/search/` directory in `main`.

## Workflows
- **Review:** "Review and Merge" implies manual maintainer simulation (checkout, test, merge, submit).
- **Git:** Rebase-only workflow preferred.
- **Docs:** `docs/tasks/*.md` for execution plans; `docs/reference/` for prompts/examples.
