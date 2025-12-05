# Technical Design: Iterative Planning & Scheduling Agent

## 1. Vision & Philosophy

The goal is to evolve the existing **Gemini Fullstack LangGraph Research Agent** into a **Long-term Planning & Scheduling Agent**.

**Core Constraint:** The scope is defined as "single -> multiple chained search queries depending on graph logic". This means we are **not** building a background cron-job server, but rather a powerful, interactive session where the agent can:
1.  **Plan:** Break down a complex user request into a Todo list.
2.  **Execute:** Perform research/tasks for each item.
3.  **Refine:** Update the plan dynamically based on findings (re-planning).
4.  **Persist:** Save the state of this plan so the user can return to it.

We adhere to the **"First Order Enhancement"** philosophy: modifications should be minimal, modular, and directly compatible with the original "Quickstart" architecture to facilitate easy updates from the upstream repo.

## 2. Architecture Overview

### Current Architecture
*   **Graph:** `generate_query` -> `planning_mode` -> `web_research` -> `reflection` -> `finalize_answer`.
*   **State:** Ephemeral `OverallState` stored in LangGraph memory.
*   **Frontend:** Simple chat interface.

### Proposed Architecture
We will enhance the "Planning" and "Memory" aspects without rewriting the core graph.

#### A. Enhanced Graph Flow
The `planning_mode` node becomes the "Central Brain".
1.  **Start:** User Request.
2.  **Plan:** `planning_mode` generates/updates the `TodoState`.
3.  **Approve:** `planning_wait` (HITL) for user confirmation.
4.  **Execute:** `web_research` (or other tools) executes the *current active task*.
5.  **Reflect:** `reflection` analyzes results *and* updates the `TodoState` (marking done, adding new tasks).
6.  **Loop:** Return to `planning_mode` to pick the next task.

#### B. Data Structures
New keys in `OverallState`:
*   `todo_list`: List[Dict] (Task ID, Description, Status [Pending, InProgress, Done], Dependencies).
*   `artifacts`: Dict[str, str] (Content of documents being written).

## 3. Feature Deep Dives

### 3.1. Memory (Deep Agents Pattern)
*   **Problem:** Current state is lost if the browser/server restarts (unless using persistent DB, but file-based is simpler for this context).
*   **Solution:** **File-based Persistence Tool**.
*   **Implementation:**
    *   Add a simple `FileSystemTool` (MCP-style).
    *   The agent saves the `todo_list` to `plans/<session_id>.json`.
    *   On startup, the agent checks for an existing plan.

### 3.2. Planning (Open SWE Pattern)
*   **Problem:** `planning_mode` currently just lists search queries.
*   **Solution:** **Iterative Todo Manager**.
*   **Implementation:**
    *   Update `planning_mode` to manage a structured `Todo` object.
    *   Allow the user to edit the plan via the Chat UI (using `/plan` commands or dedicated UI controls).
    *   *Graph Change:* The `reflection` node must output *updates to the plan*, not just follow-up queries.

### 3.3. Artifacts (Open Canvas Pattern)
*   **Problem:** The "Final Answer" is just a chat message.
*   **Solution:** **Live Canvas UI**.
*   **Implementation:**
    *   **Frontend:** Add a split-pane view (Chat Left | Canvas Right).
    *   **Backend:** The agent emits a special "Artifact Update" event.
    *   **Interaction:** User sees the "Report" building in real-time on the right while chatting on the left.

### 3.4. Tooling (MCP Adapters)
*   **Problem:** Adding new tools (e.g., File I/O, GitHub) requires custom python code for each.
*   **Solution:** **LangChain MCP Adapters**.
*   **Implementation:**
    *   Use `langchain-mcp-adapters` to load tools from standard MCP servers.
    *   This allows us to "plug in" a FileSystem MCP server or GitHub MCP server without writing custom tool logic in `graph.py`.

## 4. Tradeoffs

| Feature | Option A (Chosen) | Option B (Alternative) | Why Option A? |
| :--- | :--- | :--- | :--- |
| **Memory** | **File-based JSON** | Postgres/Redis | Simpler to debug, portable, fits "Quickstart" ethos. |
| **Planning** | **In-Graph Logic** | Separate "Planner Agent" | Keeps the graph single-threaded and easier to reason about. |
| **Tooling** | **MCP Adapters** | Native LangChain Tools | Future-proofs the agent for the growing MCP ecosystem. |
| **UI** | **Split Pane (Vite)** | Separate Dashboard App | Keeps the frontend unified and easy to deploy. |

## 5. Implementation Roadmap (Phased)

1.  **Phase 1: Foundation (Memory & Tools)**
    *   Install `langchain-mcp-adapters`.
    *   Implement `save_plan` and `load_plan` tools.
    *   Update `graph.py` to load plan on start.

2.  **Phase 2: The Loop (Planning Logic)**
    *   Refactor `planning_mode` to handle `Todo` structures.
    *   Update `reflection` to modify the plan.

3.  **Phase 3: Experience (Canvas UI)**
    *   Update Vite frontend with Split Pane.
    *   Handle "Artifact" streams.
