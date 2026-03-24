import os
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass(frozen=True)
class MCPSettings:
    """Configuration settings for Model Context Protocol (MCP)."""
    enabled: bool
    endpoint: str | None = None
    api_key: str | None = None
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

# Fine-grained implementation guide for MCP Integration:
#
# TODO(priority=High, complexity=Low): [MCP:1] Define SSE client interface
# - Create abstract base class for MCP transport
# - Define methods: connect(), disconnect(), send_message(), receive_stream()
#
# TODO(priority=High, complexity=Medium): [MCP:2] Implement SSE transport
# - Use httpx or aiohttp for Server-Sent Events
# - Handle reconnection with exponential backoff
# - Parse SSE event format (event:, data:, id:)
#
# TODO(priority=Medium, complexity=Medium): [MCP:3] Connection pooling
# - Maintain pool of persistent connections
# - Implement health checks and automatic reconnection
# - Thread-safe connection acquisition/release
#
# TODO(priority=Medium, complexity=Low): [MCP:4] Error recovery
# - Catch and log transport errors
# - Retry failed tool calls with backoff
# - Return graceful fallback on persistent failure
#
# TODO(priority=Low, complexity=Low): [MCP:5] Metrics and observability
# - Track connection latency, success/failure rates
# - Integrate with Langfuse spans
class McpConnectionManager:
    def __init__(self, settings: MCPSettings | None = None):
        self.settings = settings or load_mcp_settings()
        self.clients = []

    def get_persistence_tools(self) -> List:
        """Returns persistence tools wrapped for LangChain.
        """
        from langchain_core.tools import StructuredTool

        from agent.mcp_persistence import load_thread_plan, save_thread_plan
        
        return [
            StructuredTool.from_function(
                func=load_thread_plan,
                name="load_thread_plan",
                description="Loads the plan and artifacts for a specific thread from the local file system."
            ),
            StructuredTool.from_function(
                func=save_thread_plan,
                name="save_thread_plan",
                description="Saves the plan and artifacts for a specific thread to the local file system."
            )
        ]

    async def get_tools(self):
        # TODO(priority=High, complexity=Medium): [MCP:6] Implement actual SSE tool discovery
        # - Connect to MCP endpoint from settings
        # - Fetch tool list via SSE stream
        # - Convert to LangChain StructuredTool format
        if not self.settings.enabled:
            return []
        # Return stubs or connect to real MCP server
        return []

