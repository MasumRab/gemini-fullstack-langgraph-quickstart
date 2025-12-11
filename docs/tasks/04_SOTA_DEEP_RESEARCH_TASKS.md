# Tasks: SOTA Deep Research Integration

## Status: 🔴 Not Started

This task list tracks the integration of features from verified state-of-the-art (SOTA) research agents: **Open Deep Research**, **STORM**, **FlowSearch**, **ManuSearch**, and **GPT Researcher**.

## 1. Scoping & Clarification (Open Deep Research)
*Goal: Prevent "garbage in, garbage out" by ensuring the agent understands the user's intent.*

- [ ] **Create `scoping_node`**
    - [ ] Logic: Analyze query → If ambiguous, generate clarifying questions → Wait for user input.

## 2. Dynamic Flow & Outlines (FlowSearch / STORM)
*Goal: Move from linear search to dynamic, structured research.*

- [ ] **Hierarchical Outline Generation** (STORM)
    - [ ] Update `planning_mode` to generate tree-structured outlines (Section -> Subsection).
- [ ] **Dynamic Graph Expansion** (FlowSearch)
    - [ ] Implement logic to "append" new branches to the execution graph based on intermediate findings (e.g., adding a sub-plan when a topic is complex).

## 3. Structured Content Reading (ManuSearch)
*Goal: Improve evidence extraction from raw web pages.*

- [ ] **Create `ContentReader` Node**
    - [ ] Input: Raw HTML/Text.
    - [ ] Output: Structured `Evidence` objects (Claim, Source, Context).

## 4. Recursive Research (GPT Researcher)
*Goal: Handle depth by allowing the agent to "dive deep".*

- [ ] **Refactor Graph for Recursion**
    - [ ] Allow `web_research` to call a `ResearchSubgraph` for specific sections.

## 5. Benchmarking
*Goal: Validate performance.*

- [ ] **DeepResearch-Bench** (muset-ai) setup.
- [ ] **ORION** (RUCAIBox) setup.
