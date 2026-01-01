# Integration Strategy: Long-term Planning & Scheduling Agent

This document serves as the **Strategy Index**. For detailed architectural designs, trade-offs, and implementation tasks, please refer to the linked documents below.

## 1. Model Context Protocol (MCP) Integration
*Goal: Standardize tooling and external system access.*

*   **Design Document:** [docs/design/01_MCP_INTEGRATION.md](./docs/design/01_MCP_INTEGRATION.md)
*   **Task List:** [docs/tasks/01_MCP_TASKS.md](./docs/tasks/01_MCP_TASKS.md)

### Summary
We are replacing ad-hoc Python tool definitions with `langchain-mcp-adapters`. This allows the agent to plug-and-play with external MCP servers (Filesystem, GitHub, Slack) without custom glue code.

---

## 2. Open SWE Patterns (Iterative Planning)
*Goal: Evolve from "Search Query Approver" to "Project Manager".*

*   **Design Document:** [docs/design/02_OPEN_SWE_PATTERNS.md](./docs/design/02_OPEN_SWE_PATTERNS.md)
*   **Task List:** [docs/tasks/02_OPEN_SWE_TASKS.md](./docs/tasks/02_OPEN_SWE_TASKS.md)

### Summary
We are transitioning the graph from a linear flow to a recursive "Plan -> Execute -> Reflect -> Update Plan" loop. The central state will move from a list of queries to a structured `List[Todo]` object, allowing for dynamic re-planning.

---

## 3. Open Canvas Integration (Artifacts)
*Goal: Move beyond chat bubbles to collaborative documents.*

*   **Design Document:** [docs/design/03_OPEN_CANVAS_INTEGRATION.md](./docs/design/03_OPEN_CANVAS_INTEGRATION.md)
*   **Task List:** [docs/tasks/03_OPEN_CANVAS_TASKS.md](./docs/tasks/03_OPEN_CANVAS_TASKS.md)

### Summary
We are introducing a split-pane UI. The backend will manage an `ArtifactState` (documents, code), which updates in real-time alongside the chat conversation, enabling a richer "Co-editing" experience.
