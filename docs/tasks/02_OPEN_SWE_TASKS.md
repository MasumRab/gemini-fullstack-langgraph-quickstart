# Tasks: Open SWE Patterns

## 1. Prerequisites
*   [ ] `backend/src/agent/state.py` exists.
*   [ ] `backend/src/agent/graph.py` exists.

## 2. Dependencies
*   Completion of MCP Integration (optional, but recommended if the "Plan" involves file editing).

## 3. Detailed Task List

### Phase 1: State Definition
- [ ] **Define TypedDicts**
    - Action: Update `backend/src/agent/state.py`.
    - Subtask: Add `Todo` TypedDict (id, task, status, result).
    - Subtask: Update `OverallState` to include `plan: List[Todo]`.
    - Verification: Run static type checker or `pytest` to ensure no syntax errors.

### Phase 2: Logic Implementation
- [ ] **Update `generate_query` Node**
    - Action: Rename to `generate_plan`.
    - Subtask: Update prompt `query_writer_instructions` to generate a `Plan` (List of Todos) instead of just queries.
    - Subtask: Update output parser.

- [ ] **Implement `update_plan` Node**
    - Action: Create new function in `graph.py`.
    - Logic:
        1. Read `state.plan` and `state.web_research_result`.
        2. Prompt LLM: "Given the result, update the plan (mark done, add new tasks)."
        3. Parse output -> Update state.

- [ ] **Implement `execution_router`**
    - Action: Create routing logic.
    - Logic:
        ```python
        def router(state):
            pending = [t for t in state['plan'] if t['status'] == 'pending']
            if not pending: return "finalize"
            return "web_research" # or "tool_execution"
        ```

### Phase 3: Frontend Alignment
- [ ] **Update `planning_mode` logic**
    - Action: Ensure `planning_mode` node formats the `Todo` list correctly for the frontend.
    - Note: The frontend expects `planning_steps`. Map `Todo` objects to this format to maintain compatibility initially.

### Phase 4: Testing
- [ ] **Integration Test**
    - Action: Run a complex query ("Research X and then Compare with Y").
    - Success Criteria: Agent generates 2+ tasks, executes the first, updates plan (marks done), executes the second.
