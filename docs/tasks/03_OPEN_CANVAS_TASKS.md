# Tasks: Open Canvas Integration

## Status: 🟡 Backend Ready, Frontend Pending

The backend state includes artifact support, but the frontend UI components need to be implemented.

### Completed Components
- ✅ **Backend State** - `backend/src/agent/state.py`
  - `OverallState` includes `artifacts: dict | None`
  - Ready to store and manage artifacts

### Missing Components
- ❌ **Frontend Layout** - Split-pane design not implemented
- ❌ **ArtifactView Component** - No artifact rendering component
- ❌ **Artifact Tools** - No backend helper functions for artifact creation

## Remaining Tasks

### Phase 1: Backend Support
- [ ] **Create Artifact Helper Functions**
    - Action: Create `backend/src/agent/artifact_tools.py`
    - Functions to implement:
      ```python
      def create_artifact(id: str, content: str, type: str, title: str) -> dict:
          """Create a new artifact object"""
          return {
              "id": id,
              "content": content,
              "type": type,  # "markdown", "code", "html", "json"
              "title": title,
              "created_at": datetime.now().isoformat()
          }

      def update_artifact(artifacts: dict, id: str, content: str) -> dict:
          """Update existing artifact or create new one"""
          # Implementation
      ```
    - Verification: Functions return properly formatted artifact objects

- [ ] **Update `finalize_answer` Node**
    - Action: Modify `backend/src/agent/nodes.py::finalize_answer()`
    - Enhancement:
      - [ ] Detect when answer should be an artifact (code, long-form content, etc.)
      - [ ] Call `create_artifact()` helper
      - [ ] Add artifact to `state["artifacts"]`
      - [ ] Include artifact reference in message
    - Verification: Artifacts appear in state output

- [ ] **Add Artifact Tools to Agent**
    - Action: Update `backend/src/agent/tools_and_schemas.py`
    - Subtask: Create `save_artifact` tool that LLM can call
    - Subtask: Bind tool to appropriate nodes
    - Verification: LLM can create artifacts via tool calls

### Phase 2: Frontend Layout (React)
- [ ] **Design Split-Pane Layout**
    - Action: Modify `frontend/src/App.tsx`
    - Implementation:
      - [ ] Create CSS Grid or Flexbox layout
      - [ ] Left pane: `ChatMessagesView` (existing)
      - [ ] Right pane: `ArtifactView` (new component)
      - [ ] Add resize handle between panes (optional)
      - [ ] Add toggle button to show/hide artifact panel
    - Styling:
      - [ ] Responsive design (collapse on mobile)
      - [ ] Smooth transitions
      - [ ] Consistent with existing UI theme
    - Verification: Layout renders correctly at different screen sizes

- [ ] **Create `ArtifactView` Component**
    - Action: Create `frontend/src/components/ArtifactView.tsx`
    - Features:
      - [ ] **Markdown Rendering**
        - Use `react-markdown` or `marked`
        - Support syntax highlighting for code blocks
      - [ ] **Code Rendering**
        - Use `prismjs` or `highlight.js`
        - Add copy-to-clipboard button
        - Support multiple languages
      - [ ] **HTML Rendering**
        - Sanitize HTML with `DOMPurify`
        - Render in sandboxed iframe
      - [ ] **JSON Rendering**
        - Pretty-print with syntax highlighting
        - Collapsible tree view (optional)
    - UI Elements:
      - [ ] Artifact title header
      - [ ] Type indicator badge
      - [ ] Timestamp
      - [ ] Action buttons (copy, download, edit)
    - Verification: All artifact types render correctly

- [ ] **Add Artifact State Management**
    - Action: Update `frontend/src/hooks/useAgentState.ts`
    - Changes:
      - [ ] Add `artifacts` to state interface
      - [ ] Add `currentArtifactId` to track active artifact
      - [ ] Add `setCurrentArtifact()` function
    - Verification: Artifact state updates correctly

### Phase 3: Streaming & Event Handling
- [ ] **Update Stream Handler**
    - Action: Modify `frontend/src/App.tsx` stream event handler
    - Logic:
      ```typescript
      const handleStreamUpdate = (event: StreamEvent) => {
        // Existing message handling...

        if (event.artifacts) {
          // Update artifact state
          setArtifacts(event.artifacts);

          // Auto-open panel for new artifacts
          const newArtifactIds = Object.keys(event.artifacts);
          if (newArtifactIds.length > 0) {
            setCurrentArtifact(newArtifactIds[newArtifactIds.length - 1]);
            setIsArtifactPanelOpen(true);
          }
        }
      };
      ```
    - Verification: Artifacts appear in real-time as agent creates them

- [ ] **Add Artifact Notifications**
    - Action: Show toast/notification when new artifact is created
    - Implementation: Use existing notification system or add new one
    - Verification: User is notified of new artifacts

### Phase 4: Polish & UX
- [ ] **Loading States**
    - Action: Add loading indicators
    - Locations:
      - [ ] Artifact panel shows spinner when `finalize_answer` is active
      - [ ] Skeleton loader while artifact content is streaming
    - Verification: Loading states display correctly

- [ ] **Empty States**
    - Action: Design empty state for artifact panel
    - Content:
      - Message: "No artifacts yet"
      - Suggestion: "Ask the agent to create a document, code, or analysis"
      - Icon/illustration
    - Verification: Empty state shows when no artifacts exist

- [ ] **Artifact History**
    - Action: Add artifact list/history view
    - Features:
      - [ ] List all artifacts from current conversation
      - [ ] Click to view specific artifact
      - [ ] Search/filter artifacts
    - Verification: Users can navigate between multiple artifacts

### Phase 5: Testing & Verification
- [ ] **Backend Tests**
    - Action: Create `backend/tests/test_artifacts.py`
    - Test Cases:
      - [ ] Artifact creation
      - [ ] Artifact updates
      - [ ] Multiple artifacts in single conversation
      - [ ] Artifact serialization/deserialization
    - Success Criteria: All tests pass

- [ ] **Frontend Tests**
    - Action: Create `frontend/src/components/ArtifactView.test.tsx`
    - Test Cases:
      - [ ] Markdown rendering
      - [ ] Code rendering with syntax highlighting
      - [ ] Copy-to-clipboard functionality
      - [ ] Panel show/hide toggle
    - Success Criteria: All tests pass

- [ ] **End-to-End Tests**
    - Test Scenarios:
      - [ ] **Poem Test**: "Write a poem about AI"
        - Success: Poem appears in artifact panel as markdown
      - [ ] **Code Test**: "Write a Python function to calculate fibonacci"
        - Success: Code appears with syntax highlighting and copy button
      - [ ] **Analysis Test**: "Create a comparison table of programming languages"
        - Success: Table appears in artifact panel
    - Verification: All scenarios work end-to-end

## Dependencies
- Backend artifact state (✅ Complete)
- Frontend React components
- Markdown/code rendering libraries

## Notes
- Artifact panel should be collapsible to maximize chat space
- Consider adding artifact versioning for iterative edits
- Future: Allow users to edit artifacts and send back to agent
- Future: Export artifacts to various formats (PDF, DOCX, etc.)
