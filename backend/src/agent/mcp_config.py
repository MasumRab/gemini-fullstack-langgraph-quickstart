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
    """
    Load MCP configuration from environment variables.
    
    Reads the following environment variables and converts them into an MCPSettings instance:
    - MCP_ENABLED: interpreted as enabled when equal to "true" (case-insensitive).
    - MCP_ENDPOINT: optional endpoint URL or path.
    - MCP_API_KEY: optional API key.
    - MCP_TIMEOUT: integer timeout in seconds; defaults to 30 on missing or invalid value.
    - MCP_TOOL_WHITELIST: comma-separated list; converted to a tuple of trimmed, non-empty tool names.
    
    Returns:
        MCPSettings: Configuration populated from the corresponding environment variables.
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
    Validate MCP configuration for required fields.
    
    Raises:
        ValueError: If `settings.enabled` is True and `settings.endpoint` is missing.
    
    Parameters:
        settings (MCPSettings): The MCP configuration to validate.
    """
    if settings.enabled:
        if not settings.endpoint:
            # For now, we allow missing endpoint if we are just using local stubs,
            # but usually MCP requires a server connection.
            # The prompt example said: "if settings.enabled and not settings.endpoint: raise ValueError"
            # However, if we are doing filesystem MCP, it might be a local path, usually passed as argument to a connector.
            # We will strictly follow the prompt's example logic for now.
            if not settings.endpoint:
                 raise ValueError("MCP enabled but MCP_ENDPOINT missing")

# Stub for future connection logic
class McpConnectionManager:
    def __init__(self, settings: MCPSettings):
        """
        Initialize the connection manager with MCP configuration.
        
        Parameters:
            settings (MCPSettings): Immutable MCP configuration used by the manager; stored on the instance.
        
        Notes:
            Initializes an empty list `clients` for managing connections or client objects.
        """
        self.settings = settings
        self.clients = []

    async def get_tools(self):
        """
        Retrieve the list of available MCP tools for this connection manager.
        
        Returns:
            A list of tool descriptors available from the configured MCP endpoint; an empty list when MCP is disabled or no tools are available.
        """
        if not self.settings.enabled:
            return []
        # Return stubs or connect to real MCP server
        return []