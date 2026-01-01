# Memory Audit Report

**Date:** 2025-12-13
**Reviewer:** Jules (AI Assistant)
**Scope:** `main` branch vs. Remote Feature Branches

## Summary
A comprehensive audit of the project memories was conducted against the actual codebase. Significant discrepancies were found where memories described features (Knowledge Graph, Unified Search, Centralized Config) that are **not present in `main`** but **do exist in the `feature/search-rag-hybrid` branch**.

| Category | Count | Description |
| :--- | :---: | :--- |
| **Active / Valid** | 35 | Confirmed in `main`. Safe to use. |
| **Roadmap / Future** | 7 | Found in `feature/search-rag-hybrid...`. Do not use in `main`. |
| **Invalid / Outdated** | 14 | Not found or strictly contradicted by code. |

---

## Detailed Audit

### 1. Roadmap / Future Features (Do NOT assume present in `main`)
*Found in `origin/feature/search-rag-hybrid-3228504735555579147`*

| Memory | Evidence (Branch: `feature/search-rag-hybrid...`) | Status |
| :--- | :--- | :--- |
| **Knowledge Graph (`kg_enrich`)** | `backend/src/agent/kg.py` exists. | **Roadmap** |
| **ChromaDB Support** | `backend/src/agent/rag.py` contains `ChromaStore`. | **Roadmap** |
| **Unified Search Router** | `SearchRouter` class found in `nodes.py`. | **Roadmap** |
| **Centralized Config (`AppConfig`)** | `backend/src/config/app_config.py` exists. | **Roadmap** |
| **Legacy Graph (`_graph.py`)** | `backend/src/agent/_graph.py` exists (also in other refactor branches). | **Roadmap** |
| **Brave Search Adapter** | `backend/src/search/providers/brave.py` (inferred from SearchRouter context). | **Roadmap** |
| **Web Result Validation (Hybrid)** | Logic likely tied to `AppConfig` and `SearchRouter`. | **Roadmap** |

### 2. Active / Valid (Confirmed in `main`)

| Memory | Evidence (`main`) | Confidence |
| :--- | :--- | :--- |
| **Python 3.12/3.13 Support** | `pyproject.toml`, `environment.yml`. | High |
| **MCP Configuration** | `backend/src/agent/mcp_config.py` exists and has `MCPSettings`. | High |
| **Langfuse Integration** | `backend/src/observability/langfuse.py` handles imports. | High |
| **Google GenAI Dependency** | `google-ai-generativelanguage` in `pyproject.toml`. | High |
| **RAG (FAISS Only)** | `backend/src/agent/rag.py` exists but uses `DeepSearchRAG` (FAISS). | High |
| **Output `web_research_result`** | `nodes.py` outputs list of strings. | High |
| **Parallel Graph Structure** | `backend/src/agent/graph.py` implements parallel execution. | High |
| **Dependencies** | `langgraph`, `langchain-text-splitters` in `pyproject.toml`. | High |

### 3. Invalid / Outdated (Action: Purge)

| Memory | Reality | Action |
| :--- | :--- | :--- |
| **"RAG supports dual-write"** | `rag.py` in `main` is FAISS-only. No `DUAL_WRITE` flag. | **Purge** |
| **"Brave Search in `src/search/`"** | Directory `backend/src/search/` does not exist in `main`. | **Purge** |
| **"Mock persistence.py"** | `backend/src/agent/persistence.py` exists but contains real logic/imports, not just mocks. | **Update** |

---

## Recommendations
1. **Purge** the "Roadmap" memories from the active context to prevent hallucinations when working on `main`.
2. **Restore** them only when switching to the `feature/search-rag-hybrid` branch.
3. **Canonical Memory Set**: Use `memory_consolidation.md` for current work.
