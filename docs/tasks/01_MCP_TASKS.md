# Tasks: MCP Integration

## Status: ✅ Core Infrastructure Complete

The MCP (Model Context Protocol) integration has been successfully implemented with the following components:

### Completed Components
- ✅ **`backend/src/agent/mcp_server.py`** - FilesystemMCPServer implementation
  - Provides `read_file`, `write_file`, and `list_directory` tools
  - Includes path security validation
  - Supports async operations

- ✅ **`backend/src/agent/mcp_client.py`** - MCPToolUser implementation
  - Tool registry and execution logic
  - Planned tool sequence generation
  - LLM-driven tool planning capability

## Remaining Tasks

### Phase 1: Infrastructure Setup
- [x] **Install Python Dependencies**
    - Action: Add `langchain-mcp-adapters` and `mcp` to `requirements.txt` / `pyproject.toml`.
    - Verification: `pip install -r requirements.txt` succeeds. (Dependencies already present in `pyproject.toml`).

### Phase 2: Integration & Testing
- [ ] **Integrate MCP Tools into Agent Graph**
    - Action: Update `backend/src/agent/tools_and_schemas.py`
    - Subtask: Create `get_global_tools()` function that aggregates MCP tools + custom tools
    - Subtask: Initialize `FilesystemMCPServer` with appropriate allowed paths
    - Subtask: Create `MCPToolUser` instance and register with agent
    - Verification: Ensure the list of tools includes `read_file`, `write_file`, `list_directory`

- [ ] **Update Graph Nodes**
    - Action: Modify `backend/src/agent/nodes.py` or create new MCP-specific node
    - Subtask: Bind MCP tools to LLM in appropriate nodes (e.g., `web_research`, `finalize_answer`)
    - Verification: Verify LLM can see the file tools in its schema

- [x] **Create `backend/src/agent/mcp_config.py`**
    - [x] Subtask: Implement `MCPSettings` dataclass and loader.
    - [x] Subtask: Add `validate` function.
    - [x] Subtask: Add `McpConnectionManager` stub.
    - Code: `backend/src/agent/mcp_config.py`

- [ ] **Wrap Persistence Tools (New Task)**
    - Action: Create `backend/src/agent/mcp_persistence.py`.
    - Subtask: Wrap existing `persistence.py` functions in an MCP-compatible server/adapter.
    - Note: This avoids rewriting the core logic.

- [ ] **Refactor `tools_and_schemas.py`**
    - Subtask: Add `get_global_tools()` function that aggregates MCP tools + custom tools.
    - Note: Perform this incrementally. Start with `load_plan` and `save_plan`.
    - Verification: Ensure the list of tools includes `read_file`, `write_file` (from MCP).

### Phase 2: Testing & Validation
- [ ] **Create MCP Integration Tests**
    - Action: Create `backend/tests/test_mcp_integration.py`
    - Test Cases:
      - [ ] Test file reading from allowed paths
      - [ ] Test file writing to allowed paths
      - [ ] Test path security validation (reject unauthorized paths)
      - [ ] Test directory listing
      - [ ] Test planned tool sequence execution
    - Success Criteria: All tests pass

- [ ] **End-to-End Agent Test**
    - Action: Create test script that asks agent to "Write a summary of your research to summary.txt"
    - Success Criteria:
      - File `summary.txt` appears in the sandbox
      - Content is relevant to the research query
      - Agent uses MCP tools correctly

### Phase 3: Documentation & Polish
- [ ] **Update Documentation**
    - Action: Document MCP configuration in `README.md`
    - Subtask: Add examples of MCP tool usage
    - Subtask: Document allowed paths configuration
    - Subtask: Add troubleshooting guide

- [ ] **Configuration Management**
    - Action: Add MCP configuration to `backend/src/agent/configuration.py`
    - Subtask: Add `mcp_allowed_paths` configuration option
    - Subtask: Add `mcp_enabled` toggle
    - Verification: Configuration can be set via environment variables

## Notes
- The current implementation uses in-process MCP servers (Python classes)
- For external MCP servers via stdio/SSE, additional transport layer needed
- Consider adding more MCP servers (e.g., database, API) in future iterations
