# Research Agent Inspirations & Implementation Map

This document maps state-of-the-art (SOTA) research agent frameworks to the nodes and capabilities implemented in this project.

---

## Quick Access Testing

```python
# Test different graph configurations inspired by SOTA frameworks
from agent.graph_builder import build_graph

# FlowSearch-inspired (DAG + Refinement)
flowsearch_graph = build_graph(
    enable_planning=True,
    enable_reflection=True,
    enable_validation=True,
)

# RhinoInsight-inspired (Checklist + Auditing)
rhino_graph = build_graph(
    enable_planning=True,      # Checklist via planning_mode
    enable_validation=True,    # Evidence auditing via validate_web_results
    enable_compression=True,   # Context pruning via compression_node
)

# TTD-DR-inspired (Multi-variant synthesis)
ttd_graph = build_graph(
    enable_reflection=True,    # Self-evolution via reflection loop
    enable_compression=True,   # Synthesis optimization
)
```

---

## 1. Open Deep Research (LangChain)

**Source:** [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research)

| Core Concept | This Project Implementation | Status |
|--------------|----------------------------|--------|
| Query Decomposition | `generate_query` node | ✅ Implemented |
| Web Search | `web_research` node + `SearchRouter` | ✅ Implemented |
| Reflection Loop | `reflection` + `evaluate_research` | ✅ Implemented |
| Final Synthesis | `finalize_answer` node | ✅ Implemented |
| Multi-agent Supervisor | `graphs/supervisor.py` | ✅ Implemented |

**Graph:** `upstream.py` (minimal), `planning.py` (standard)

---

## 2. ThinkDepthAI Deep Research

