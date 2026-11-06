import ipaddress
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

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


def _is_loopback_endpoint(endpoint: str) -> bool:
    """True when an endpoint points at this machine.

    A Bearer token on loopback never leaves the host, so plaintext is no worse
    than the local process. Anywhere else it is readable by every hop.
    """
    host = urlparse(endpoint).hostname
    if not host:
        return False
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def validate(settings: MCPSettings) -> None:
    """Validates the MCP settings."""
    if settings.enabled and not settings.endpoint:
        raise ValueError("MCP enabled but MCP_ENDPOINT missing")


# Fine-grained implementation guide for MCP Integration:
#
# TODO(priority=High, complexity=Low, owner=agent): [MCP:1] Define SSE client interface
# - Create abstract base class for MCP transport
# - Define methods: connect(), disconnect(), send_message(), receive_stream()
#
# TODO(priority=High, complexity=Medium, owner=agent): [MCP:2] Implement SSE transport
# - Use httpx or aiohttp for Server-Sent Events
# - Handle reconnection with exponential backoff
# - Parse SSE event format (event:, data:, id:)
#
# TODO(priority=Medium, complexity=Medium, owner=agent): [MCP:3] Connection pooling
# - Maintain pool of persistent connections
# - Implement health checks and automatic reconnection
# - Thread-safe connection acquisition/release
#
# TODO(priority=Medium, complexity=Low, owner=agent): [MCP:4] Error recovery
# - Catch and log transport errors
# - Retry failed tool calls with backoff
# - Return graceful fallback on persistent failure
#
# TODO(priority=Low, complexity=Low, owner=agent): [MCP:5] Metrics and observability
# - Track connection latency, success/failure rates
# - Integrate with Langfuse spans
class McpConnectionManager:
    def __init__(self, settings: MCPSettings | None = None):
        self.settings = settings or load_mcp_settings()
        self._pool: Dict[Tuple[str, str | None, Tuple[str, ...]], Dict[str, Any]] = {}

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

        if config.api_key and not _is_loopback_endpoint(config.endpoint):
            parsed = urlparse(config.endpoint)
            if parsed.scheme != "https":
                raise ValueError(
                    "Refusing to send MCP_API_KEY over a non-HTTPS endpoint "
                    f"({parsed.scheme or 'no'} scheme, host {parsed.hostname}). "
                    "Use https://, or a loopback address for local development."
                )

        # The whitelist is part of the cache key: two callers on the same endpoint
        # and key but with different allowlists must not share one tool list.
        key = (config.endpoint, config.api_key, config.tool_whitelist)
        if key in self._pool:
            return self._pool[key]["tools"]

        from langchain_mcp_adapters.sessions import SSEConnection
        from langchain_mcp_adapters.tools import load_mcp_tools

        conn_kwargs: Dict[str, Any] = {"url": config.endpoint}
        if config.api_key:
            conn_kwargs["headers"] = {"Authorization": f"Bearer {config.api_key}"}

        conn = SSEConnection(**conn_kwargs)
        session = await conn.__aenter__()
        try:
            tools = await load_mcp_tools(session)
        except BaseException:
            # Discovery failed after the SSE session was opened and before the
            # entry reached the pool, so close_all() can never reach it: close it
            # here or the connection leaks on every retry.
            try:
                await conn.__aexit__(None, None, None)
            except Exception as close_error:
                # Cleanup must not mask the discovery error being re-raised.
                logger.warning(
                    f"Error closing MCP connection after failed discovery: {close_error}"
                )
            raise

        tools = self._filter_by_whitelist(tools, config.tool_whitelist)
        self._pool[key] = {"conn": conn, "session": session, "tools": tools}
        return tools

    @staticmethod
    def _filter_by_whitelist(tools: List[Any], whitelist: Tuple[str, ...]) -> List[Any]:
        """Drop tools outside the configured allowlist.

        An empty whitelist means "no restriction", which is the behaviour every
        existing deployment has. A non-empty one is an allowlist: tools it does
        not name must not reach the model.
        """
        if not whitelist:
            return tools
        allowed = set(whitelist)
        kept = [t for t in tools if getattr(t, "name", None) in allowed]
        if len(kept) != len(tools):
            logger.info(
                f"MCP tool whitelist kept {len(kept)} of {len(tools)} discovered tools"
            )
        return kept

    async def close_all(self) -> None:
        """Close every pooled connection, keeping any that fail to close.

        The pool is emptied *before* the first await so a concurrent
        ``get_tools()`` that adds an entry during teardown keeps it instead of
        having it cleared away unclosed. A connection whose ``__aexit__``
        raises is put back, so a later ``close_all()`` can retry it.
        """
        entries = list(self._pool.items())
        self._pool.clear()
        for key, entry in entries:
            conn = entry.get("conn")
            if not conn:
                continue
            try:
                await conn.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing MCP connection for {key[0]}: {e}")
                # setdefault: if get_tools() re-opened this key while we were
                # awaiting, keep the live entry rather than the dead one.
                self._pool.setdefault(key, entry)


_default_manager = None


def get_default_manager() -> McpConnectionManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = McpConnectionManager()
    return _default_manager
