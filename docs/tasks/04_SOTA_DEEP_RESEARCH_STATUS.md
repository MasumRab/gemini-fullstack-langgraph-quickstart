# SOTA Deep Research Integration Status

*This document was generated automatically by the agent to report the status of SOTA Deep Research Strategies.*


*See the companion document: [04_SOTA_DEEP_RESEARCH_SOTA_SOURCES.md](04_SOTA_DEEP_RESEARCH_SOTA_SOURCES.md) for a full catalog of SOTA techniques, benchmarks, and the updated roadmap. Also see the frontend control plan: [04_SOTA_DEEP_RESEARCH_FRONTEND_PLAN.md](04_SOTA_DEEP_RESEARCH_FRONTEND_PLAN.md).*

## A. Executive Summary

**Overall Project Status: 🟡 In Progress (Significant Architecture Updates Completed)**

The project has made substantial strides in incorporating state-of-the-art (SOTA) research paradigms into the main agent graph. Of the 7 core strategies identified, **4 are implemented and integrated**, **1 is partially implemented**, and **2 remain mostly as scaffolding or TODOs**.

The biggest gaps currently lie in the recursive/parallel execution of sub-topics (GPT Researcher's `research_subgraph` node is stubbed but not fully wired/routed dynamically) and the dynamic knowledge flow DAG updates (FlowSearch's `flow_update` logic is heavily stubbed with TODOs).

**Priority Next Steps:**
1. Complete the `flow_update` logic to handle task DAG expansion based on search results.
2. Complete the graph wiring for `research_subgraph` to enable true recursive depth.
3. Integrate DeepResearch-Bench or MLE-Bench to establish a quantitative baseline for the current hybrid graph.

---

## B. Strategy-by-Strategy Status

### 1. Open Deep Research (Clarification & Scoping)
*   **Purpose:** Prevent "garbage in, garbage out" by forcing the agent to clarify ambiguous user queries before generating a plan.
*   **Status:** ✅ Implemented
*   **Evidence:**
    *   `scoping_node` exists in `backend/src/agent/nodes.py`.
    *   Integrated into `backend/src/agent/graph.py` (edges: `load_context` -> `scoping_node` -> router).
*   **Missing/TODO items:** An active TODO mentions "Verify full alignment with Open Deep Research (Clarification Loop)", suggesting the logic might be basic and could need refinement against the official LangChain implementation.
*   **Next Action:** Review the user-interaction loop of `scoping_node` to ensure it properly halts and resumes via LangGraph interrupts or frontend state.

### 2. STORM (Dynamic Outlines)
*   **Purpose:** Shift from linear search tasks to structured, hierarchical outlines (Sections -> Subsections) to guide the research.
*   **Status:** ✅ Implemented
*   **Evidence:**
    *   `outline_gen` node exists in `backend/src/agent/nodes.py`.
    *   Integrated into `backend/src/agent/graph.py` right before `generate_plan`.
*   **Missing/TODO items:** None explicitly identified for this node.
*   **Next Action:** Ensure the generated outline properly influences the `checklist_verifier`.

### 3. FlowSearch (Dynamic Task DAG)
*   **Purpose:** Analyze findings and dynamically update the `todo_list` (DAG) by adding new tasks, marking complete, or refining tasks.
*   **Status:** 🔴 Not Implemented (Scaffolded)
*   **Evidence:**
    *   `flow_update` node exists in `backend/src/agent/nodes.py` but currently `raises NotImplementedError("flow_update not implemented")`.
    *   Contains 5 structured TODOs (e.g., `[flow_update:4] DAG expansion logic`).
*   **Missing/TODO items:** The entire core logic of reading the results and modifying the state's `todo_list`.
*   **Next Action:** High priority: implement the `flow_update` state mutations.

### 4. ManuSearch (Structured Content Reader)
*   **Purpose:** Improve evidence extraction from raw web pages into structured `Evidence` items (Claim, Source URL, Context).
*   **Status:** ✅ Implemented
*   **Evidence:**
    *   `content_reader` exists in `backend/src/agent/nodes.py` and extracts evidence.
    *   Unit tests exist in `backend/tests/test_nodes.py` (`test_content_reader_extracts_evidence`).
*   **Missing/TODO items:** None identified.
*   **Next Action:** Monitor extraction quality; potentially add domain-specific readers as suggested in future extensions.

### 5. GPT Researcher (Recursive Depth)
*   **Purpose:** Handle deep topics by spinning up a fresh subgraph instance for sub-topic queries.
*   **Status:** 🟡 Partially Implemented / Stubbed
*   **Evidence:**
    *   `research_subgraph` exists in `backend/src/agent/nodes.py`.
    *   `graph.py` contains logic to `Send` state to `research_subgraph`.
