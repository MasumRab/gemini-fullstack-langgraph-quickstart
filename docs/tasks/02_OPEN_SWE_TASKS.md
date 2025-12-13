# Tasks: Open SWE Patterns

## Status: 🟡 Partially Implemented

The foundation for Open SWE-style planning and execution is in place, but needs enhancement and testing.

### Completed Components
- ✅ **State Definition** - `backend/src/agent/state.py`
  - `OverallState` includes `todo_list: List[dict] | None`
  - `planning_steps: List[dict] | None` for frontend compatibility
  - `planning_status: str | None` for workflow control
  - `planning_feedback: Annotated[list, operator.add]` for user input

- ✅ **Planning Infrastructure** - `backend/src/agent/planning_router.py`
  - Planning router logic implemented
  - Routes between `planning_wait` and `web_research`

- ✅ **Planning Node** - `backend/src/agent/nodes.py`
  - `planning_mode()` function implemented
  - Integrated into multiple graph variants (linear, parallel, supervisor)

## Remaining Tasks

### Phase 1: Enhanced Planning Logic
- [ ] **Upgrade `planning_mode` Node**
    - Action: Update `backend/src/agent/nodes.py::planning_mode()`
    - Current: Generates `planning_steps` for frontend display
    - Enhancement Needed:
      - [ ] Generate structured `Todo` objects with `id`, `task`, `status`, `result` fields
      - [ ] Store in both `todo_list` (for execution) and `planning_steps` (for frontend)
      - [ ] Add priority/ordering to tasks
    - Verification: Planning output includes both formats

- [ ] **Implement `update_plan` Node**
    - Action: Create new function in `backend/src/agent/nodes.py`
    - Logic:
        1. Read `state.todo_list` and `state.web_research_result`
        2. Prompt LLM: "Given the result, update the plan (mark done, add new tasks, adjust priorities)"
        3. Parse LLM output → Update `todo_list` with new statuses
        4. Emit updated plan to frontend
    - Integration: Add to graph after research nodes
    - Verification: Plan updates correctly after each research iteration

### Phase 2: Execution Router
- [ ] **Implement `execution_router`**
    - Action: Create routing logic in `backend/src/agent/router.py` or `planning_router.py`
    - Logic:
        ```python
        def execution_router(state: OverallState) -> str:
            todo_list = state.get('todo_list', [])
            pending = [t for t in todo_list if t.get('status') == 'pending']

            if not pending:
                return "finalize_answer"  # All tasks complete

            # Determine next action based on task type
            next_task = pending[0]
            if next_task.get('type') == 'research':
                return "web_research"
            elif next_task.get('type') == 'file_operation':
                return "mcp_tools"  # If MCP integrated
            else:
                return "web_research"  # Default
        ```
    - Integration: Replace or enhance `planning_router`
    - Verification: Router correctly dispatches based on task queue

### Phase 3: Graph Integration
- [ ] **Update Graph Workflow**
    - Action: Modify `backend/src/agent/graph.py` (or variant graphs)
    - Changes:
      - [ ] Add `update_plan` node after `web_research`
      - [ ] Replace `planning_router` with `execution_router` (or add as separate router)
      - [ ] Add conditional edge: `web_research` → `update_plan` → `execution_router`
      - [ ] Ensure loop: `execution_router` → `web_research` (for next task)
    - Verification: Graph visualization shows iterative planning loop

### Phase 4: Frontend Alignment
- [ ] **Ensure Frontend Compatibility**
    - Action: Verify `frontend/src/hooks/useAgentState.ts` handles both formats
    - Current: Frontend expects `planning_steps`
    - Requirement: Continue populating `planning_steps` while also managing `todo_list`
    - Enhancement: Add UI to show task status (pending/in-progress/done)
    - Verification: Frontend displays plan with status updates

### Phase 5: Testing
- [ ] **Integration Tests**
    - Action: Create `backend/tests/test_open_swe_workflow.py`
    - Test Cases:
      - [ ] Single-task plan execution
      - [ ] Multi-task plan with sequential execution
      - [ ] Plan updates after each task completion
      - [ ] Router correctly selects next task
      - [ ] Finalization when all tasks complete
    - Success Criteria: All tests pass

- [ ] **End-to-End Test**
    - Action: Run complex query: "Research quantum computing, then compare it with classical computing"
    - Success Criteria:
      - [ ] Agent generates 2+ tasks in plan
      - [ ] Executes first task (research quantum computing)
      - [ ] Updates plan (marks first task done)
      - [ ] Executes second task (compare with classical)
      - [ ] Finalizes with comprehensive answer

## Dependencies
- MCP Integration (optional, but recommended for file editing tasks)
- Current graph structure (linear/parallel/supervisor variants)

## Notes
- The current `planning_mode` focuses on user confirmation workflow
- Open SWE pattern requires autonomous task execution with dynamic plan updates
- Consider adding task types: `research`, `file_edit`, `code_generation`, `analysis`
- Future: Integrate with MCP tools for actual file operations
