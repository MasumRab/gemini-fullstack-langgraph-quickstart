# Tasks: MCP Integration

## 1. Prerequisites
*   [ ] Python environment active.
*   [ ] Node.js installed (for `server-filesystem`).

## 2. Dependencies
*   None. (This is a foundational infrastructure step).

## 3. Detailed Task List

### Phase 1: Infrastructure Setup
- [ ] **Install Python Dependencies**
    - Action: Add `langchain-mcp-adapters` and `mcp` to `requirements.txt` / `pyproject.toml`.
    - Verification: `pip install -r requirements.txt` succeeds.

- [ ] **Install MCP Server (Filesystem)**
    - Action: Ensure `npx` is available.
    - Action: Verify `@modelcontextprotocol/server-filesystem` can run via `npx`.
    - Snippet: `npx @modelcontextprotocol/server-filesystem --help`

### Phase 2: Configuration & Code
- [ ] **Create `backend/src/agent/mcp_config.py`**
    - Subtask: Implement `McpConnectionManager` class.
    - Subtask: Implement method `connect_filesystem(path: str)`.
    - Pseudocode:
      ```python
      class McpConfig:
          def __init__(self):
              self.clients = []
          async def get_filesystem_tools(self, mount_dir):
              # ... logic from design doc ...
      ```

- [ ] **Refactor `tools_and_schemas.py`**
    - Subtask: Add `get_global_tools()` function that aggregates MCP tools + custom tools.
    - Verification: Ensure the list of tools includes `read_file`, `write_file` (from MCP).

### Phase 3: Integration
- [ ] **Update `graph.py`**
    - Subtask: In `web_research` (or new node), bind these tools to the LLM.
    - Verification: Verify LLM can see the file tools in its schema.

- [ ] **Test**
    - Action: Create a test script `tests/test_mcp.py` that spins up the agent and asks it to "Write a file named test.txt".
    - Success Criteria: File `test.txt` appears in the sandbox.