*   **Missing/TODO items:**
    *   TODO in `nodes.py`: "[SOTA Deep Research] Recursive Trigger - Implement logic in reflection or a new 'router' node to decide when to call 'research_subgraph'."
    *   TODO in `graph.py`: "[SOTA Deep Research] Graph Wiring - Add conditional edges to route from 'reflection' or 'update_plan' to 'research_subgraph'."
*   **Next Action:** Fix the routing logic so the agent can autonomously trigger the recursion rather than relying on hardcoded map-reduce flows.

### 6. RhinoInsight (Checklist Verification)
*   **Purpose:** Audit the collected `evidence_bank` against the generated `outline` to flag unsupported claims and prevent hallucinations.
*   **Status:** ✅ Implemented
*   **Evidence:**
    *   `checklist_verifier` exists in `backend/src/agent/nodes.py`.
    *   Unit tests exist in `backend/tests/agent/test_checklist_verifier.py`.
    *   Wired in `graph.py` (`kg_enrich` -> `checklist_verifier` -> `reflection`).
*   **Missing/TODO items:** None identified.
*   **Next Action:** Ensure the reflection node properly interprets the verifier's output.

### 7. TTD-DR (Test-Time Denoising Refiner)
*   **Purpose:** Generate multiple draft answers, critique them, and synthesize a high-quality final report.
*   **Status:** ✅ Implemented
*   **Evidence:**
    *   `denoising_refiner` exists in `backend/src/agent/nodes.py` and is explicitly mapped to `finalize_answer`.
    *   Unit tests exist in `backend/tests/test_nodes.py` and `backend/tests/test_graph_mock.py` confirming the 3-step process.
*   **Missing/TODO items:** None identified.
*   **Next Action:** Evaluate latency impact of generating 3 drafts.

---

## C. TODO/Readme Accuracy Review

*   **Accurate TODOs:** The `04_SOTA_DEEP_RESEARCH_TASKS.md` accurately reflects that `scoping_node`, `outline_gen`, `content_reader`, `checklist_verifier`, and `denoising_refiner` are implemented (checked off). It accurately reflects that benchmarking is missing.
*   **Stale/Inaccurate Claims:**
    *   The readme claims `flow_update` (FlowSearch) is implemented (`[x] Implement flow_update Node`). However, the codebase (`nodes.py`) shows it `raises NotImplementedError` and is full of TODOs. **This is a critical discrepancy.**
    *   The readme claims `research_subgraph` is not implemented at all (`[ ] Implement research_subgraph Node`). However, the node *does* exist in `nodes.py` and there is partial wiring in `graph.py`. It is partially implemented.

---

## D. Implementation Map

| Strategy | Key Module(s) | Tests Available? | Role in Graph |
| :--- | :--- | :--- | :--- |
| Open Deep Research | `nodes.py` (`scoping_node`) | No explicit unit test | Runs before planning to clarify intent. |
| STORM | `nodes.py` (`outline_gen`) | No explicit unit test | Generates hierarchical outline pre-planning. |
| FlowSearch | `nodes.py` (`flow_update`) | No | Supposed to update tasks post-research (Stubbed). |
| ManuSearch | `nodes.py` (`content_reader`) | Yes (`test_nodes.py`) | Extracts structured evidence from raw HTML. |
| GPT Researcher | `nodes.py` (`research_subgraph`), `graph.py` | No | Subgraph node for deep-dive recursive search. |
| RhinoInsight | `nodes.py` (`checklist_verifier`) | Yes (`test_checklist_verifier.py`) | Audits evidence against outline. |
| TTD-DR | `nodes.py` (`denoising_refiner`) | Yes (`test_nodes.py`) | Synthesizes final report via multiple drafts. |

---

## E. Recommended Next Steps

1.  **Immediate Fix:** Un-check `flow_update` in `docs/tasks/04_SOTA_DEEP_RESEARCH_TASKS.md` to reflect reality, and prioritize implementing the DAG expansion logic in `nodes.py` (addressing `[flow_update:1]` through `[flow_update:5]`).
2.  **Architectural Wiring:** Complete the routing logic for `research_subgraph`. Currently, the node exists but the conditional edge to trigger it dynamically based on complexity is missing.
3.  **Benchmarking Integration:** Port `bench_race_eval.py` into a proper evaluation suite to test if these SOTA additions actually improve the Pass@1 score.
4.  **Test Coverage:** Add specific unit tests for `scoping_node` and `outline_gen` to match the rigorous testing already present for `denoising_refiner` and `checklist_verifier`.

## F. Limitations

*   **Runtime Evaluation:** I did not execute a full agent loop to verify the quality of the outputs (e.g., if the `denoising_refiner` actually improves results vs. a single pass).
*   **DeepBench Integration:** The repo contains analysis docs mentioning `bench_race_eval.py` integration, but I did not find active CI/CD pipelines running these benchmarks.
