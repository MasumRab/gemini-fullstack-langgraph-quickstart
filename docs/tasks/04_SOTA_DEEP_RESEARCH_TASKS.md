# Tasks: SOTA Deep Research Integration

## Status: 🔴 Not Started

This task list tracks the integration of features from verified state-of-the-art (SOTA) research agents: **Open Deep Research**, **STORM**, **ManuSearch**, and **GPT Researcher**.

## 1. Scoping & Clarification (Open Deep Research)
*Goal: Prevent "garbage in, garbage out" by ensuring the agent understands the user's intent before planning.*

- [ ] **Create `scoping_node`**
    - [ ] Define `ScopingState` (query, clarifications_needed, user_answers).
    - [ ] Create node logic: Analyze query → If ambiguous, generate clarifying questions → Wait for user input.
    - [ ] Integration: Insert before `planning_mode`.

## 2. Hierarchical Outlines (STORM)
*Goal: Move from linear search to structure-driven research.*

- [ ] **Define `Outline` Schema**
    - [ ] Create Pydantic models for `Section`, `Subsection`, `KeyPoint`.
- [ ] **Update `planning_mode`**
    - [ ] Prompt engineering: Instruct LLM to generate a `STORM`-style outline based on the scoped query.

## 3. Structured Content Reading (ManuSearch)
*Goal: Improve evidence extraction from raw web pages.*

- [ ] **Create `ContentReader` Node**
    - [ ] Input: Raw HTML/Text from `web_research`.
    - [ ] Logic: Use LLM to extract structured "Evidence" (Claim, Source, Context) tailored to the current plan step.
    - [ ] Output: List of `Evidence` objects.

## 4. Recursive Research (GPT Researcher)
*Goal: Handle depth by allowing the agent to "dive deep" into sub-topics.*

- [ ] **Refactor Graph for Recursion**
    - [ ] Create a `ResearchSubgraph` that can be called as a node.
    - [ ] Allow `web_research` to call `ResearchSubgraph` for a specific section if it lacks depth.

## 5. Benchmarking
*Goal: Validate performance against standard metrics.*

- [ ] **DeepResearch-Bench Setup**
    - [ ] Create a script `backend/scripts/run_benchmark.py`.
    - [ ] Load tasks from the `DeepResearch-Bench` (muset-ai) space.
- [ ] **ORION Benchmark Setup**
    - [ ] Load tasks from `RUC-AIBOX/ORION`.
    - [ ] Evaluate "Long-tail entity" reasoning capabilities.
