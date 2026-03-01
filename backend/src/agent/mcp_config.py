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
    """
    Load MCP configuration from environment variables into an MCPSettings instance.
    
    Reads these environment variables and maps them to MCPSettings fields:
    - MCP_ENABLED: case-insensitive; set to `True` only if the value equals "true".
    - MCP_ENDPOINT: optional string used as the MCP endpoint.
    - MCP_API_KEY: optional string used as the MCP API key.
    - MCP_TIMEOUT: parsed as an integer; falls back to 30 if missing or not an integer.
    - MCP_TOOL_WHITELIST: comma-separated list; entries are trimmed, empty entries removed, and stored as a tuple.
    
    Returns:
        MCPSettings: An MCPSettings instance populated from the environment values.
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
        tool_whitelist=whitelist,
    )


def validate(settings: MCPSettings) -> None:
    """
    Validate MCPSettings for required configuration.
    
    Parameters:
        settings (MCPSettings): MCP configuration to validate.
    
    Raises:
        ValueError: If `settings.enabled` is True and `settings.endpoint` is empty or None.
    """
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
        """
        Create a connection manager configured with MCP settings.
        
        If `settings` is None, configuration is loaded from environment variables and used.
        Parameters:
            settings (MCPSettings | None): MCP configuration to use for this manager; pass None to load configuration from the environment.
        """
        self.settings = settings or load_mcp_settings()
        self.clients = []

    def get_persistence_tools(self) -> List:
        """
        Provide persistence StructuredTool instances for loading and saving thread plans.
        
        Returns:
            List[StructuredTool]: Two StructuredTool objects:
                - The first loads a thread's plan and artifacts from the local filesystem.
                - The second saves a thread's plan and artifacts to the local filesystem.
        """
        from langchain_core.tools import StructuredTool

        from agent.mcp_persistence import load_thread_plan, save_thread_plan

        return [
            StructuredTool.from_function(
                func=load_thread_plan,
                name="load_thread_plan",
                description="Loads the plan and artifacts for a specific thread from the local file system.",
            ),
            StructuredTool.from_function(
                func=save_thread_plan,
                name="save_thread_plan",
                description="Saves the plan and artifacts for a specific thread to the local file system.",
            ),
        ]

    async def get_tools(self):
        # TODO(priority=High, complexity=Medium): [MCP:6] Implement actual SSE tool discovery
        # - Connect to MCP endpoint from settings
        # - Fetch tool list via SSE stream
        # - Convert to LangChain StructuredTool format
        """
        Discover and return available MCP tools as LangChain StructuredTool instances.
        
        When MCP is disabled, this returns an empty list. When enabled, it yields the tools exposed by the configured MCP endpoint formatted as LangChain StructuredTool objects.
        
        Returns:
            List: A list of StructuredTool objects representing available MCP tools; an empty list if MCP is disabled or no tools are discovered.
        """
        if not self.settings.enabled:
            return []
        # Return stubs or connect to real MCP server
        return []
