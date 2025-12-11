# Architectural Alignment Strategy: The Overlay Pattern

**Goal:** Enable the local codebase to inherit updates from `google-gemini/gemini-fullstack-langgraph-quickstart` (upstream) while maintaining advanced features (Planning, MCP, RAG) with minimal merge conflicts.

## 1. The Core Problem
Currently, the local codebase **modifies** upstream files (`graph.py`, `state.py`, `App.tsx`) to add features. This creates "Hard Forks" where every upstream update requires a painful manual merge/conflict resolution.

## 2. Proposed Architecture: The Overlay Pattern

### Concept
Treat the upstream code as a **Base Library** that we import from, rather than a template we modify. Our features should live in an **Extension Layer** that wraps or injects into the Base.

### A. Backend: Builder Factory & State Inheritance

#### 1. The "Base" (Upstream)
*Ideally, we submit a PR to upstream to support this.*
Refactor `graph.py` to export a builder function, not just a compiled graph.

```python
# upstream/graph.py (Target State)
def get_builder() -> StateGraph:
    builder = StateGraph(OverallState)
    builder.add_node("generate_query", generate_query)
    # ... basic wiring ...
    return builder

# If upstream doesn't do this, we treat their file as "read-only"
# and import nodes directly if they are exported.
```

#### 2. The "Extension" (Local)
We create a new entry point `backend/src/agent/extended_graph.py` that imports the base and enhances it.

```python
# backend/src/agent/extended_graph.py
from agent.graph import get_builder as get_base_builder # From upstream file
from agent.state import OverallState as BaseState
from agent.extensions.planning import planning_node
from agent.extensions.mcp import mcp_tool_node

# 1. State Inheritance
class ExtendedState(BaseState):
    planning_steps: list[str]
    mcp_config: dict

# 2. Graph Extension
def build_extended_graph():
    # Start with the upstream structure
    builder = get_base_builder()

    # Modify the schema to use our ExtendedState
    # (Note: LangGraph makes swapping state schema tricky,
    #  better to have Upstream use a generic or open schema,
    #  OR we rebuild the graph using Upstream Node Functions)

    # Preferred: Rebuild using Upstream Nodes
    workflow = StateGraph(ExtendedState)

    # Import nodes from upstream (assuming they are public)
    from agent.nodes import generate_query, web_research

    workflow.add_node("generate_query", generate_query)
    workflow.add_node("web_research", web_research)

    # Add OUR nodes
    workflow.add_node("planning_node", planning_node)

    # Wire them together (Custom Edges)
    workflow.add_edge("generate_query", "planning_node")
    workflow.add_edge("planning_node", "web_research")

    return workflow.compile()
```

### B. Frontend: Composition over Modification

#### 1. Component Slots
Instead of editing `ChatMessagesView.tsx` to add "Planning Mode UI" inside the render loop, we should wrap it.

```tsx
// frontend/src/features/Planning/PlanningOverlay.tsx
export const PlanningOverlay = ({ children, threadState }) => {
  const planningContext = usePlanningState(threadState);

  return (
    <div className="layout">
      {planningContext.isActive && <PlanningPanel data={planningContext} />}
      <div className="main-chat">
        {children} {/* The upstream ChatMessagesView */}
      </div>
    </div>
  );
};
```

#### 2. App Wrapper
In `App.tsx`, we import the upstream `ChatMessagesView` (if exported) and wrap it.

```tsx
// frontend/src/App.tsx (Local)
import { ChatMessagesView } from './upstream/ChatMessagesView'; // Renamed/Moved upstream file
import { PlanningOverlay } from './features/Planning';

export default function App() {
  // ... hook setup ...

  return (
    <PlanningOverlay threadState={thread}>
       <ChatMessagesView messages={thread.messages} ... />
    </PlanningOverlay>
  );
}
```

## 3. Implementation Steps

1.  **Isolate Upstream:** Move current upstream-identical files to a dedicated directories (e.g., `backend/src/agent/base/` or just keep them clean in root).
2.  **Public API:** Ensure upstream files export their internal components/nodes (submit PRs to upstream if needed).
3.  **Extension Files:** Move all "Pro" logic (Planning, MCP, RAG) into `backend/src/agent/features/` or `frontend/src/features/`.
4.  **Wiring:** Create "assembler" files (`app_pro.py`, `AppPro.tsx`) that combine Base + Features.

## 4. Benefits
*   **Zero Conflict Merges:** You can `git pull upstream main` and it only updates the Base files. Your Extension files remain untouched.
*   **Clear Boundaries:** Easy to see what is "Stock" vs "Custom".
*   **Toggleable Features:** Easier to turn off "Pro" mode for debugging.
