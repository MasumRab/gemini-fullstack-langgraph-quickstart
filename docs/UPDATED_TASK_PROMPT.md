# Master Task List: Long-term Planning & Ecosystem Integration

This document outlines the master plan for evolving the Research Agent. It serves as the entry point for the "Task Master" agent to orchestrate the implementation.

**Status:** A high-level roadmap exists in `ROADMAP.md`. Detailed technical strategies are documented in `INTEGRATION_STRATEGY.md`.

## Core Requirements & Strategy

1.  **Documentation First:** Prioritize modular, easy-to-understand documentation.
2.  **File Structure:**
    *   `ROADMAP.md`: Executive Summary.
    *   `INTEGRATION_STRATEGY.md`: Technical Index.
    *   `docs/design/*.md`: Architectural Designs & Trade-offs.
    *   `docs/tasks/*.md`: Granular Execution Plans.

## Master Implementation Plan

### Phase 1: Model Context Protocol (MCP)
*Standardize tooling using `langchain-mcp-adapters`.*

*   [ ] **Execute Task List:** [docs/tasks/01_MCP_TASKS.md](./docs/tasks/01_MCP_TASKS.md)
    *   Install Dependencies (`langchain-mcp-adapters`).
    *   Configure `McpClient`.
    *   Refactor `web_research` node to use MCP tools.

### Phase 2: Open SWE Patterns
*Enhance the "Planning Loop" to handle structured `Todo` tasks.*

*   [ ] **Execute Task List:** [docs/tasks/02_OPEN_SWE_TASKS.md](./docs/tasks/02_OPEN_SWE_TASKS.md)
    *   Migrate State (`Todo`, `PlanState`).
    *   Implement `generate_plan` and `update_plan` nodes.
    *   Implement `execution_router`.

### Phase 3: Open Canvas
*Implement "Artifacts" that update in real-time.*

*   [ ] **Execute Task List:** [docs/tasks/03_OPEN_CANVAS_TASKS.md](./docs/tasks/03_OPEN_CANVAS_TASKS.md)
    *   Update State (`ArtifactState`).
    *   Frontend: Implement Split-pane Layout.
    *   Frontend: Implement `ArtifactRenderer`.
    *   Backend: Stream Artifact events.

## Reference Links
*   **MCP:** [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters)
*   **Agent Patterns:** [deepagents](https://github.com/langchain-ai/deepagents)
*   **Frontend/Interaction:** [open-swe](https://github.com/langchain-ai/open-swe), [open-canvas](https://github.com/langchain-ai/open-canvas)
