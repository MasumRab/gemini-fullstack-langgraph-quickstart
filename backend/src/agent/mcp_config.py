from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import os

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

# TODO: [MCP Integration] Implement full McpConnectionManager with SSE support.
# Should handle connection pooling and error recovery.
class McpConnectionManager:
    def __init__(self, settings: MCPSettings):
        self.settings = settings
        self.clients = []

    async def get_tools(self):
        if not self.settings.enabled:
            return []
        # Return stubs or connect to real MCP server
        return []
