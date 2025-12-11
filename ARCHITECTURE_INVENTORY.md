# Agent Architecture Inventory

This document catalogs all node classes, graph variants, and feature modules implemented in this project.

---

## 1. Core Nodes (`backend/src/agent/nodes.py`)

| Node Name | Function | Description | Inputs | Outputs |
|-----------|----------|-------------|--------|---------|
| `load_context` | `load_context()` | Loads existing plan/artifacts from persistence | `thread_id` | `todo_list`, `artifacts` |
| `generate_query` | `generate_query()` | LLM generates search queries from user question | `messages` | `search_query` (list) |
| `continue_to_web_research` | `continue_to_web_research()` | Fan-out helper routing queries to parallel search | `search_query` | `Send[]` to `web_research` |
| `web_research` | `web_research()` | Executes web search via SearchRouter | `search_query` | `web_research_result`, `sources_gathered` |
| `planning_mode` | `planning_mode()` | Creates structured plan steps for user review | `search_query` | `planning_steps`, `planning_status` |
| `planning_wait` | `planning_wait()` | Pauses execution until user confirms plan | - | `planning_feedback` |
| `planning_router` | `planning_router()` | Routes based on planning status and commands | `planning_status`, `messages` | Node name |
| `validate_web_results` | `validate_web_results()` | Hybrid validation (Heuristics + LLM) | `web_research_result` | `validated_web_research_result` |
| `compression_node` | `compression_node()` | Tiered compression of research results | `validated_web_research_result` | Compressed results |
| `reflection` | `reflection()` | Evaluates coverage, proposes follow-up queries | `web_research_result` | `is_sufficient`, `follow_up_queries` |
| `evaluate_research` | `evaluate_research()` | Routing policy for loop or finalize | `is_sufficient`, `research_loop_count` | Node name or `Send[]` |
| `finalize_answer` | `finalize_answer()` | Synthesizes final response with citations | `web_research_result`, `sources_gathered` | `messages` (AIMessage) |

---

## 2. Specialized Nodes

### Knowledge Graph (`backend/src/agent/kg.py`)
| Node | Function | Description |
|------|----------|-------------|
| `kg_enrich` | `kg_enrich()` | Enriches KG with research results (uses Cognee) |

### RAG Nodes (`backend/src/agent/rag_nodes.py`)
| Node | Function | Description |
|------|----------|-------------|
| `rag_retrieve` | `rag_retrieve()` | Retrieves documents from configured RAG sources |
| `should_use_rag` | `should_use_rag()` | Routing: RAG vs Web Search |
| `rag_fallback_to_web` | `rag_fallback_to_web()` | Fallback routing after RAG |

### Deep Search Agent (`backend/src/agent/deep_search_agent.py`)
| Class | Method | Description |
|-------|--------|-------------|
| `DeepSearchAgent` | `research()` | Standalone research workflow (Plan -> Search -> RAG -> Synthesize) |
| `DeepSearchAgent` | `research_with_artifacts()` | Research + MCP artifact saving |
| `QueryPlanner` | `decompose()` | Decomposes query into sub-questions |
| `WebSearcher` | `search()` | Executes search (Tavily/DuckDuckGo/Mock) |
| `AnswerRefiner` | `synthesize()` | Synthesizes final answer from context |

---

## 3. Graph Variants (`backend/src/agent/graphs/`)

| Graph | File | Description | Features |
|-------|------|-------------|----------|
| **Upstream** | `upstream.py` | Minimal baseline | Query → Search → Answer |
| **Planning** | `planning.py` | Standard workflow | + Planning Mode, + Reflection, + Validation |
| **Linear** | `linear.py` | Sequential execution | No parallel Send, strict queue |
| **Parallel** | `parallel.py` | Parallel fan-out | Parallel web research |
| **Supervisor** | `supervisor.py` | Multi-agent supervision | Agent coordination |
| **Enriched** | `graph.py` | Full-featured | + KG Enrichment, + Compression |

### Dynamic Graph Builder (`backend/src/agent/graph_builder.py`)

For notebook flexibility, use `build_graph()` to compose custom graphs:

```python
from agent.graph_builder import build_graph

# Minimal (upstream-like)
graph = build_graph(enable_planning=False, enable_reflection=False)

# Standard with planning
graph = build_graph(enable_planning=True, enable_reflection=True)

# Full enriched
graph = build_graph(
    enable_planning=True,
    enable_reflection=True,
    enable_compression=True,
    enable_kg=True,
)

# RAG-enabled
graph = build_graph(enable_rag=True, enable_planning=True)

# Execute
result = await graph.ainvoke(state, config)
```

