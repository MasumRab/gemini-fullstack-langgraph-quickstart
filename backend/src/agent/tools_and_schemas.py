import os
from typing import Any, List

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.mcp_config import McpConnectionManager
from agent.mcp_server import FilesystemMCPServer

# Global list to hold MCP tools config or instances
MCP_TOOLS: List[Any] = []


class SearchQueryList(BaseModel):
    query: List[str] = Field(
        description="A list of search queries to be used for web research."
    )
    rationale: str = Field(
        description="A brief explanation of why these queries are relevant to the research topic."
    )


class Todo(BaseModel):
    title: str = Field(
        description="A concise title for the task (acting as the search query)."
    )
    description: str | None = Field(
        description="A brief description of what to look for."
    )
    status: str = Field(description="Set to 'pending' by default.", default="pending")


class Plan(BaseModel):
    plan: List[Todo] = Field(description="A list of tasks (Todos) to execute.")
    rationale: str = Field(description="Brief explanation of the research strategy.")


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


class Subsection(BaseModel):
    title: str = Field(description="Title of the subsection.")
    description: str = Field(description="Content to cover in this subsection.")


class Section(BaseModel):
    title: str = Field(description="Title of the main section.")
    subsections: List[Subsection] = Field(description="List of subsections.")


class Outline(BaseModel):
    title: str = Field(description="Title of the research report.")
    sections: List[Section] = Field(description="List of main sections.")


def get_mcp_tools() -> List:
    """Retrieves MCP-based tools.
    Currently returns the Persistence tools (load_thread_plan, save_thread_plan).
    """
    manager = McpConnectionManager()
    # In a sync context, we might need to be careful with async tools,
    # but LangGraph handles async tools fine.
    return manager.get_persistence_tools()


async def get_tools_from_mcp(mcp_config=None):
    """Connects to an MCP server and loads available tools.
    """
    if not mcp_config or not mcp_config.enabled or not mcp_config.endpoint:
        return []

    try:
        from langchain_mcp_adapters.sessions import SSEConnection
        from langchain_mcp_adapters.tools import load_mcp_tools
        # TODO(priority=Low, complexity=Medium, owner=infra): Support Stdio connection if schema allows? For now assuming SSE via endpoint URL
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


async def get_global_tools() -> List[Any]:
    """Aggregates MCP tools (Persistence) and Custom tools (Filesystem).
    """
    tools = []

    # 1. Get Persistence Tools
    tools.extend(get_mcp_tools())

    # 2. Get Filesystem Tools (Internal Server)
    # Ensure workspace exists
    workspace_path = "./workspace"
    if not os.path.exists(workspace_path):
        os.makedirs(workspace_path)

    server = FilesystemMCPServer([workspace_path])

    # Explicit wrapping for the 3 known tools
    # This is safer than dynamic wrapper for now.

    async def read_file_wrapper(path: str) -> str:
        res = await server.read_file(path)
        return str(res.data) if res.success else f"Error: {res.error}"

    async def write_file_wrapper(path: str, content: str) -> str:
        res = await server.write_file(path, content)
        return str(res.data) if res.success else f"Error: {res.error}"

    async def list_directory_wrapper(path: str) -> str:
        res = await server.list_directory(path)
        return str(res.data) if res.success else f"Error: {res.error}"

    tools.append(
        StructuredTool.from_function(
            coroutine=read_file_wrapper,
            name="read_file",
            description="Read contents of a file. Args: path",
        )
    )

    tools.append(
        StructuredTool.from_function(
            coroutine=write_file_wrapper,
            name="write_file",
            description="Write content to a file. Args: path, content",
        )
    )

    tools.append(
        StructuredTool.from_function(
            coroutine=list_directory_wrapper,
            name="list_directory",
            description="List files in a directory. Args: path",
        )
    )

    return tools
