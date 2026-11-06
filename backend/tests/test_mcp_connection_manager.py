from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import agent.mcp_config
from agent.mcp_config import McpConnectionManager, MCPSettings


@pytest.fixture(autouse=True)
def reset_default_manager():
    """Reset the module-level singleton between tests."""
    original_manager = getattr(agent.mcp_config, "_default_manager", None)
    agent.mcp_config._default_manager = None
    yield
    agent.mcp_config._default_manager = original_manager


def _adapters(tools=None, load=None, conn_cls=None):
    """Build the sys.modules patch for langchain_mcp_adapters.

    ``get_tools()`` imports both adapters at call time, so the patch has to be
    in place for the duration of the call rather than for the test.
    """
    tools_module = MagicMock()
    sessions_module = MagicMock()

    if conn_cls is not None:
        sessions_module.SSEConnection = conn_cls

    async def default_load(session):
        return tools

    tools_module.load_mcp_tools = load or default_load

    return {
        "langchain_mcp_adapters": MagicMock(),
        "langchain_mcp_adapters.tools": tools_module,
        "langchain_mcp_adapters.sessions": sessions_module,
    }


def _fake_connection():
    """A connection whose async enter/exit are awaitable."""
    conn = MagicMock()
    conn.__aenter__ = AsyncMock(return_value=AsyncMock())
    conn.__aexit__ = AsyncMock(return_value=None)
    return conn


@pytest.mark.asyncio
async def test_missing_endpoint():
    """A disabled configuration returns [] without constructing a connection.

    Asserting only the empty list would pass for an implementation that tries to
    connect and then swallows the failure, so the constructor is checked too.
    """
    manager = McpConnectionManager(MCPSettings(enabled=False, endpoint="http://local"))
    conn_cls = MagicMock()

    with patch.dict("sys.modules", _adapters(tools=["tool"], conn_cls=conn_cls)):
        tools = await manager.get_tools()

    assert tools == []
    conn_cls.assert_not_called()
    assert manager._pool == {}


@pytest.mark.asyncio
async def test_success_and_pooling():
    """Tools are returned as loaded, and a repeat call reuses the same list."""
    settings = MCPSettings(
        enabled=True, endpoint="https://mcp.example.com/sse", api_key="secret"
    )
    manager = McpConnectionManager(settings)
    conn = _fake_connection()
    conn_cls = MagicMock(return_value=conn)

    with patch.dict(
        "sys.modules", _adapters(tools=["tool1", "tool2"], conn_cls=conn_cls)
    ):
        tools1 = await manager.get_tools()
        assert tools1 == ["tool1", "tool2"]
        conn_cls.assert_called_once()

        tools2 = await manager.get_tools()
        assert tools1 is tools2
        conn_cls.assert_called_once()


@pytest.mark.asyncio
async def test_isolation():
    """Two endpoints get two sessions; each is then cached."""
    manager = McpConnectionManager()
    settings_1 = MCPSettings(enabled=True, endpoint="http://e1")
    settings_2 = MCPSettings(enabled=True, endpoint="http://e2")
    ctor = MagicMock(side_effect=lambda **kw: _fake_connection())

    with patch.dict("sys.modules", _adapters(tools=["tool"], conn_cls=ctor)):
        await manager.get_tools(settings_1)
        assert ctor.call_count == 1

        await manager.get_tools(settings_2)
        assert ctor.call_count == 2

        await manager.get_tools(settings_1)
        assert ctor.call_count == 2


