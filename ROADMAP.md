# Roadmap: Gemini Fullstack LangGraph Evolution

This document outlines the strategic roadmap for evolving the current "Research Agent" into a "Long-term Planning & Scheduling Agent".

**Detailed Strategy:** For technical trade-offs, architecture, and granular task breakdowns, please refer to [INTEGRATION_STRATEGY.md](./INTEGRATION_STRATEGY.md).

**Deep Research Analysis:** For a comparative analysis of this agent vs. state-of-the-art "Deep Research" implementations (and integration plans), see [docs/analysis/DEEP_RESEARCH_COMPARISON.md](./docs/analysis/DEEP_RESEARCH_COMPARISON.md).

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

### Low Priority
- [ ] **CLI Interface:** Add a CLI entry point for headless operation of the planning loop.

## Phase 2: Planning & Interaction (Open SWE Patterns)
*Goal: Transform the agent from a "Search Query Approver" to a "Task Manager".*

### High Priority
- [ ] **Enhance `planning_mode`:**
    - [ ] Transition from simple `search_query` lists to structured `Todo` objects (Status: Pending, InProgress, Done).
    - [ ] Implement logic to update the plan based on `reflection` output (e.g., adding new sub-tasks).
- [ ] **Dynamic Re-planning:**
    - [ ] Update `reflection` node to output *Plan Updates* in addition to *Follow-up Queries*.
    - [ ] Ensure the graph loops back to `planning_mode` to confirm the updated plan.

### Low Priority
- [ ] **Background Task Execution:**
    - [ ] Enable the agent to run long-duration tasks without blocking the UI.

## Phase 3: Artifacts & Collaboration (Open Canvas Integration)
*Goal: Move beyond chat bubbles. The agent should produce and maintain live "artifacts" (documents, schedules, code) that the user can co-edit.*

### High Priority
- [ ] **Artifact UI State:**
    - [ ] Frontend: Split the view into "Chat" (left) and "Artifact/Canvas" (right).
    - [ ] Backend: Define `ArtifactState` in `OverallState` to track the content of the "Final Report" or "Plan".
- [ ] **Real-time Artifact Streaming:**
    - [ ] Stream updates to the Artifact panel separately from the chat stream.

## Backlog / Jobs
*Open engineering tasks for contributors.*

1.  **Refactor `graph.py`:** Break down the monolithic graph definition into modular sub-graphs (e.g., `ResearchGraph`, `PlanningGraph`) to support complexity.
2.  **Frontend State Sync:** Improve the React hook (`useStream`) handling to support complex, multi-channel state (Chat + Artifacts + Plan).
3.  **Testing Infrastructure:** Add integration tests for the full graph flow using LangSmith.

## Architecture Log
*Record of significant architectural decisions.*

- **[Date]:** Added Deep Research Analysis and Benchmarking integration strategy.
- **[Date]:** Roadmap updated to reflect "Iterative Chained Planning" vision and existing `planning_mode` implementation.
- **[Date]:** Initial Roadmap creation. Decision to prioritize Deep Agents memory patterns before UI overhauls.
