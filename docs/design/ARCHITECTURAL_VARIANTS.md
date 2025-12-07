# Architectural Variants & Migration Roadmap

This document outlines the architectural evolution of the agent framework, moving from a simple parallel execution model to more robust patterns verified by empirical research.

## Overview of Variants

We maintain multiple execution graphs to allow benchmarking and specific use-case optimization.

### 1. Parallel (Default)
**File:** `backend/src/agent/graphs/parallel.py`
**Concept:** "Fan-out / Fan-in"
- **Flow:** `Plan` -> `Parallel Web Search` -> `Validate` -> `Reflect` -> `Loop`.
- **Pros:** Fast, maximizes throughput.
- **Cons:** High risk of "Context Fragmentation" (as warned by Cognition blog). Context grows linearly with search results, leading to "Lost in the Middle" phenomenon for LLMs.

### 2. Linear (Strict)
**File:** `backend/src/agent/graphs/linear.py`
**Concept:** "One at a time"
- **Flow:** `Plan` -> `Search (Item 1)` -> `Validate` -> `Reflect` -> `Search (Item 2)`...
- **Pros:** Maximum reliability, easy to debug, clear causal chain.
- **Cons:** Slowest execution.
- **Status:** Implemented as a baseline for reliability benchmarks.

### 3. Supervisor + Compression (Option A+)
**File:** `backend/src/agent/graphs/supervisor.py`
**Concept:** "Parallel Execution with Managed Memory"
- **Flow:** `Plan` -> `Parallel Search` -> `Validate` -> `**Compress Context**` -> `Reflect`.
- **Key Innovation:** The `compress_context` node runs after validation. It summarizes the raw search results into a concise "Knowledge Graph" or running summary *before* the reflection step.
- **Benefit:** Maintains the speed of parallelism while mitigating context fragmentation.

## Configuration

To switch between variants, use the `agent_mode` configuration parameter in `langgraph.json` or at runtime:

```json
{
  "configurable": {
    "agent_mode": "linear" // or "parallel", "supervisor"
  }
}
```

## Migration Roadmap

| Phase | Variant | Goal | Status |
|-------|---------|------|--------|
| 1 | **Parallel** | Baseline speed benchmark. | ✅ Active |
| 2 | **Linear** | Baseline reliability benchmark. | ✅ Implemented |
| 3 | **Supervisor** | Prove "Compression" solves context issues. | ⚠️ Prototype |
| 4 | **Diffusion** | Advanced "Plan -> Diffuse -> Compress -> Aggregate" flow. | 📅 Future |

## References
- **Blog:** "Don't Build Multi-Agents" (Cognition AI) - Warns against fragmentation.
- **Report:** "Evidence-Based Extensions" - Validates Supervisor/Worker patterns with shared memory/compression.
