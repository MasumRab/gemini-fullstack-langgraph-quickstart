# Tasks: Open Canvas Integration

## 1. Prerequisites
*   [ ] Frontend environment (`npm install` has run).
*   [ ] Backend `OverallState` defined.

## 2. Dependencies
*   None strictly, but best done after "Open SWE" so the Artifacts can reflect the executed plan.

## 3. Detailed Task List

### Phase 1: Backend Support
- [ ] **Update State**
    - Action: Add `artifacts: Dict[str, Artifact]` to `OverallState` in `backend/src/agent/state.py`.

- [ ] **Create `Artifact` Tools/Nodes**
    - Action: Create a helper function/tool `update_artifact(id, content, type)`.
    - Action: Update `finalize_answer` to optionally emit an artifact instead of just text.

### Phase 2: Frontend Layout (React)
- [ ] **Layout Changes**
    - Action: Modify `frontend/src/App.tsx`.
    - Subtask: Create a split-pane layout (using CSS Grid or Flexbox). Left: `ChatMessagesView`, Right: `ArtifactView` (new component).
    - Subtask: Add a toggle button to show/hide the Artifact panel.

- [ ] **Create `ArtifactView` Component**
    - Action: Create `frontend/src/components/ArtifactView.tsx`.
    - Subtask: Support rendering Markdown (using `react-markdown`).
    - Subtask: Support rendering Code (using `prismjs` or similar).

### Phase 3: Streaming & Event Handling
- [ ] **Update `useStream` Handler**
    - Action: In `App.tsx`, inside `onUpdateEvent`:
    - Logic:
      ```javascript
      if (event.artifacts) {
          // Update local artifact state
          setArtifacts(event.artifacts);
          // Open the panel
          setIsArtifactOpen(true);
      }
      ```

### Phase 4: Polish
- [ ] **Loading States**
    - Action: Show a spinner in the Artifact panel when the agent is "writing" (i.e., when `finalize_answer` is active).

- [ ] **Verification**
    - Action: Ask the agent "Write a poem about AI".
    - Success Criteria: The poem appears in the Right Panel (Artifact), not just the chat bubble.
