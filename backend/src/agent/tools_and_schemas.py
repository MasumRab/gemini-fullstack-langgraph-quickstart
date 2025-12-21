from typing import List, Optional, Any
from pydantic import BaseModel, Field
from agent.mcp_config import McpConnectionManager

# Global list of loaded MCP tools/Persistent tools
MCP_TOOLS: List[Any] = []

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


def get_mcp_tools() -> List:
    """
    Retrieves MCP-based tools.
    Currently returns the Persistence tools (load_thread_plan, save_thread_plan).
    """
    manager = McpConnectionManager()
    # In a sync context, we might need to be careful with async tools,
    # but LangGraph handles async tools fine.
    return manager.get_persistence_tools()

async def get_tools_from_mcp(mcp_config=None):
    """
    Connects to an MCP server and loads available tools.
    """
    if not mcp_config or not mcp_config.enabled or not mcp_config.endpoint:
        return []

    try:
        from langchain_mcp_adapters.tools import load_mcp_tools
        from langchain_mcp_adapters.sessions import SSEConnection
        # TODO: Support Stdio connection if schema allows? For now assuming SSE via endpoint URL
        # headers = {"Authorization": f"Bearer {mcp_config.api_key}"} if mcp_config.api_key else {}
        # NOTE: Test mocks SSEConnection(url=..., headers=...).
        
        # We need to construct arguments for SSEConnection dynamically based on availability
        conn_kwargs = {"url": mcp_config.endpoint}
        if mcp_config.api_key:
             conn_kwargs["headers"] = {"Authorization": f"Bearer {mcp_config.api_key}"}

        async with SSEConnection(**conn_kwargs) as session:
            return await load_mcp_tools(session)
    except ImportError:
        # Fallback or log if adapters not installed (though dependency is listed)
        return []
    except Exception as e:
        # Log error or return empty list so app startup doesn't crash on optional tool load
        print(f"Error loading MCP tools: {e}")
        return []
