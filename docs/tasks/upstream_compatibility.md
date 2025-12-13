# Task: Restore Upstream Compatibility via `_nodes.py`

**Status:** Proposed / Todo
**Priority:** Low (Cleanup/Architecture)

## Context
The file `backend/src/agent/nodes.py` has significantly diverged from the original upstream implementation to support features like:
*   `SearchRouter` (reliability-first search)
*   `observe_span` (Langfuse observability)
*   Hybrid Validation (LLM claim-check + heuristics)
*   Tiered Compression

While `backend/src/agent/graph.py` uses these evolved nodes, there is a desire to maintain an `_graph.py` (or similar) that represents the "standard" or "upstream" implementation for benchmarking and compatibility testing.

## Plan

### 1. Create `backend/src/agent/_nodes.py`
This file should contain the **unmodified** or minimally modified node logic corresponding to the upstream repository state.
*   **Web Research:** Direct call to Tavily/Google without `SearchRouter` fallback complexity.
*   **Validation:** Simple heuristics or pass-through.
*   **No Observability:** Remove `observe_span` decorators to keep it clean.

### 2. Create/Update `backend/src/agent/_graph.py`
This graph definition should import nodes from `_nodes.py` instead of `nodes.py`.
```python
from agent._nodes import (
    load_context,
    generate_query,
    # ...
)
# Define StateGraph using these nodes
```

### 3. Integrate Decorators for Readability
To clearly distinguish between "Standard" and "Evolved" nodes in tooling (like `GraphRegistry`), we should use decorators or metadata.

**Proposal:** Update `graph_registry.describe` or add a new decorator `@upstream_compatible`.

```python
# In _nodes.py
@graph_registry.describe(
    "web_research",
    tags=["upstream", "standard"],
    summary="Standard web research using single provider."
)
def web_research(state): ...

# In nodes.py
@graph_registry.describe(
    "web_research",
    tags=["evolved", "production"],
    summary="Reliability-first web research with fallback and observability."
)
def web_research(state): ...
```

This allows visualization tools to filter or highlight the differences.

## Next Steps
1.  Copy the original node logic (from git history or upstream) into `backend/src/agent/_nodes.py`.
2.  Implement `backend/src/agent/_graph.py` using these nodes.
3.  Update `backend/src/agent/registry.py` to handle `tags` in metadata if not already present.
