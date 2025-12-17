# Gemma Model Integration Tasks

This document outlines the tasks required to integrate Gemma models into the Research Agent, leveraging the findings from the Gemma Cookbook.

Reference Guide: `docs/reference/GEMMA_COOKBOOK.md`
Scaffolding Code: `backend/examples/gemma_providers.py`

## Phase 1: Environment & Dependencies

- [ ] **Dependency Update**: Add optional dependencies to `backend/pyproject.toml` or `backend/requirements.txt` based on chosen provider.
    - [ ] `google-cloud-aiplatform` (for Vertex AI)
    - [ ] `requests` (for Ollama - usually standard, but check)
    - [ ] `llama-cpp-python` (for local embedded)
- [ ] **Configuration**: Update `backend/src/config/app_config.py` to include Gemma-specific settings.
    - [ ] `GEMMA_PROVIDER` (vertex, ollama, local)
    - [ ] `GEMMA_MODEL_NAME` (e.g., gemma:7b, 2b_pt_v2.gguf)
    - [ ] `VERTEX_ENDPOINT_ID` (if applicable)
    - [ ] `OLLAMA_BASE_URL` (default: http://localhost:11434)

## Phase 2: Client Implementation

- [ ] **Integrate Vertex Client**: Adapt `VertexAIGemmaClient` from `backend/examples/gemma_providers.py` into `backend/src/agent/llm_client.py` or a new module `backend/src/agent/gemma_client.py`.
- [ ] **Integrate Ollama Client**: Adapt `OllamaGemmaClient` for local development workflows.
- [ ] **Standardize Interface**: Ensure all Gemma clients conform to the existing `LLMClient` interface (or `LangChain` runnable interface) used by the agent graph.

## Phase 3: Agentic Workflows (from Cookbook)

- [ ] **LangChain Adaptation**: Implement the patterns from `Gemma/[Gemma_2]Using_with_LangChain.ipynb`.
    - [ ] Create a `GemmaChatModel` wrapper compatible with LangChain if the standard `ChatOllama` or `ChatVertexAI` needs customization for Gemma-specific tokens.
- [ ] **Routing Implementation**: Implement the routing logic from `Gemma/[Gemma_2]Using_Gemini_and_Gemma_with_RouteLLM.ipynb`.
    - [ ] Create a `ModelRouter` node in the graph that decides whether to use a small model (Gemma 2B/7B) or a large model (Gemini 1.5 Pro) based on query complexity.

## Phase 4: RAG & Deep Research

- [ ] **Local RAG**: Implement the `LocalAgenticRAG` pattern from `Gemma/[Gemma_3]Local_Agentic_RAG.ipynb`.
    - [ ] Set up `Qdrant` or `ChromaDB` (if not already present).
    - [ ] Configure `FastEmbed` for local embeddings to pair with local Gemma.

## Phase 5: Testing & Verification

- [ ] **Unit Tests**: Create tests for the new Gemma clients in `backend/tests/agent/test_gemma.py`.
- [ ] **Integration Tests**: Verify end-to-end flow with a local Ollama instance.
- [ ] **Performance Benchmarking**: Compare latency/cost between Vertex AI Gemma and Gemini Flash.
