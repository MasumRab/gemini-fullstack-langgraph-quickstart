# Dependency Map & Feature Analysis

This document maps the codebase's high-level capabilities to their underlying Python package costs.

## Architecture Overview

The system is built on a **LangGraph** backend (Orchestration) and **FastAPI** (Serving), utilizing **Google Gemini** for intelligence and **DuckDuckGo** for grounding.

### 1. Core Agent Orchestration
**Capabilities:** State management, cyclical planning, tool execution.
**Packages:**
- `langgraph`: The core state machine.
- `langchain-core`: Primitives for runnables and messages.
- `langchain`: Higher-level chains (being phased out for pure LangGraph).

### 2. Search & Grounding
**Capabilities:** Web research, source verification.
**Packages:**
- `duckduckgo-search`: Primary search provider (lightweight).
- `langchain-community` (implicit): Adapters for search tools.

### 3. RAG (Retrieval Augmented Generation)
**Capabilities:** Long-term memory, document storage, semantic search.
**Packages:**
- `sentence-transformers` (Heavy): Generates embeddings locally. Requires `torch`.
- `faiss-cpu`: Vector similarity search index.
- `pandas`: Data manipulation for evidence chunks.
- `langchain-text-splitters`: Chunking logic.

### 4. Intelligence & LLM
**Capabilities:** Plan generation, reasoning, synthesis.
**Packages:**
- `google-genai`: Official Gemini SDK (V2/Vertex).
- `langchain-google-genai`: LangChain adapter for Gemini.
- `google-ai-generativelanguage`: Low-level protocol buffers.

### 5. Infrastructure & Serving
**Capabilities:** API endpoints, async execution.
**Packages:**
- `fastapi`: Web server.
- `uvicorn` (Standard): ASGI server.
- `python-dotenv`: Config management.
- `tenacity`: Retry logic for robust API calls.

### 6. Visualization & Analysis
**Capabilities:** Graph introspection, dependency plotting.
**Packages:**
- `matplotlib`: Plotting library.
- `scipy` (Dev): Hierarchical clustering algorithms.

---

## Trade-off Analysis: Heavy Dependencies

### `sentence-transformers` & `torch`
*   **Role:** Provides local embedding generation for RAG.
*   **Cost:** Significant disk space (~700MB+ for Torch CPU) and memory usage.
*   **Trade-off:** Allows privacy-preserving, free embeddings (vs. API calls).
*   **Optimization:** Configured to strictly use `pytorch-cpu` to avoid pulling in multi-GB Nvidia CUDA libraries.

### `pandas`
*   **Role:** Structured data handling in RAG/Analysis.
*   **Cost:** Medium-weight (numpy dependency).
*   **Trade-off:** Overkill for simple lists, but essential for complex RAG operations and future data analysis features.

### `matplotlib`
*   **Role:** Generating static visualizations (graphs, charts).
*   **Cost:** Medium-weight.
*   **Trade-off:** kept in production dependencies to allow runtime generation of graph images (e.g., `graph.draw_mermaid_png()`).

## Dependency Cluster Strategy
Dependencies are grouped by "Feature Cluster" rather than just file proximity. This allows us to assess the "weight" of adding a new feature. For example, adding RAG requires the entire `torch` stack, whereas Search is relatively lightweight.
