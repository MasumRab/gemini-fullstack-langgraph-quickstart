# SOTA Deep Research Sources, Benchmarks, and Future Roadmap

*This document serves as a companion to the `04_SOTA_DEEP_RESEARCH_STATUS.md` report. It ensures we are tracking the right external state-of-the-art (SOTA) deep research strategies, benchmarks, and implementation patterns.*

## 1. Benchmark Catalog

To evaluate deep research agents rigorously, we must rely on standardized benchmarks that test for accuracy, citation fidelity, and multi-step reasoning.

| Benchmark | What it Measures | Relevance to Repo | Current Status | Integration Path |
| :--- | :--- | :--- | :--- | :--- |
| **DeepResearch-Bench** | Report Quality (RACE) and Citation Accuracy (FACT). | Direct evaluation of long-form research generation and hallucination prevention. | Partial (We have `bench_race_eval.py` stubbed based on this). | Integrate into a CI/CD test suite comparing generated reports against a gold-standard subset using our Gemini LLM as a judge. |
| **BrowseComp** | Multi-hop browser navigation, persistence, and complex web task completion. | Tests if the agent can handle sequential web interactions beyond simple API search queries. | Missing. | Implement a test subset to evaluate our web-scraper/reader node's robustness over long workflows. |
| **GAIA** | General AI Assistant benchmark (reasoning, tool use, web browsing). | The standard for complex, multi-modal, and multi-step reasoning tasks. | Missing. | Add a local test suite with 10-20 GAIA-style questions to test the planner and tool routing. |
| **Humanity’s Last Exam (HLE)** | Extremely difficult expert-level multi-disciplinary questions. | Stress-tests the agent's depth, recursion logic (`research_subgraph`), and ability to synthesize complex, novel answers. | Missing. | Use for manual spot-checking and edge-case evaluations of the recursive subgraph logic. |
| **SimpleQA** | Strict factuality and hallucination detection on short answers. | Provides a baseline for the `checklist_verifier` to ensure the agent doesn't hallucinate basic facts before synthesis. | Missing. | Build a unit test suite for the `checklist_verifier` using SimpleQA data. |
| **ORION** | Open-web reasoning over long-tail entities (used in ManuSearch). | Tests the `content_reader`'s ability to extract structured evidence from obscure sources. | Missing. | Add long-tail queries to our regression tests to validate the `content_reader`. |
| **Internal `bench_race_eval.py`** | Custom adaptation of DeepResearch-Bench's RACE metric. | Serves as our primary internal gating mechanism for report quality. | Stubbed in `docs/reference`. | Needs to be moved to `backend/src/eval` and integrated into a runnable evaluation tool/node. |

## 2. SOTA Technique Catalog

This catalog summarizes the external frameworks guiding our architecture, expanding on the implementation status report.

### Open Deep Research / LangChain
*   **Problem Solved:** "Garbage in, garbage out" due to ambiguous initial queries.
*   **Design Pattern:** Clarification loop (Scoping Phase) prior to execution.
*   **Repo Status:** ✅ Implemented (`scoping_node`).
*   **Recommended Action:** Ensure the node can properly interrupt/resume execution in the LangGraph setup.

### STORM / Co-STORM (Stanford)
*   **Problem Solved:** Linear searches miss the broader context and alternative perspectives.
*   **Design Pattern:** Hierarchical outline generation (Sections -> Subsections) and persona-based query formulation.
*   **Repo Status:** ✅ Implemented (`outline_gen`).
*   **Recommended Action:** Maintain; consider adding "perspective/persona" generation to diversify search queries.

### FlowSearch
*   **Problem Solved:** Static, rigid plans fail when new, unexpected information is discovered.
*   **Design Pattern:** Dynamic Task DAG (Directed Acyclic Graph) expansion based on search results.
*   **Repo Status:** 🔴 Scaffolded/Missing (`flow_update` raises `NotImplementedError`).
*   **Recommended Action:** **High Priority.** Implement the logic to analyze results, mark tasks complete, and spawn new dependent tasks dynamically.

### ManuSearch
*   **Problem Solved:** Raw HTML/text dumps overwhelm the LLM's context window.
*   **Design Pattern:** Structured webpage reading; extracting discrete `Evidence` objects (Claim, URL, Context).
*   **Repo Status:** ✅ Implemented (`content_reader`).
*   **Recommended Action:** Maintain; expand with domain-specific readers (e.g., academic vs. news) if needed.

### GPT Researcher
*   **Problem Solved:** Complex topics require deeper, isolated dives that clutter the main agent's state.
*   **Design Pattern:** Recursive subgraphs (Agent spawns sub-agents for specific sub-topics).
*   **Repo Status:** 🟡 Partially Implemented (Node `research_subgraph` exists, but dynamic conditional routing is missing).
*   **Recommended Action:** Complete the LangGraph wiring to allow the `reflection` or `flow_update` nodes to trigger this recursively.