**Available Flags:**
| Flag | Default | Description |
|------|---------|-------------|
| `enable_planning` | `False` | Include planning mode |
| `enable_reflection` | `True` | Include reflection loop |
| `enable_validation` | `True` | Include result validation |
| `enable_compression` | `False` | Include compression |
| `enable_rag` | `False` | Include RAG retrieval |
| `enable_kg` | `False` | Include KG enrichment |
| `parallel_search` | `True` | Parallel web search |

### CLI Selection (via `cli_research.py`)
```bash
python examples/cli_research.py "Your question" --mode upstream   # Minimal
python examples/cli_research.py "Your question" --mode planning   # Standard
python examples/cli_research.py "Your question" --mode linear     # Sequential
python examples/cli_research.py "Your question" --mode enriched   # Full
```

---

## 8. Orchestration Layer (`backend/src/agent/orchestration.py`)

For dynamic tool and agent management with coordinator-based task allocation:

### Tool Registry
```python
from agent.orchestration import ToolRegistry

registry = ToolRegistry()

# Register custom tools
registry.register(
    "semantic_search",
    my_semantic_search_func,
    description="Search using semantic embeddings",
    category="search",
)

# Get tools by category
search_tools = registry.get_tools(category="search")
```

### Agent Pool
```python
from agent.orchestration import AgentPool

pool = AgentPool()

# Register sub-agents
pool.register(
    "fact_checker",
    fact_check_graph,
    description="Verifies claims against sources",
    capabilities=["verification", "citation"],
)

# Get agents with capability
verifiers = pool.get_agents_with_capability("verification")
```

### Orchestrated Graph
```python
from agent.orchestration import build_orchestrated_graph, ToolRegistry, AgentPool

# Setup registries
tools = ToolRegistry()
agents = AgentPool()

# Add custom components
tools.register("custom_tool", my_func, description="My custom tool")
agents.register("specialist", specialist_graph, capabilities=["domain_expert"])

# Build orchestrated graph
graph = build_orchestrated_graph(
    tools=tools,
    agents=agents,
    coordinator_model="gemini-2.5-pro",
)

# Execute with coordinator-based routing
result = await graph.ainvoke(state, config)
```

### Orchestration Flow
```
User Query → Coordinator → [Route Decision]
                              ↓
              ┌───────────────┼───────────────┐
              ↓               ↓               ↓
        quick_search      planner      deep_researcher
              ↓               ↓               ↓
              └───────────────┴───────────────┘
                              ↓
                         Finalize
```

---

## 4. Feature Modules

### MCP Tools (`backend/src/agent/mcp_*.py`)
| Module | Description |
|--------|-------------|
| `mcp_config.py` | MCP settings loader and validator |
| `mcp_client.py` | MCP tool user client |
| `mcp_server.py` | Filesystem MCP server implementation |

### Search Providers (`backend/src/search/`)
| Provider | Description |
|----------|-------------|
| `GoogleSearchAdapter` | Google GenAI grounding search |
| `TavilyAdapter` | Tavily API search |
| `DuckDuckGoAdapter` | DuckDuckGo fallback search |
| `SearchRouter` | Unified router with fallback logic |

### RAG Store (`backend/src/rag/`)
| Store | Description |
|-------|-------------|
| `faiss_store.py` | FAISS vector store (default) |
| `chroma_store.py` | ChromaDB vector store |

### Configuration (`backend/src/config/`)
| Config | Description |
|--------|-------------|
| `app_config.py` | Application-wide settings (RAG, KG, Search, Models) |
| `configuration.py` | LangGraph agent configuration schema |

---

## 5. Model Configuration

| Role | Default Model | Config Key |
|------|---------------|------------|
| Query Generation | `gemini-2.5-flash-lite` | `query_generator_model` |
| Reflection | `gemini-2.5-flash` | `reflection_model` |
| Final Answer | `gemini-2.5-pro` | `answer_model` |
| Validation | `gemini-2.5-flash-lite` | `model_validation` |
| Compression | `gemini-2.5-flash-lite` | `model_compression` |
| Planning | `gemini-2.5-flash` | `model_planning` |

---

## 6. Feature Flags (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `KG_ENABLED` | `false` | Enable Knowledge Graph enrichment |
| `COMPRESSION_ENABLED` | `true` | Enable result compression |
| `VALIDATION_MODE` | `hybrid` | Validation mode (heuristic/hybrid) |
| `REQUIRE_CITATIONS` | `true` | Require citations in results |
| `RAG_STORE` | `faiss` | RAG store type (faiss/chroma) |
| `SEARCH_PROVIDER` | `google` | Primary search provider |
| `SEARCH_FALLBACK` | `duckduckgo` | Fallback search provider |

---

## 7. Registry & Observability

| Component | Description |
|-----------|-------------|
| `graph_registry` | Metadata registry for node documentation |
| `observe_span` | Langfuse observability wrapper (optional) |

