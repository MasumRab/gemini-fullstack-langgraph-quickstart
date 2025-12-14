from typing import List, Optional, Any
from pydantic import BaseModel, Field


class SearchQueryList(BaseModel):
    query: List[str] = Field(
        description="A list of search queries to be used for web research."
    )
    rationale: str = Field(
        description="A brief explanation of why these queries are relevant to the research topic."
    )


class Reflection(BaseModel):
    is_sufficient: bool = Field(
        description="Whether the provided summaries are sufficient to answer the user's question."
    )
    knowledge_gap: str = Field(
        description="A description of what information is missing or needs clarification."
    )
    follow_up_queries: List[str] = Field(
        description="A list of follow-up queries to address the knowledge gap."
    )

# TODO: [MCP Integration] Create 'get_global_tools()' to aggregate MCP + Custom tools.
# See docs/tasks/01_MCP_TASKS.md
# Subtask: Add `get_global_tools()` function.
# Subtask: Ensure the list of tools includes `read_file`, `write_file` (from MCP).

async def get_tools_from_mcp(mcp_config=None) -> List[Any]:
    """
    Load tools via langchain-mcp-adapters.
    Connects to the MCP server defined in mcp_config.

    Note: This function is asynchronous because connecting to an MCP server
    (especially via SSE) involves network operations. Callers must await this function.
    """
    if mcp_config is None:
        try:
            from .mcp_config import load_mcp_settings
            mcp_config = load_mcp_settings()
        except ImportError:
             # Fallback if mcp_config module is not available or path issues
             return []

    if not mcp_config.enabled or not mcp_config.endpoint:
        return []

    try:
        from langchain_mcp_adapters.tools import load_mcp_tools
        from langchain_mcp_adapters.sessions import SSEConnection
    except ImportError:
        # langchain-mcp-adapters not installed
        return []

    # Headers for authentication if API key is present
    headers = {}
    if mcp_config.api_key:
         headers["Authorization"] = f"Bearer {mcp_config.api_key}"

    # We currently support SSE transport via HTTP/S endpoint
    connection = SSEConnection(
        transport="sse",
        url=mcp_config.endpoint,
        headers=headers if headers else None,
        timeout=mcp_config.timeout_seconds
    )

    try:
        # load_mcp_tools establishes the connection and returns LangChain compatible tools.
        # Ensure the environment supports async execution.
        tools = await load_mcp_tools(connection=connection)
        return tools
    except Exception as e:
        # Log error in a real app, here we just print or return empty
        # print(f"Error loading MCP tools: {e}")
        return []
