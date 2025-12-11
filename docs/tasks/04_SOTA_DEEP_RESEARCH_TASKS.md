# Tasks: SOTA Deep Research Integration

## Status: 🔴 Not Started

This task list tracks the integration of features from verified state-of-the-art (SOTA) research agents: **Open Deep Research**, **STORM**, and **GPT Researcher**.

## 1. Scoping & Clarification (Open Deep Research)
*Goal: Prevent "garbage in, garbage out" by ensuring the agent understands the user's intent before planning.*

- [ ] **Create `scoping_node`**
    - [ ] Define `ScopingState` (query, clarifications_needed, user_answers).
    - [ ] Create node logic: Analyze query → If ambiguous, generate clarifying questions → Wait for user input.
    - [ ] Integration: Insert before `planning_mode`.
- [ ] **Frontend Interaction**
    - [ ] Update frontend to handle a "Clarification Request" event (distinct from a normal plan approval).

## 2. Hierarchical Outlines (STORM)
*Goal: Move from linear search to structure-driven research.*

- [ ] **Define `Outline` Schema**
    - [ ] Create Pydantic models for `Section`, `Subsection`, `KeyPoint`.
- [ ] **Update `planning_mode`**
    - [ ] Prompt engineering: Instruct LLM to generate a `STORM`-style outline based on the scoped query.
    - [ ] Store outline in `OverallState`.
- [ ] **Update `web_research`**
    - [ ] Logic change: Iterate through *Sections* of the outline, not just flat queries.

## 3. Recursive Research (GPT Researcher)
*Goal: Handle depth by allowing the agent to "dive deep" into sub-topics.*

- [ ] **Refactor Graph for Recursion**
    - [ ] Create a `ResearchSubgraph` that can be called as a node.
    - [ ] Allow `web_research` to call `ResearchSubgraph` for a specific section if it lacks depth.
- [ ] **Depth Control**
    - [ ] Add `depth` and `breadth` parameters to the configuration.
    - [ ] Enforce a `max_depth` to prevent infinite loops.

## 4. Verification & Citations (General SOTA)
*Goal: Ensure high fidelity and reduce hallucinations.*

- [ ] **Implement `check_citation` Tool**
    - [ ] Logic: Given a claim and a URL, scrape the URL and verify if the claim is supported.
- [ ] **Add `verification_node`**
    - [ ] Run after `web_research`.
    - [ ] For each key claim in the generated answer, run `check_citation`.
    - [ ] If verification fails, trigger a "Repair" search.

## 5. Benchmarking
*Goal: Validate performance against standard metrics.*

- [ ] **DeepResearch-Bench Setup**
    - [ ] Create a script `backend/scripts/run_benchmark.py`.
    - [ ] Load tasks from the `DeepResearch-Bench` dataset (HuggingFace).
    - [ ] Run the agent against 10 sample tasks.
    - [ ] Log `Pass@1` and `Citation Quality`.
