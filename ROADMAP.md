# Roadmap: Gemini Fullstack LangGraph Evolution

This document outlines the strategic roadmap for evolving the current "Research Agent" into a comprehensive "Long-term Planning & Todo Scheduling Agent". The goal is to integrate advanced capabilities from the LangChain ecosystem (`deepagents`, `open-swe`, `open-canvas`) while maintaining the simplicity and robustness of the existing infrastructure.

## Current Status
- **Core Functionality:** Functional Research Agent (Gemini + Google Search).
- **Architecture:** LangGraph backend (Python) + React/Vite frontend.
- **State Management:** Per-thread persistence via LangGraph.
- **Interaction:** Chat-based interface with streaming updates.

## Phase 1: Infrastructure & Robustness (Deep Agents Integration)
*Goal: Enhance the agent's ability to maintain context, manage persistent memory, and handle structured tasks, leveraging patterns from `deepagents`.*

### High Priority
- [ ] **Implement File-based Memory (Middleware):**
    - Port `FilesystemMiddleware` or similar logic from `deepagents`.
    - Allow the agent to read/write persistent files (e.g., `memories/user_preferences.md`, `todos/active_list.md`) to store long-term context beyond the immediate conversation window.
- [ ] **Standardize Tool Schemas:**
    - Refactor `tools_and_schemas.py` to align with `langchain-mcp-adapters` or standard Deep Agent tool definitions for better interoperability.
- [ ] **Enhance Error Handling & Recovery:**
    - Implement robust retry logic and error propagation inspired by Deep Agents' exception handling patterns.

### Low Priority
- [ ] **CLI Interface:** Add a CLI entry point similar to `deepagents` for headless operation and testing of long-running planning tasks.

## Phase 2: Planning & Interaction (Open SWE Patterns)
*Goal: Transform the agent from a passive researcher to an active planner capable of managing schedules and async tasks, inspired by `open-swe`.*

### High Priority
- [ ] **Async "Planner" Node:**
    - Introduce a dedicated "Planner" node in `graph.py` that runs before/parallel to execution.
    - This node maintains the "Todo List" state, deciding which tasks to tackle next.
- [ ] **Human-in-the-loop (HITL) for Plans:**
    - Update frontend to display the proposed "Plan" or "Todo List" separately from the chat.
    - Allow users to approve/edit the plan before the agent executes it (similar to Open SWE's planning step).
- [ ] **Background Task Execution:**
    - Enable the agent to run long-duration tasks (e.g., "Research these 5 topics over the next hour") without blocking the UI, notifying the user upon completion.

### Low Priority
- [ ] **GitHub Integration:**
    - Add tools for the agent to read/write GitHub issues if the "Todo" list extends to code tasks.

## Phase 3: Artifacts & Collaboration (Open Canvas Integration)
*Goal: Move beyond chat bubbles. The agent should produce and maintain live "artifacts" (documents, schedules, code) that the user can co-edit.*

### High Priority
- [ ] **Artifact UI State:**
    - Frontend: Split the view into "Chat" (left) and "Artifact/Canvas" (right).
    - Backend: Define `ArtifactState` in `OverallState` to track the content and version of the document being worked on.
- [ ] **Iterative Editing Loop:**
    - Implement the flow: `Agent generates Draft` -> `User Edits Draft` -> `Agent reads edits & updates Plan`.
    - Use `open-canvas` patterns for syncing state between the LLM's "mind" and the user's editor.

### Low Priority
- [ ] **Multi-Artifact Support:** Allow switching between different active documents (e.g., "Weekly Schedule" vs. "Research Report").

## Backlog / Jobs
*Open engineering tasks for contributors.*

1.  **Refactor `graph.py`:** Break down the monolithic graph definition into modular sub-graphs (e.g., `ResearchGraph`, `PlanningGraph`) to support complexity.
2.  **Frontend State Sync:** Improve the React hook (`useStream`) handling to support complex, multi-channel state (Chat + Artifacts + Plan).
3.  **Testing Infrastructure:** Add integration tests for the full graph flow using LangSmith.

## Architecture Log
*Record of significant architectural decisions.*

- **[Date]:** Initial Roadmap creation. Decision to prioritize Deep Agents memory patterns before UI overhauls.
