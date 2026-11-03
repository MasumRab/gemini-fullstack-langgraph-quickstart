import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


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
        tool_whitelist=whitelist,
    )


def validate(settings: MCPSettings) -> None:
    """Validates the MCP settings."""
    if settings.enabled and not settings.endpoint:
        raise ValueError("MCP enabled but MCP_ENDPOINT missing")


class McpConnectionManager:
    def __init__(self, settings: MCPSettings | None = None):
        self.settings = settings or load_mcp_settings()
        self._pool: Dict[Tuple[str, str | None], Dict[str, Any]] = {}

    def get_persistence_tools(self) -> List:
        """Returns persistence tools wrapped for LangChain."""
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

    async def get_tools(self, config: MCPSettings | None = None) -> List[Any]:
        config = config or self.settings
        if not config or not config.enabled or not config.endpoint:
            return []

        key = (config.endpoint, config.api_key)
        if key in self._pool:
            return self._pool[key]["tools"]

        try:
            from langchain_mcp_adapters.sessions import SSEConnection
            from langchain_mcp_adapters.tools import load_mcp_tools

            conn_kwargs = {"url": config.endpoint}
            if config.api_key:
                conn_kwargs["headers"] = {"Authorization": f"Bearer {config.api_key}"}

            conn = SSEConnection(**conn_kwargs)
            session = await conn.__aenter__()
            tools = await load_mcp_tools(session)

            self._pool[key] = {"conn": conn, "session": session, "tools": tools}
            return tools
        except (ImportError, Exception) as e:
            logger.error(f"Error loading MCP tools for {config.endpoint}: {e}")
            self._pool.pop(key, None)
            return []

    async def close_all(self) -> None:
        for key, entry in list(self._pool.items()):
            conn = entry.get("conn")
            if conn:
                try:
                    await conn.__aexit__(None, None, None)
                except Exception as e:
                    logger.warning(f"Error closing MCP connection for {key[0]}: {e}")
        self._pool.clear()


_default_manager = None


def get_default_manager() -> McpConnectionManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = McpConnectionManager()
    return _default_manager
