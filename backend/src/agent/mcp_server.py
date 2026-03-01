import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

try:
    import mcp.types as types  # noqa: F401
    from mcp.server import Server  # noqa: F401
    from mcp.types import (  # noqa: F401
        EmbeddedResource,
        ImageContent,
        TextContent,
        Tool,
    )
except ImportError:
    logger.warning("mcp package not available; MCP server features will be limited")

# 🛡️ Sentinel: Limit file read size to 1MB to prevent Memory Exhaustion / DoS
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB

# 🛡️ Sentinel: Limit directory listing count to prevent Output Flooding
MAX_DIR_ITEMS = 1000


class ToolResult:
    """Helper to match the spec's ToolResult expectation if not in mcp.types directly as that name."""

    def __init__(
        self, success: bool, data: Dict | None = None, error: str | None = None
    ):
        """
        Initialize a ToolResult representing the outcome of a tool operation.
        
        Parameters:
            success (bool): Whether the operation completed successfully.
            data (Dict | None): Optional result payload returned by the operation.
            error (str | None): Optional error message describing a failure.
        """
        self.success = success
        self.data = data
        self.error = error


class FilesystemMCPServer:
    """MCP Server for filesystem operations.

    Enables agent to read/write research artifacts.
    """

    def __init__(self, allowed_paths: List[str]):
        self.name = "filesystem"
        self.allowed_paths = [Path(p).resolve() for p in allowed_paths]
        self.tools = []
        self._register_tools()

    def _register_tools(self):
        """Register available filesystem tools."""
        # We store tools in a list of wrappers that include the handler
        self.tools.append(
            self._create_tool(
                name="read_file",
                description="Read contents of a file",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path to read"}
                    },
                    "required": ["path"],
                },
                handler=self.read_file,
            )
        )

        self.tools.append(
            self._create_tool(
                name="write_file",
                description="Write content to a file",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path to write"},
                        "content": {
                            "type": "string",
                            "description": "Content to write",
                        },
                    },
                    "required": ["path", "content"],
                },
                handler=self.write_file,
            )
        )

        self.tools.append(
            self._create_tool(
                name="list_directory",
                description="List files in a directory",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path"}
                    },
                    "required": ["path"],
                },
                handler=self.list_directory,
            )
        )

    def _create_tool(self, name, description, parameters, handler):
        """
        Create a lightweight tool object exposing metadata and a callable handler compatible with the MCP tool shape.
        
        Parameters:
            name (str): Tool name identifier.
            description (str): Short description of the tool's purpose.
            parameters (dict): Input schema for the tool; assigned to the returned object's `inputSchema` attribute to match the MCP spec.
            handler (callable): Callable that will be invoked to execute the tool.
        
        Returns:
            SimpleTool: An object with attributes `name`, `description`, `inputSchema`, and `handler` suitable for in-process use or exposure to MCP-compatible consumers.
        """
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
                self.inputSchema = parameters  # using inputSchema to match MCP spec
                self.handler = handler

        return SimpleTool(name, description, parameters, handler)

    def _check_path_allowed(self, path: str) -> bool:
        """
        Resolve the given filesystem path and determine whether it resides within any configured allowed path.
        
        Parameters:
            path (str): The filesystem path to check; may refer to an existing or non-existing location.
        
        Returns:
            bool: `True` if the resolved path equals or is inside one of the server's allowed paths, `False` otherwise.
        """
        try:
            resolved = Path(path).resolve()
            # If path doesn't exist yet (for write), check parent
            # But we still need to verify the intended path is safe.
            # resolve() handles '..' even if file doesn't exist, as long as path logic holds.

            return any(
                resolved == allowed or resolved.is_relative_to(allowed)
                for allowed in self.allowed_paths
            )
        except (OSError, ValueError):
            return False

    async def read_file(self, path: str) -> ToolResult:
        """
        Read and return the text content of a file.
        
        Checks that the provided path is within the server's allowed paths and that the file exists and is no larger than the configured maximum size; reads the file as UTF-8 text when allowed.
        
        Parameters:
            path (str): Filesystem path to the file to read. Must reside under the server's allowed paths.
        
        Returns:
            ToolResult: On success, `success` is `True` and `data` contains `{"content": <str>, "path": <str>}`. On failure, `success` is `False` and `error` contains a descriptive message (e.g., path not allowed, file not found, file too large, or other I/O errors).
        """
        if not self._check_path_allowed(path):
            logger.warning(f"Path traversal attempt blocked: {path}")
            return ToolResult(success=False, error=f"Path not allowed: {path}")

        try:
            p = Path(path)
            if not p.exists():
                return ToolResult(success=False, error=f"File not found: {path}")

            # 🛡️ Sentinel: Check file size before reading
            file_size = p.stat().st_size
            if file_size > MAX_FILE_SIZE:
                return ToolResult(
                    success=False,
                    error=f"File too large: {file_size} bytes (Limit: {MAX_FILE_SIZE} bytes)",
                )

            content = p.read_text(encoding="utf-8")
            return ToolResult(success=True, data={"content": content, "path": path})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def write_file(self, path: str, content: str) -> ToolResult:
        """
        Write UTF-8 text to a file at the given path.
        
        Writes the provided string to the filesystem, creating parent directories if necessary. Enforces a maximum content size (in characters and UTF-8 bytes) and rejects writes when the path is outside the server's allowed paths. Returns a ToolResult containing the written path and the number of bytes written on success, or an error message on failure.
        
        Returns:
            ToolResult: On success, `data` contains `{"path": path, "bytes_written": <int>}`; on failure, `error` contains a human-readable message.
        """
        if not self._check_path_allowed(path):
            logger.warning(f"Path traversal attempt blocked: {path}")
            return ToolResult(success=False, error=f"Path not allowed: {path}")

        # 🛡️ Sentinel: Check content size before writing to prevent Disk Fill DoS
        # Optimization: Check char count first to avoid encoding huge strings (OOM risk)
        if len(content) > MAX_FILE_SIZE:
            return ToolResult(
                success=False,
                error=f"Content too large: {len(content)} chars (Limit: {MAX_FILE_SIZE} bytes)",
            )

        content_bytes = content.encode("utf-8")
        if len(content_bytes) > MAX_FILE_SIZE:
            return ToolResult(
                success=False,
                error=f"Content too large: {len(content_bytes)} bytes (Limit: {MAX_FILE_SIZE} bytes)",
            )

        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return ToolResult(
                success=True, data={"path": path, "bytes_written": len(content)}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def list_directory(self, path: str) -> ToolResult:
        """
        List the entries in a directory, subject to the server's allowed path restrictions.
        
        Parameters:
            path (str): Filesystem path of the directory to list. The path must resolve inside the server's configured allowed paths.
        
        Returns:
            ToolResult: On success (`success=True`) `data` contains:
                - `files` (List[dict]): Entries with keys `name` (str), `type` ("file" or "directory"), and `size` (int or None).
                - `count` (int): Number of entries returned.
                - `truncated` (bool): `true` if the listing was cut off due to the MAX_DIR_ITEMS limit.
            On failure (`success=False`) `error` contains a human-readable message describing the problem (e.g., path not allowed, directory not found, or unexpected error).
        """
        if not self._check_path_allowed(path):
            logger.warning(f"Path traversal attempt blocked: {path}")
            return ToolResult(success=False, error=f"Path not allowed: {path}")

        try:
            dir_path = Path(path)
            if not dir_path.exists():
                return ToolResult(success=False, error=f"Directory not found: {path}")

            items = []
            count = 0
            for f in dir_path.iterdir():
                items.append(
                    {
                        "name": f.name,
                        "type": "file" if f.is_file() else "directory",
                        "size": f.stat().st_size if f.is_file() else None,
                    }
                )
                count += 1
                # 🛡️ Sentinel: Limit number of items
                if count >= MAX_DIR_ITEMS:
                    break

            return ToolResult(
                success=True,
                data={
                    "files": items,
                    "count": len(items),
                    "truncated": count >= MAX_DIR_ITEMS,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def start(self):
        """Start the MCP server.

        In a real MCP server, this would start stdio/sse transport.
        For this implementation (in-process usage), it is intentionally a no-op.
        """
