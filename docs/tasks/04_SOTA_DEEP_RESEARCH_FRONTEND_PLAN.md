# Frontend Control Surface and Technique Reproduction Mode

*This document outlines the planned frontend architecture for controlling, reproducing, and evaluating SOTA Deep Research strategies. It is part of the broader SOTA tracking initiative (see `04_SOTA_DEEP_RESEARCH_STATUS.md` and `04_SOTA_DEEP_RESEARCH_SOTA_SOURCES.md`).*

## 1. Goal & Principles

The goal is to add a small, additive, data-driven frontend control layer that lets users configure deep-research behaviors, compare established technique profiles, and leave room for newly discovered SOTA methods without redesigning the UI.

**Principles:**
*   **Data-Driven Profiles**: Presets are driven by a central registry, not hardcoded enums.
*   **Honest Capability Mapping**: Do not imply planned features are active. Use clear badges (Implemented, Partial, Planned, Reference-only).
*   **Extensibility**: The UI must easily accommodate new "experimental" or newly discovered profiles.
*   **Preserve Customization**: Users can override preset profiles using a compact Advanced Options panel.

## 2. Research Mode vs. Technique Reproduction Mode

The UI will expose two distinct selector levels to cater to different user intents:

### A. Research Mode (Intent-driven)
A user-friendly, high-level selector that configures the agent for a broad outcome:
*   **Fast Summary**: Shallow search, minimal verification, no recursion.
*   **Balanced Deep Research**: Default behavior.
*   **Exhaustive Deep Research**: High search depth, high verification.
*   **Source Verification / Fact Check**: Stricter citations, contradiction detection, verifier checklist.
*   **Multi-Perspective Outline**: STORM-style perspective planning and outline-first output.
*   **Dynamic Flow / Adaptive Research**: FlowSearch-style dynamic task graph expansion.

### B. Technique Reproduction Mode (Implementation-driven)
A selector for power-users, researchers, and developers evaluating specific SOTA frameworks:
*   **Off / Custom**
*   **Open Deep Research-style**
*   **STORM-style**
*   **FlowSearch-style**
*   **ManuSearch-style**
*   **GPT Researcher-style**
*   **Verifier / Checklist-style**
*   **TTD-DR / Denoising-style**
*   **Other / Experimental** (Reveals secondary dropdown of documented watchlist items).

*Fidelity Labels*: Each profile will display its reproduction fidelity:
- Exact, Strong approximation, Partial, Planned, or Reference only.

## 3. UI Components

### Technique Behavior Summary Panel
Displays a short explanation of the selected profile, its primary behavior, and the current backend support status (e.g., `flow_update`: Implemented, graph visualization: Planned).

### Compact Advanced Options
Collapsed by default. Allows overriding specific toggles:
*   **Features**: Ask clarification questions, Multi-perspective planning, Dynamic task graph expansion, Recursive subtopic research, Structured webpage reading, Contradiction detection, Verifier checklist, Evidence denoising, Citation quality scoring.
*   **Depth & Strictness**: Research Depth (Light, Standard, Deep, Exhaustive), Citation Strictness (Relaxed, Standard, Strict).
*   **Output Format**: Short answer, Structured brief, Long report, Outline first, Evidence table, Research plan only.
*   **Numeric Limits (If supported)**: Max sources, max iterations, max recursive depth.

### Compare Techniques View
A lightweight comparison mode to evaluate two technique profiles side-by-side:
*   Compares dimensions like: Planning style, Primary artifact, Adaptation during run, Best suited for, Current support, Major warnings.
*   Initially implements a "Plan Preview Compare" (shows the effective config and expected behavior without running a double-job).

### Effective Config Preview
Displays the exact JSON payload (`research_config`) that will be sent to the backend. Essential for debugging complex interactions and verifying profile overrides.

### Feature Compatibility Warnings
Simple warnings (e.g., "Strict citation mode requires source verification") to prevent misleading combinations.

### Read-only Research Trace Panel
Visualizes the backend execution trace (Task graph nodes, Sources found, Verifier checklist result, etc.).

## 4. Backend Contract

The frontend will send a normalized `research_config` object. If the backend ignores any fields (e.g., because they are planned but not implemented), the UI must document this clearly.

```json
{
  "query": "string",
  "research_config": {
    "mode": "balanced",
    "technique_profile": "custom",
    "depth": "standard",
    "output_format": "structured_brief",
    "citation_strictness": "standard",
    "features": {
      "clarification": true,
      "multi_perspective": false,
      "dynamic_flow_update": false,
      "recursive_subtopics": false,
      "structured_reader": false,
      "contradiction_detection": false,
      "verifier_checklist": false,
      "evidence_denoising": false,
      "citation_quality_scoring": false
    },
    "limits": {
      "max_sources": 20,
      "max_iterations": 3,
      "max_graph_nodes": 12,
      "max_recursive_depth": 1
    }
  }
}
```

## 5. Open-ended SOTA Discovery and Extensible Technique Profiles

We do not assume the current list of SOTA deep research techniques is complete.

*   **Discovery Model**: We will periodically scan recent papers, benchmarks, and agentic workflows for new approaches.
*   **Classification**: Newly discovered techniques are documented and classified based on source confidence (High/Medium/Low).
*   **Integration Path**: A new technique becomes a runnable reproduction profile *only* if it has a distinct planning, retrieval, verification, or interaction strategy. Otherwise, it is mapped to an existing profile or documented as a watchlist item.
*   **Unclassified Pathway**: Methods requiring entirely new interaction paradigms (e.g., mid-run human-in-the-loop critique) are marked as "Discovered but unclassified" and deferred to future architectural updates rather than forced into simple toggles.
