import shutil
import asyncio
from typing import List, Any
from langchain_core.tools import StructuredTool

# Import our internal MCP definition
from agent.mcp_persistence import mcp as persistence_mcp

class McpConnectionManager:
    """
    Manages connections to MCP servers (both internal and external).
    """

    def __init__(self):
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

        return []
