from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Any
import os
import shutil
import asyncio

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
    """
    Load MCP configuration from environment variables and return an MCPSettings instance.
    
    Reads these environment variables and maps them to MCPSettings fields:
    - MCP_ENABLED: "true" (case-insensitive) enables MCP; any other value disables it.
    - MCP_ENDPOINT: optional endpoint URL string.
    - MCP_API_KEY: optional API key string.
    - MCP_TIMEOUT: timeout in seconds parsed as an integer; defaults to 30 if missing or invalid.
    - MCP_TOOL_WHITELIST: comma-separated list of tool names; entries are stripped of whitespace and empty entries are ignored.
    
    Returns:
        MCPSettings: An immutable settings object populated from the environment.
    """
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
    """
    Validate MCPSettings and ensure required fields are present when MCP is enabled.
    
    Parameters:
        settings (MCPSettings): MCP configuration to validate.
    
    Raises:
        ValueError: If `settings.enabled` is True but `settings.endpoint` is missing.
    """
    if settings.enabled and not settings.endpoint:
        raise ValueError("MCP enabled but MCP_ENDPOINT missing")

class McpConnectionManager:
    """
    Manages connections to MCP servers (both internal and external).
    """

    def __init__(self, settings: Optional[MCPSettings] = None):
        """
        Initialize the connection manager and its tool registry.
        
        Parameters:
            settings (Optional[MCPSettings]): MCP configuration to use; if omitted, settings are loaded from environment variables via load_mcp_settings().
        """
        self.settings = settings or load_mcp_settings()
        self.tools = []
        self.clients = []



    def get_persistence_tools(self) -> List[StructuredTool]:
        """
        Create LangChain StructuredTool objects from the internal FastMCP persistence tools.
        
        Each persistence tool is converted into a StructuredTool; asynchronous tool functions are exposed via the `coroutine` field and synchronous functions via the `func` field. The tools' argument schemas are omitted so LangChain can infer parameters from the functions' signatures.
        
        Returns:
            list[StructuredTool]: StructuredTool instances corresponding to the persistence tools.
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
        Discover and return filesystem-related tools from an external Filesystem MCP server.
        
        Parameters:
            mount_dir (str): Local mount directory to expose to the filesystem MCP server; defaults to "./workspace".
        
        Returns:
            List[Any]: A list of tool objects provided by the external Filesystem MCP server. May be an empty list if the system dependency `npx` is not available or the external filesystem MCP integration is not configured; in that case a warning is printed and no tools are returned.
        """
        if not shutil.which("npx"):
            print("Warning: npx not found. Filesystem MCP server cannot be started.")
            return []

        # TODO: Implement full MultiServerMCPClient connection here.
        return []

    async def get_tools(self):
        """
        Aggregate all available tools from configured sources.
        
        Returns:
            tools (List[Any]): List of tool objects aggregated from persistence and, when MCP is enabled, from external MCP sources.
        """
        tools = self.get_persistence_tools()

        if self.settings.enabled:
            tools.extend(await self.get_filesystem_tools())

        return tools