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
- **Colab:** `backend/notebooks/colab_setup.ipynb` handles environment detection and package uninstallation (tensorflow/grpcio-status) fixes.

## Features & Configuration
- **MCP:** Configured in `backend/src/agent/mcp_config.py` via `MCPSettings` (env vars: `MCP_ENABLED`, `MCP_ENDPOINT`).
- **Observability:** `LangfuseCallbackHandler` is conditionally imported in `backend/src/observability/langfuse.py`.
- **Testing:** Uses `pytest` with `unittest.mock` for LLM clients.
- **Search:** `web_research` node outputs formatted strings; no dedicated `SearchRouter` or `backend/src/search/` directory in `main`.

## Workflows
- **Review:** "Review and Merge" implies manual maintainer simulation (checkout, test, merge, submit).
- **Git:** Rebase-only workflow preferred.
- **Docs:** `docs/tasks/*.md` for execution plans; `docs/reference/` for prompts/examples.

## Repository Workflows & Best Practices
- **Missing Configurations (e.g., Dependabot, Mergify):**
  - Do not assume missing configurations (like `.github/dependabot.yml` or `.mergify.yml`) were deleted by an agent or a "memory setting."
  - Often, the branch being worked on is outdated and the files were simply merged into `main` *after* the PR branch was created.
  - **Action:** Agents must fetch `main` (`git fetch origin main`) and check its contents (`git ls-tree origin/main .github/`) or use `gh pr list --state all` to verify if these features already exist or have been addressed in other PRs before recreating or modifying them locally.