**Source:** [ThinkDepthAI/deep-research-example](https://github.com/ThinkDepthAI/deep-research-example)

| Core Concept | This Project Implementation | Status |
|--------------|----------------------------|--------|
| Planning Mode | `planning_mode` + `planning_wait` | ✅ Implemented |
| User Confirmation | `planning_router` + `/confirm_plan` | ✅ Implemented |
| Structured Plans | `planning_steps` in state | ✅ Implemented |
| Plan Persistence | `save_plan` / `load_plan` | ✅ Implemented |

**Graph:** `planning.py`

---

## 3. RhinoInsight

**Paper/Concept:** Checklist-based verification with evidence auditing.

| Core Tool | This Project Implementation | Status | Notes |
|-----------|----------------------------|--------|-------|
| **Checklist Generator** | `planning_mode` (generates plan steps) | ✅ Implemented | Decomposes into plan items |
| **Evidence Auditor** | `validate_web_results` (hybrid validation) | ✅ Implemented | Heuristic + LLM claim-check |
| **Source Validator** | `validate_web_results` (citation check) | ✅ Implemented | `REQUIRE_CITATIONS` flag |
| **Citation Tracker** | `sources_gathered` + `insert_citation_markers` | ✅ Implemented | URL-to-claim mapping |
| **Context Pruner** | `compression_node` (tiered compression) | ✅ Implemented | Token budget via `TOKEN_BUDGET` |

**Graph:** `build_graph(enable_planning=True, enable_validation=True, enable_compression=True)`

---

## 4. TTD-DR (Test-Time Diffusion for Deep Research)

**Concept:** Generate multiple answer trajectories, iteratively refine via self-evolution.

| Core Tool | This Project Implementation | Status | Notes |
|-----------|----------------------------|--------|-------|
| **Diffusion Planner** | `generate_query` (multi-query gen) | ⚡ Partial | Generates N initial queries |
| **Self-Evolution Engine** | `reflection` loop | ✅ Implemented | Follow-up query iteration |
| **LLM-as-Judge** | `validate_web_results` (LLM validator) | ✅ Implemented | Hybrid mode claim-check |
| **Multi-Doc Synthesizer** | `finalize_answer` | ✅ Implemented | Combines all sources |
| **Variant Generator** | Not implemented | ❌ Planned | Multiple answer variants |

**Planned Enhancement:** Add `answer_variants` node for multi-trajectory synthesis.

---

## 5. ManuSearch

**Concept:** Modular, domain-aware search with transparent logging.

| Core Tool | This Project Implementation | Status | Notes |
|-----------|----------------------------|--------|-------|
| **Modular Planner** | `planning_mode` | ✅ Implemented | Structured decomposition |
| **Domain-Specific Readers** | `SearchRouter` adapters | ⚡ Partial | Google, Tavily, DDG |
| **Transparent Logger** | `graph_registry` + `observe_span` | ✅ Implemented | Langfuse integration |
| **Multi-Domain Searcher** | `SearchRouter` with fallback | ✅ Implemented | Provider routing |

**Enhancement Opportunity:** Add domain classification to route academic vs news queries.

---

## 6. FlowSearch (DAG-based Research)

**Concept:** Graph-based query flow with semantic reranking.

| Core Tool | This Project Implementation | Status | Notes |
|-----------|----------------------------|--------|-------|
| **Web Search Engine** | `SearchRouter` (multi-provider) | ✅ Implemented | Google, Tavily, DDG |
| **Content Extractor** | Search adapter `raw_content` | ✅ Implemented | Via provider APIs |
| **Query Rewriter** | `generate_query` | ✅ Implemented | LLM-optimized queries |
| **Knowledge Flow Tracker** | `OverallState` + `graph_registry` | ✅ Implemented | State machine tracking |
| **Answer Refiner** | `reflection` loop | ✅ Implemented | Iterative improvement |
| **Semantic Ranker** | Not implemented | ❌ Planned | Embedding-based rerank |

**Planned Enhancement:** Add `semantic_rerank` node using embeddings.

---

## 7. Google Pro Search (This Project's Core)

**Source:** [google-gemini/gemini-fullstack-langgraph-quickstart](https://github.com/google-gemini/gemini-fullstack-langgraph-quickstart)

| Feature | Node/Module | Status |
|---------|-------------|--------|
| Gemini Integration | `ChatGoogleGenerativeAI` | ✅ Implemented |
| Google Search Grounding | `GoogleSearchAdapter` | ✅ Implemented |
| Parallel Search | `Send()` in `evaluate_research` | ✅ Implemented |
| Planning UI | `planning_mode` + frontend | ✅ Implemented |
| RAG Retrieval | `rag_retrieve` + FAISS/Chroma | ✅ Implemented |
| KG Enrichment | `kg_enrich` (Cognee) | ✅ Implemented |
| MCP Tools | `mcp_client.py`, `mcp_server.py` | ✅ Implemented |

---

## Implementation Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Fully implemented |
| ⚡ | Partially implemented |
| ❌ | Planned / Not implemented |

---

## Planned Features (Roadmap)

Based on SOTA inspirations:

### High Priority
1. **Semantic Reranker** (FlowSearch) - Embedding-based result reranking
2. **Answer Variants** (TTD-DR) - Generate multiple answer trajectories
3. **Domain Classifier** (ManuSearch) - Route queries by domain type

### Medium Priority
4. **Confidence Scorer** - Numeric confidence for each claim
5. **Fact Checker** - Cross-reference claims against known sources
6. **Timeline Analyzer** - Temporal reasoning for dated information

### Low Priority / Experimental
7. **Debate Mode** - Multi-agent adversarial fact-checking
8. **Visual Evidence** - Image/chart extraction and analysis
9. **Code Executor** - Run code snippets for technical queries

---

## Quick Test Commands

```bash
# Test upstream (minimal)
python examples/cli_research.py "What is quantum computing?" --mode upstream

# Test planning (standard)
python examples/cli_research.py "Compare renewable energy sources" --mode planning

# Test enriched (full features)
python examples/cli_research.py "Latest AI research trends" --mode enriched
```

---

## References

| Framework | Repository/Paper |
|-----------|-----------------|
| Open Deep Research | https://github.com/langchain-ai/open_deep_research |
| ThinkDepthAI | https://github.com/ThinkDepthAI/deep-research-example |
| RhinoInsight | (Conceptual - Checklist verification pattern) |
| TTD-DR | (Conceptual - Diffusion-based research) |
| ManuSearch | (Conceptual - Modular search) |
| FlowSearch | (Conceptual - DAG-based research) |
| Cognee (KG) | https://github.com/topoteretes/cognee |
| LangGraph | https://github.com/langchain-ai/langgraph |