@pytest.mark.asyncio
async def test_connection_failure_propagates_and_pool_stays_empty():
    """A failing connection raises instead of reporting "no tools", and retries."""
    manager = McpConnectionManager(MCPSettings(enabled=True, endpoint="http://local"))

    calls = 0

    def side_effect(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ValueError("Connection failed")
        return _fake_connection()

    ctor = MagicMock(side_effect=side_effect)

    with patch.dict("sys.modules", _adapters(tools=["tool"], conn_cls=ctor)):
        with pytest.raises(ValueError, match="Connection failed"):
            await manager.get_tools()
        assert manager._pool == {}

        assert await manager.get_tools() == ["tool"]
        assert len(manager._pool) == 1


@pytest.mark.asyncio
async def test_discovery_failure_closes_the_connection():
    """A failure after __aenter__ must not leak the SSE connection.

    The entry never reaches the pool, so close_all() cannot reach it: the error
    path has to close it itself, and then propagate.
    """
    from unittest.mock import patch

    manager = McpConnectionManager(MCPSettings(enabled=True, endpoint="http://local"))
    conn = _fake_connection()

    async def failing_load(session):
        raise RuntimeError("discovery blew up")

    with patch.dict(
        "sys.modules", _adapters(load=failing_load, conn_cls=lambda **kw: conn)
    ):
        with pytest.raises(RuntimeError, match="discovery blew up"):
            await manager.get_tools()

    conn.__aexit__.assert_awaited_once()
    assert manager._pool == {}


@pytest.mark.asyncio
async def test_api_key_refused_over_plaintext():
    """A bearer token must not cross a non-HTTPS, non-loopback endpoint."""
    manager = McpConnectionManager(
        MCPSettings(enabled=True, endpoint="http://mcp.example.com/sse", api_key="k")
    )
    ctor = MagicMock()

    with patch.dict("sys.modules", _adapters(tools=["tool"], conn_cls=ctor)):
        with pytest.raises(ValueError, match="non-HTTPS"):
            await manager.get_tools()

    ctor.assert_not_called()


@pytest.mark.asyncio
async def test_api_key_allowed_over_loopback_plaintext():
    """Plaintext on loopback never leaves the host, so it is permitted."""
    manager = McpConnectionManager(
        MCPSettings(enabled=True, endpoint="http://127.0.0.1:8000/sse", api_key="k")
    )
    ctor = MagicMock(return_value=_fake_connection())

    with patch.dict("sys.modules", _adapters(tools=["tool"], conn_cls=ctor)):
        assert await manager.get_tools() == ["tool"]

    ctor.assert_called_once()


@pytest.mark.asyncio
async def test_whitelist_filters_tools_and_scopes_the_cache():
    """A non-empty whitelist is an allowlist, and is part of the pool key."""
    manager = McpConnectionManager(
        MCPSettings(enabled=True, endpoint="http://local", tool_whitelist=("keep",))
    )

    def make_tool(name):
        tool = MagicMock()
        tool.name = name
        return tool

    discovered = [make_tool("keep"), make_tool("drop")]
    ctor = MagicMock(return_value=_fake_connection())

    with patch.dict("sys.modules", _adapters(tools=discovered, conn_cls=ctor)):
        allowed = await manager.get_tools()
        assert [t.name for t in allowed] == ["keep"]

        # A different allowlist must not reuse the filtered list.
        unrestricted = MCPSettings(enabled=True, endpoint="http://local")
        assert await manager.get_tools(unrestricted) == discovered
        assert ctor.call_count == 2


@pytest.mark.asyncio
async def test_close_all():
    """close_all awaits __aexit__ once per pooled session and is idempotent."""
    manager = McpConnectionManager(MCPSettings(enabled=True, endpoint="http://local"))
    conn = _fake_connection()

    with patch.dict(
        "sys.modules", _adapters(tools=["tool"], conn_cls=lambda **kw: conn)
    ):
        await manager.get_tools()
        assert len(manager._pool) == 1

        await manager.close_all()
        assert manager._pool == {}
        conn.__aexit__.assert_awaited_once()

        await manager.close_all()
        conn.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_all_keeps_entries_that_fail_to_close():
    """A connection that fails to close stays pooled so cleanup can be retried."""
    manager = McpConnectionManager(MCPSettings(enabled=True, endpoint="http://local"))

    failing = _fake_connection()
    failing.__aexit__.side_effect = OSError("close failed")

    with patch.dict(
        "sys.modules", _adapters(tools=["tool"], conn_cls=lambda **kw: failing)
    ):
        await manager.get_tools()

        await manager.close_all()
        assert len(manager._pool) == 1
        assert failing.__aexit__.await_count == 1

        # The retry reaches it again.
        assert await manager.get_tools() == ["tool"]
        assert failing.__aexit__.await_count == 1


@pytest.mark.asyncio
async def test_close_all_does_not_clear_an_entry_added_during_teardown():
    """The pool is emptied before the first await, so a racing add survives."""
    manager = McpConnectionManager(MCPSettings(enabled=True, endpoint="http://local"))
    conn = _fake_connection()

    async def add_then_close(exc_type, exc, tb):
        # Simulates get_tools() winning the race while close_all is awaiting.
        manager._pool[("raced", None, ())] = {"conn": None, "session": None}
        return None

    conn.__aexit__.side_effect = add_then_close

    with patch.dict(
        "sys.modules", _adapters(tools=["tool"], conn_cls=lambda **kw: conn)
    ):
        await manager.get_tools()
        await manager.close_all()

    assert list(manager._pool) == [("raced", None, ())]


@pytest.mark.asyncio
async def test_delegation():
    """get_tools_from_mcp(settings) delegates to McpConnectionManager.get_tools."""
    from agent.tools_and_schemas import get_tools_from_mcp

    settings = MCPSettings(enabled=True, endpoint="http://local")

    with patch("agent.tools_and_schemas.get_default_manager") as mock_get_manager:
        mock_manager = MagicMock()
        mock_manager.get_tools = AsyncMock(return_value=["tools"])
        mock_get_manager.return_value = mock_manager

        res = await get_tools_from_mcp(settings)
        assert res == ["tools"]
        mock_manager.get_tools.assert_called_once_with(settings)
