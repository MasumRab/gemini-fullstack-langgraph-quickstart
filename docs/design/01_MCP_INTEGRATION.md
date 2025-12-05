# Design: Model Context Protocol (MCP) Integration

## 1. Overview
This document details the strategy for integrating the [Model Context Protocol (MCP)](https://github.com/langchain-ai/langchain-mcp-adapters) into the Research Agent. The goal is to standardize how the agent interacts with external systems (FileSystem, GitHub, etc.) by replacing ad-hoc Python tool definitions with universal MCP adapters.

## 2. Trade-offs

| Feature | Custom Python Tools (Current) | MCP Adapters (Proposed) |
| :--- | :--- | :--- |
| **Complexity** | Low (simple Python functions) | Medium (requires managing MCP server connections) |
| **Extensibility** | Linear effort (must write code for every new tool) | High (plug-and-play existing MCP servers) |
| **Maintenance** | Manual updates for API changes | Offloaded to MCP server maintainers |
| **Portability** | Locked to this repo | Standard protocol usable by other agents/IDEs |
| **Latency** | In-process (fast) | IPC/Network (slight overhead) |

**Decision:** Adopt MCP for "System Tools" (File I/O, Git) to future-proof the agent. Keep "Business Logic Tools" (Search, Reflection) as custom graph nodes or standard LangChain tools for now.

## 3. Architecture

### Current State
Tools are defined in `backend/src/agent/tools_and_schemas.py` as Pydantic models or simple functions. They are bound to the LLM directly in `web_research` (using Google GenAI `tools` parameter).

### Proposed Architecture

1.  **MCP Configuration Manager**: A singleton or config module (`backend/src/agent/mcp_config.py`) responsible for:
    *   Starting/Connecting to local MCP servers (e.g., `stdio` or `sse`).
    *   Aggregating tools from multiple servers.
    *   Converting MCP tools to LangChain/GenAI compatible tool formats.

2.  **Graph Integration**:
    *   The `web_research` node currently handles Google Search.
    *   **New Node**: `tool_execution` (or enhancing `web_research`).
    *   For the "Planning/Scheduling" agent evolution, we likely need a dedicated `execute_tools` node that can handle File I/O separately from Web Research.

### Data Flow Diagram (Conceptual)

```mermaid
graph TD
    A[Start] --> B[Planning Mode]
    B --> C{Action Required?}
    C -- Web Search --> D[Web Research Node]
    C -- File/Git Ops --> E[Tool Execution Node]
    D --> F[Reflection/Validation]
    E --> F
    E -.-> MCP[MCP Server (e.g. Filesystem)]
```

## 4. Proof of Concept (POC) Snippets

### A. Dependency Setup
`pyproject.toml` or `requirements.txt`:
```text
langchain-mcp-adapters
mcp
```

### B. MCP Client Configuration (`backend/src/agent/mcp_config.py`)

```python
# POC: How to initialize an MCP client for a filesystem server
from langchain_mcp_adapters.client import MultiServerMCPClient

async def get_mcp_tools(mount_path: str):
    """
    Connects to a local filesystem MCP server and returns LangChain-compatible tools.
    """
    client = MultiServerMCPClient()

    # Example: Connecting to a stdio-based server (requires the server binary installed)
    # In a real setup, we might use 'npx' or a docker container.
    await client.connect_server(
        name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", mount_path],
    )

    # Convert to LangChain tools
    return client.get_tools()
```

### C. Integrating into Graph State

We don't necessarily need to change `OverallState` just to hold tools, but we need to ensure the `messages` history correctly records `ToolMessage` outputs from MCP tools.

## 5. Risks & Mitigations
*   **Risk:** MCP Server availability in the runtime environment (e.g., Docker container).
    *   *Mitigation:* Ensure `Dockerfile` includes necessary runtimes (Node.js for `npx` servers, Python for python servers).
*   **Risk:** Latency in tool execution.
    *   *Mitigation:* Use persistent connections; avoid restarting servers per request.