### RhinoInsight-style Verifiers
*   **Problem Solved:** LLMs hallucinate claims that aren't supported by the gathered evidence.
*   **Design Pattern:** Checklist Verification (Auditing gathered evidence against the initial plan).
*   **Repo Status:** ✅ Implemented (`checklist_verifier`).
*   **Recommended Action:** Maintain; integrate a metric for "Effective Citation Count" into the node's output.

### TTD-DR (Test-Time Denoising)
*   **Problem Solved:** Single-pass drafting often produces noisy, unstructured, or incomplete reports.
*   **Design Pattern:** Diffusion/Decomposition (Generate multiple drafts, critique, and merge into a final report).
*   **Repo Status:** ✅ Implemented (`denoising_refiner`).
*   **Recommended Action:** Maintain; optimize prompt instructions based on benchmark feedback.

## 3. Recommendations Beyond the Existing 7 Strategies

To push the agent to the actual SOTA frontier, we must incorporate patterns beyond the initial checklist:

1.  **Dynamic Task Graph Expansion:** Instead of a fixed linear plan generated upfront, the system should operate as an evolving DAG where discoveries trigger new branches of inquiry (Addresses the `flow_update` gap).
2.  **Explicit Source Diversity & Contradiction Handling:** The agent currently aggregates information but does not explicitly seek out or resolve conflicting sources. We should add a "Contradiction Resolution" step before final synthesis.
3.  **Measurable Citation Scoring:** The `checklist_verifier` should output a quantifiable "Citation Accuracy Score" and "Effective Citation Count" to reject drafts that fall below a threshold.
4.  **Browse-Persistence Testing:** Implement evaluations that require the agent to maintain state across multiple page interactions (e.g., clicking through pagination or logging in), inspired by BrowseComp.
5.  **Benchmark-Driven Gating:** Final report generation should be gated by an internal evaluation score (using a smaller, faster model) before presenting to the user.

## 4. Evidence-Backed Source List

*   **DeepResearch-Bench**: [HuggingFace Leaderboard (muset-ai)](https://huggingface.co/spaces/muset-ai/DeepResearch-Bench-Leaderboard) - *Relevant for RACE/FACT metrics to evaluate long-form reports.*
*   **FlowSearch Paper**: [Advancing deep research with dynamic structured knowledge flow](https://arxiv.org/abs/2510.08521) - *Relevant for `flow_update` DAG expansion logic.*
*   **ManuSearch Paper**: [Democratizing Deep Search in Large Language Models](https://arxiv.org/abs/2505.18105) - *Relevant for `content_reader` structured extraction and ORION benchmark.*
*   **RhinoInsight Paper**: [Improving Deep Research through Control Mechanisms](https://arxiv.org/abs/2511.18743) - *Relevant for `checklist_verifier` logic.*
*   **STORM**: [Stanford OVAL GitHub](https://github.com/stanford-oval/storm) - *Relevant for `outline_gen` and hierarchical structuring.*
*   **GAIA Benchmark**: [GAIA Leaderboard](https://huggingface.co/spaces/gaia-benchmark/leaderboard) - *Relevant for general assistant multi-step reasoning evaluation.*
*   **Humanity's Last Exam**: [HLE Dataset](https://huggingface.co/datasets/cais/hle) - *Relevant for testing the recursive depth bounds of `research_subgraph`.*

## 5. Frontend Control Surface

*See [04_SOTA_DEEP_RESEARCH_FRONTEND_PLAN.md](04_SOTA_DEEP_RESEARCH_FRONTEND_PLAN.md) for details on how these techniques will be exposed and configured via the UI.*

## 6. Updated Implementation Roadmap

Priorities are ranked based on resolving critical repo gaps and maximizing benchmark impact.

| Rank | Task / Strategy | Priority Class | Impact / Effort | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Fix FlowSearch `flow_update`** | High | High Impact / Low-Med Effort | The repo currently claims this is done, but it throws `NotImplementedError`. Fixing this enables dynamic, reactive research. |
| **2** | **Wire GPT Researcher `research_subgraph`** | High | High Impact / Med Effort | The node exists but isn't routed dynamically. Wiring this enables true deep recursive research for complex topics. |
| **3** | **Integrate `bench_race_eval.py`** | High | High Impact / High Effort | We need a quantitative baseline (RACE/FACT) to prove these SOTA additions actually work. |
| **4** | **Citation Quality Checks** | Medium | Med Impact / Low Effort | Enhance `checklist_verifier` to output measurable effective citation counts and accuracy scores. |
| **5** | **BrowseComp/GAIA Local Subsets** | Medium | Med Impact / High Effort | Establish testing suites for multi-hop browsing and complex tool reasoning to prevent regressions. |
| **6** | **Contradiction Handling** | Optional | Med Impact / Med Effort | Advanced feature to improve report quality by explicitly addressing conflicting sources. |
