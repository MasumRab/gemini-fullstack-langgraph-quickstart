import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from mcp import Tool
from mcp.server.fastmcp import FastMCP # Attempting to use High Level API if available, or fallback to manual server
import logging

# We will use the standard MCPServer class from mcp (low level) as per spec, or FastMCP if it's easier.
# The spec uses MCPServer but imports seem slightly different in latest mcp.
# Let's try to follow the spec provided closely, assuming `mcp` package structure.
# If `mcp` package has changed, we might need to adjust.
# Based on "from mcp import MCPServer, Tool, ToolResult", this looks like a specific version.

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent, EmbeddedResource, ImageContent
    import mcp.types as types
except ImportError:
    # Fallback or different import structure
    pass

logger = logging.getLogger(__name__)

class ToolResult:
    """Helper to match the spec's ToolResult expectation if not in mcp.types directly as that name"""
    def __init__(self, success: bool, data: Optional[Dict] = None, error: Optional[str] = None):
        self.success = success
        self.data = data
        self.error = error

class FilesystemMCPServer:
    """
    MCP Server for filesystem operations.
    Enables agent to read/write research artifacts.
    """

    def __init__(self, allowed_paths: List[str]):
        self.name = "filesystem"
        self.allowed_paths = [Path(p).resolve() for p in allowed_paths]
        self.tools = []
        self._register_tools()

    def _register_tools(self):
        """Register available filesystem tools"""

        # We store tools in a list of wrappers that include the handler
        self.tools.append(self._create_tool(
            name="read_file",
            description="Read contents of a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"}
                },
                "required": ["path"]
            },
            handler=self.read_file
        ))

        self.tools.append(self._create_tool(
            name="write_file",
            description="Write content to a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write"},
                    "content": {"type": "string", "description": "Content to write"}
                },
                "required": ["path", "content"]
            },
            handler=self.write_file
        ))

        self.tools.append(self._create_tool(
            name="list_directory",
            description="List files in a directory",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path"}
                },
                "required": ["path"]
            },
            handler=self.list_directory
        ))

    def _create_tool(self, name, description, parameters, handler):
        """Helper to create a tool object with a handler attached"""
        # In a real MCP server, we would use the SDK's Tool class.
        # Here we create a simple object that holds the metadata and handler
        # so our MCPToolUser can consume it directly (in-process)
        # OR we can serve it.
        # The spec implies "plug-and-play with external MCP servers", but also
        # implements it as a python class here.

        class SimpleTool:
            def __init__(self, name, description, parameters, handler):
                self.name = name
                self.description = description
                self.inputSchema = parameters # using inputSchema to match MCP spec
                self.handler = handler

        return SimpleTool(name, description, parameters, handler)

    def _check_path_allowed(self, path: str) -> bool:
        """Security: ensure path is within allowed directories"""
        try:
            resolved = Path(path).resolve()
            # If path doesn't exist yet (for write), check parent
            if not resolved.exists() and not resolved.parent.exists():
                 # Create parents logic is in write_file, but for check we need a base
                 # We check if resolved path starts with any allowed path
                 pass

            return any(
                str(resolved).startswith(str(allowed))
                for allowed in self.allowed_paths
            )
        except Exception:
            return False

    async def read_file(self, path: str) -> ToolResult:
        """Read file contents"""
        if not self._check_path_allowed(path):
            return ToolResult(
                success=False,
                error=f"Path not allowed: {path}"
            )

        try:
            p = Path(path)
            if not p.exists():
                 return ToolResult(success=False, error=f"File not found: {path}")

            content = p.read_text(encoding='utf-8')
            return ToolResult(
                success=True,
                data={"content": content, "path": path}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def write_file(self, path: str, content: str) -> ToolResult:
        """Write content to file"""
        if not self._check_path_allowed(path):
            return ToolResult(success=False, error=f"Path not allowed: {path}")

        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding='utf-8')
            return ToolResult(
                success=True,
                data={"path": path, "bytes_written": len(content)}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def list_directory(self, path: str) -> ToolResult:
        """List directory contents"""
        if not self._check_path_allowed(path):
            return ToolResult(success=False, error=f"Path not allowed: {path}")

        try:
            dir_path = Path(path)
            if not dir_path.exists():
                 return ToolResult(success=False, error=f"Directory not found: {path}")

            files = [
                {
                    "name": f.name,
                    "type": "file" if f.is_file() else "directory",
                    "size": f.stat().st_size if f.is_file() else None
                }
                for f in dir_path.iterdir()
            ]
            return ToolResult(
                success=True,
                data={"files": files, "count": len(files)}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def start(self):
        # In a real MCP server, this would start stdio/sse transport.
        # For this implementation (in-process usage in notebooks), it's a no-op
        # or sets up internal state.
        pass
