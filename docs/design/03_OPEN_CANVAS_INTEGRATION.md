# Design: Open Canvas Integration (Artifacts)

## 1. Overview
This document details the strategy for implementing "Artifacts" (documents, code, schedules) that live alongside the chat, enabling a co-editing workflow similar to [Open Canvas](https://github.com/langchain-ai/open-canvas).

## 2. Trade-offs

| Feature | Chat-Only (Current) | Chat + Canvas (Proposed) |
| :--- | :--- | :--- |
| **UX** | Simple, linear | Rich, multi-modal (Split pane) |
| **Frontend Effort** | Low (Standard Chat UI) | High (Syncing state, collaborative editing logic) |
| **Value** | Good for Q&A | Essential for "Work Products" (Reports, Plans, Code) |
| **State Sync** | Simple (Append-only) | Complex (CRDTs or Last-Write-Wins) |

**Decision:** Implement a simplified Canvas initially (Last-Write-Wins). The "Research Agent" output is usually a report, which is better viewed as a document than a chat message.

## 3. Architecture

### Backend: Artifact State
We need to track "Artifacts" independently of the message history.

```python
class Artifact(TypedDict):
    id: str
    type: Literal["markdown", "code", "json"]
    title: str
    content: str
    version: int

class OverallState(TypedDict):
    # ...
    artifacts: Dict[str, Artifact]
```

### Streaming Logic
*   **Current:** `useStream` receives a stream of events/messages.
*   **Proposed:** The backend emits specific events for artifact updates (e.g., `artifact_created`, `artifact_updated`).
*   **Frontend:** The `useStream` hook (or a wrapper) parses these events. Chat messages go to the left pane; Artifact events update the state of the right pane.

### Frontend Components
1.  **SplitPaneLayout**: A resizable container (Left: Chat, Right: Artifact).
2.  **ArtifactRenderer**: Dynamically renders content based on `type` (Markdown vs CodeEditor).
3.  **ArtifactSelector**: If multiple artifacts exist, tabs to switch between them.

## 4. Proof of Concept (POC) Snippets

### A. Backend: Emitting Artifact Updates
The `finalize_answer` (or a dedicated `write_artifact`) node can emit custom data.

```python
# In graph.py node
def write_report_node(state: OverallState):
    report_content = generate_report(state)

    artifact = {
        "id": "final-report",
        "type": "markdown",
        "title": "Research Report",
        "content": report_content,
        "version": 1
    }

    # We can return this to update the graph state
    # AND LangGraph streaming will pick up the state change.
    return {
        "artifacts": {"final-report": artifact}
    }
```

### B. Frontend: Handling the Stream (`App.tsx` logic)

```typescript
// Conceptual modification to onUpdateEvent
onUpdateEvent: (event: any) => {
    // ... existing chat logic ...

    if (event.values?.artifacts) {
        // State update contains artifact data
        const updatedArtifacts = event.values.artifacts;
        setArtifactState(updatedArtifacts);
        // Trigger UI to open the updated artifact
        setActiveArtifactId(Object.keys(updatedArtifacts)[0]);
    }
}
```

## 5. Risks & Mitigations
*   **Risk:** Race conditions if user edits while Agent streams.
    *   *Mitigation:* Lock the artifact while Agent is generating. OR, simple "Last Write Wins" for V1.
*   **Risk:** Mobile responsiveness.
    *   *Mitigation:* Use a tabbed interface (Chat / Artifact) on small screens instead of split-pane.
