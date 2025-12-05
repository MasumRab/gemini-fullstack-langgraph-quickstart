# Integration Strategy: Long-term Planning & Scheduling Agent

This document serves as the deep-dive technical companion to `ROADMAP.md`. It details the specific strategies, trade-offs, and implementation tasks for integrating advanced LangChain ecosystem features into the Gemini Fullstack LangGraph Agent.

## 1. Model Context Protocol (MCP) Integration

### Overview
Adopt the [Model Context Protocol (MCP)](https://github.com/langchain-ai/langchain-mcp-adapters) to standardize how the agent interacts with external systems (FileSystem, GitHub, etc.), replacing ad-hoc Python tool definitions.

### Trade-offs

| Feature | Custom Python Tools (Current) | MCP Adapters (Proposed) |
| :--- | :--- | :--- |
| **Complexity** | Low (simple functions) | Medium (requires running MCP servers) |
| **Extensibility** | Linear effort (write code for every tool) | High (plug-and-play existing servers) |
| **Maintenance** | Manual updates for API changes | Offloaded to MCP server maintainers |
| **Portability** | Locked to this repo | Standard protocol usable by other agents |

**Decision:** Adopt MCP for "System Tools" (File I/O, Git) to future-proof the agent. Keep "Business Logic Tools" (Search, Reflection) as custom graph nodes for now.

### Architecture
*   **Current:** `tools_and_schemas.py` defines Pydantic models and functions directly.
*   **Target:**
    *   Install `langchain-mcp-adapters`.
    *   Configure `McpClient` to connect to local/remote MCP servers (e.g., `filesystem-server`).
    *   Inject MCP tools into the `web_research` or new `tool_execution` node.

### Implementation Tasks
- [ ] **Dependency Setup**
    - [ ] Add `langchain-mcp-adapters` to `pyproject.toml` / `requirements.txt`.
    - [ ] Add basic MCP server for FileSystem (e.g., `npx @modelcontextprotocol/server-filesystem`).
- [ ] **Tool Integration**
    - [ ] Create `backend/src/agent/mcp_config.py` to manage server connections.
    - [ ] Refactor `tools_and_schemas.py` to expose a `get_mcp_tools()` function.
- [ ] **Graph Update**
    - [ ] Update `OverallState` to support tool messages from MCP tools.

---

## 2. Open SWE Patterns (Iterative Planning)

### Overview
Transition from a linear "Search -> Summarize" loop to an iterative "Plan -> Execute -> Reflect" loop, inspired by [Open SWE](https://github.com/langchain-ai/open-swe). This allows the agent to maintain a long-running "Todo List".

### Trade-offs

| Feature | Static Plan (Current) | Dynamic Todo State (Proposed) |
| :--- | :--- | :--- |
| **User Control** | Low (Review initial queries only) | High (Edit/Add/Reorder tasks anytime) |
| **State Complexity** | Low (List[str]) | High (List[Todo] with status/deps) |
| **Predictability** | High (Deterministic flow) | Variable (Loop depends on reflection) |

**Decision:** Implement "Dynamic Todo State". The value of handling complex, multi-step research tasks outweighs the state management complexity.

### Architecture
*   **State:** detailed `Todo` object:
    ```python
    class Todo(TypedDict):
        id: str
        task: str
        status: Literal["pending", "in_progress", "done", "blocked"]
        result: Optional[str]
    ```
*   **Graph Flow:**
    *   `planning_mode`: Visualizes the `Todo` list.
    *   `reflection`: Now acts as a "Project Manager". Instead of just asking "Is this sufficient?", it updates the `Todo` list (marks current task done, adds new tasks).
    *   `planning_wait`: Allows the user to interrupt and modify the plan manually.

### Implementation Tasks
- [ ] **State Migration**
    - [ ] Define `Todo` and `PlanState` schemas in `agent/state.py`.
    - [ ] Update `OverallState` to replace `search_query: List[str]` with `plan: List[Todo]`.
- [ ] **Node Logic**
    - [ ] Update `generate_query` to produce an initial `List[Todo]`.
    - [ ] Create `update_plan_node`: LLM takes current context + results and outputs `PlanUpdate` (add/remove/update tasks).
- [ ] **Frontend Sync**
    - [ ] Ensure the frontend can render the structured `Todo` list (not just chat bubbles).

---

## 3. Open Canvas (Artifacts)

### Overview
Move beyond chat interactions by implementing "Artifacts" (documents, code, schedules) that live alongside the conversation, inspired by [Open Canvas](https://github.com/langchain-ai/open-canvas).

### Trade-offs

| Feature | Chat-Only (Current) | Chat + Canvas (Proposed) |
| :--- | :--- | :--- |
| **UX** | Simple, linear | Rich, multi-modal (requires split pane) |
| **Frontend Effort** | Low (Standard Chat UI) | High (Syncing state, collaborative editing) |
| **Value** | Good for Q&A | Essential for "Work Products" (Reports/Plans) |

**Decision:** Implement a simplified Canvas. The "Research Agent" output is usually a report, which is better viewed as a document than a chat message.

### Architecture
*   **Frontend:**
    *   Split the view: `ChatStream` (Left) | `ArtifactView` (Right).
    *   Listen for specific event types (e.g., `artifact_update`).
*   **Backend:**
    *   Add `artifacts` dict to `OverallState`.
    *   `finalize_answer` (or a new `write_report` node) emits updates to the artifact key.
    *   Use LangGraph's streaming events to push partial updates to the frontend.

### Implementation Tasks
- [ ] **Backend Artifacts**
    - [ ] Add `artifacts: Dict[str, str]` to `OverallState`.
    - [ ] Create a tool/node specifically for `update_artifact(id, content)`.
- [ ] **Frontend Layout**
    - [ ] Refactor `App.tsx` to support a resizable split-pane layout.
    - [ ] Create an `ArtifactRenderer` component (Markdown/Code support).
- [ ] **Streaming Logic**
    - [ ] Update `useStream` hook to demultiplex the stream: Chat messages go to Chat List, Artifact updates go to Canvas.
