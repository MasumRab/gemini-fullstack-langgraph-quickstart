# Roadmap: Gemini Fullstack LangGraph Evolution

This document outlines the strategic roadmap for evolving the current "Research Agent" into a "Long-term Planning & Scheduling Agent".

**Detailed Strategy:** For technical trade-offs, architecture, and granular task breakdowns, please refer to [INTEGRATION_STRATEGY.md](./INTEGRATION_STRATEGY.md).

**Deep Research Analysis:** For a comparative analysis of this agent vs. state-of-the-art "Deep Research" implementations (and integration plans), see [docs/analysis/DEEP_RESEARCH_LANDSCAPE.md](./docs/analysis/DEEP_RESEARCH_LANDSCAPE.md).

## Current Status
- **Core Functionality:** Functional Research Agent with Basic Planning Mode (`planning_mode`, `planning_wait`).
- **Architecture:** LangGraph backend (Python) + React/Vite frontend.
- **State Management:** Per-thread persistence via LangGraph.
- **Interaction:** Chat-based interface with streaming updates.

## Phase 1: Infrastructure & Robustness (Deep Agents & MCP)
*Goal: Enhance the agent's ability to maintain context and extend its toolset using standard protocols.*

### High Priority
- [ ] **Standardize Tooling (MCP):**
    - [x] Foundation: Config module `mcp_config.py` created and tested.
    - [x] Wiring: Agent graph updated to load MCP settings (disabled by default).
    - [x] Install `langchain-mcp-adapters` (Included in `pyproject.toml`).
    - [x] Refactor `tools_and_schemas.py` to use MCP adapters for tool definitions.
- [ ] **Implement File-based Memory:**
    - [x] Create simple `load_plan` and `save_plan` tools. (Implemented in `persistence.py` & wrapped).
    - [x] Allow the agent to persist the `TodoState` to a local JSON file to survive server restarts.

## Phase 2: SOTA Deep Research Features
*Goal: Integrate verified patterns from Open Deep Research, STORM, FlowSearch, ManuSearch, and GPT Researcher.*

### High Priority
- [ ] **Scoping & Clarification (Open Deep Research):**
    - [ ] Implement a pre-planning "Scoping Node" that asks the user clarifying questions.
- [ ] **Hierarchical Outlines (STORM):**
    - [ ] Upgrade `planning_mode` to generate structured outlines (Section -> Subsection).
- [ ] **Dynamic Knowledge Flow (FlowSearch):**
    - [ ] Enable the planner to dynamically expand the graph (DAG) based on intermediate findings.
- [ ] **Structured Content Reading (ManuSearch):**
    - [ ] Implement a specialized `ContentReader` node that extracts evidence from retrieved pages.
- [ ] **Recursive Research (GPT Researcher):**
    - [ ] Enable the `web_research` node to "recurse" (call the graph again) for complex sub-topics.

## Phase 3: Planning & Interaction (Open SWE Patterns)
*Goal: Transform the agent from a "Search Query Approver" to a "Task Manager".*

### High Priority
- [ ] **Enhance `planning_mode`:**
    - [ ] Transition from simple `search_query` lists to structured `Todo` objects.
    - [ ] Implement logic to update the plan based on `reflection` output.
- [ ] **Dynamic Re-planning:**
    - [ ] Update `reflection` node to output *Plan Updates*.

## Phase 4: Artifacts & Collaboration (Open Canvas Integration)
*Goal: Move beyond chat bubbles. The agent should produce and maintain live "artifacts" that the user can co-edit.*

### High Priority
- [ ] **Artifact UI State:**
    - [ ] Frontend: Split the view into "Chat" (left) and "Artifact/Canvas" (right).
- [ ] **Real-time Artifact Streaming:**
    - [ ] Stream updates to the Artifact panel separately from the chat stream.

## Architecture Log
*Record of significant architectural decisions.*

- **[Date]:** Roadmap updated to align with verified SOTA Deep Research architectures (Open Deep Research, STORM, FlowSearch, ManuSearch, GPT Researcher).
- **[Date]:** Roadmap updated to reflect "Iterative Chained Planning" vision and existing `planning_mode` implementation.
- **[Date]:** Initial Roadmap creation. Decision to prioritize Deep Agents memory patterns before UI overhauls.
