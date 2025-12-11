# Upstream Compatibility Strategy

## Objective
Maintain a clean path to the upstream "Deep Research" baseline while allowing the agent to evolve with advanced features (SearchRouter, Observability, MCP).

## Strategy: Node Splitting
We will split the monolithic `nodes.py` into two distinct modules:

1.  **`_nodes.py` (Legacy/Upstream):**
    - Contains the original, un-refactored node functions exactly as they appear in the upstream repository.
    - Used by the "Strict Linear" or "Legacy" graph variants.
    - **Rule:** Do not modify this file unless pulling upstream changes.

2.  **`nodes.py` (Evolved):**
    - Contains the enhanced node functions (e.g., using `SearchRouter` instead of direct Tavily calls, adding `observe_span` decorators).
    - Used by the "Production" or "Evolved" graph (`graph.py`).
    - **Rule:** This is the active development file.

## Implementation Plan
1.  Copy the current `nodes.py` to `_nodes.py` (if we wanted to capture the current state, but better to fetch the actual upstream state).
2.  Refactor `nodes.py` to import necessary shared utilities but keep the logic evolved.
3.  Update `graph.py` to import from `nodes.py` (already doing this).
4.  Create a new `legacy_graph.py` (or use `graphs/linear.py`) that imports from `_nodes.py`.

## Benefits
- **Benchmarks:** We can run the same queries against `graph.py` (Evolved) and `legacy_graph.py` (Upstream) to measure improvements.
- **Merge Conflicts:** Upstream changes to `nodes.py` will conflict with our `nodes.py`, but having `_nodes.py` gives us a reference to resolve them or to apply them to the legacy path first.
