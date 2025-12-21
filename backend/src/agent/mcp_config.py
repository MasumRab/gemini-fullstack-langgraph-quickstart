import shutil
import asyncio
import os
from typing import List, Any, Optional, Tuple
from dataclasses import dataclass, field
from langchain_core.tools import StructuredTool

# Import our internal MCP definition
from agent.mcp_persistence import mcp as persistence_mcp

@dataclass(frozen=True)
class MCPSettings:
    """Configuration settings for Model Context Protocol (MCP)."""
    enabled: bool
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    timeout_seconds: int = 30
    tool_whitelist: Tuple[str, ...] = field(default_factory=tuple)

def load_mcp_settings() -> MCPSettings:
    """Loads MCP settings from environment variables."""
    enabled_str = os.getenv("MCP_ENABLED", "false").lower()
    enabled = enabled_str == "true"

    endpoint = os.getenv("MCP_ENDPOINT")
    api_key = os.getenv("MCP_API_KEY")

    try:
        timeout = int(os.getenv("MCP_TIMEOUT", "30"))
    except ValueError:
        timeout = 30

    whitelist_str = os.getenv("MCP_TOOL_WHITELIST", "")
    whitelist = tuple(filter(None, [s.strip() for s in whitelist_str.split(",")]))

    return MCPSettings(
        enabled=enabled,
        endpoint=endpoint,
        api_key=api_key,
        timeout_seconds=timeout,
        tool_whitelist=whitelist
    )

def validate(settings: MCPSettings) -> None:
    """Validates the MCP settings."""
    if settings.enabled and not settings.endpoint:
        raise ValueError("MCP enabled but MCP_ENDPOINT missing")

# TODO(priority=High, complexity=High): [MCP Integration] Implement full McpConnectionManager with SSE support.
# Should handle connection pooling and error recovery.
# Subtask: Implement `McpConnectionManager` class.
# Subtask: Support SSE transport via HTTP/S endpoint.
class McpConnectionManager:
    """
    Manages connections to MCP servers (both internal and external).
    """

    def __init__(self, settings: Optional[MCPSettings] = None):
        self.settings = settings or load_mcp_settings()
        self.tools = []

    def get_persistence_tools(self) -> List[StructuredTool]:
        """
        Converts the internal FastMCP tools into LangChain tools.
        """
        lc_tools = []

        for name, tool_def in persistence_mcp._tool_manager._tools.items():
            # tool_def.fn is the actual python function.
            # We can use StructuredTool.from_function to wrap it.
            # LangChain will inspect the signature to generate args_schema.

            # Note: if the function is async, we should provide it as 'coroutine'
            # if it is sync, as 'func'.

            is_async = asyncio.iscoroutinefunction(tool_def.fn)

            lc_tool = StructuredTool.from_function(
                func=tool_def.fn if not is_async else None,
                coroutine=tool_def.fn if is_async else None,
                name=name,
                description=tool_def.description or "",
                # We omit args_schema here and let LangChain infer it from the function signature,
                # which matches what FastMCP did anyway.
            )
            lc_tools.append(lc_tool)

        return lc_tools

    async def get_filesystem_tools(self, mount_dir: str = "./workspace") -> List[Any]:
        """
        Returns tools from the external Filesystem MCP server.
        Uses langchain-mcp-adapters.
        """
        if not shutil.which("npx"):
            print("Warning: npx not found. Filesystem MCP server cannot be started.")
            return []

        try:
            from mcp import StdioServerParameters
            from langchain_mcp_adapters.client import MultiServerMCPClient
        except ImportError:
            print("Warning: langchain-mcp-adapters or mcp not installed.")
            return []

        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", os.path.abspath(mount_dir)],
            env=os.environ
        )

        # Note: In a real app, you might want to keep the client open.
        # Here we connect, get tools, and close (which might kill the server).
        # This is a limitation of this simple implementation.
        try:
            async with MultiServerMCPClient() as client:
                await client.connect_stdio("filesystem", server_params)
                tools = await client.get_tools()
                return tools
        except Exception as e:
            print(f"Error connecting to filesystem MCP: {e}")
            return []

    async def get_tools(self):
        """Aggregate all enabled tools."""
        tools = self.get_persistence_tools()

        if self.settings.enabled:
            # Connect to external endpoint if configured
            pass

        return tools
