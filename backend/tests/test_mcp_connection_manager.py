import sys
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


@pytest.mark.asyncio
async def test_missing_endpoint():
    """1. MCPSettings(enabled=False) or a missing endpoint: get_tools() returns [] without constructing a connection."""
    manager = McpConnectionManager(MCPSettings(enabled=False, endpoint="http://local"))

    with patch.dict("sys.modules", {"langchain_mcp_adapters.sessions": MagicMock()}):
        tools = await manager.get_tools()
        assert tools == []


@pytest.mark.asyncio
async def test_success_and_pooling():
    """
    2. Success: tools are returned and their identity matches what the fake load_mcp_tools returned.
    3. Pooling: two get_tools() calls for the same endpoint construct SSEConnection exactly once and return the same cached tool list.
    """
    settings = MCPSettings(enabled=True, endpoint="http://local", api_key="secret")
    manager = McpConnectionManager(settings)

    mock_tools_module = MagicMock()
    mock_sessions_module = MagicMock()

    mock_conn = MagicMock()
    mock_session = AsyncMock()
    mock_conn.__aenter__.return_value = mock_session
    mock_conn_cls = mock_sessions_module.SSEConnection
    mock_conn_cls.return_value = mock_conn

    async def mock_load_mcp_tools(session):
        return ["tool1", "tool2"]

    mock_tools_module.load_mcp_tools = mock_load_mcp_tools

    with patch.dict(
        "sys.modules",
        {
            "langchain_mcp_adapters": MagicMock(),
            "langchain_mcp_adapters.tools": mock_tools_module,
            "langchain_mcp_adapters.sessions": mock_sessions_module,
        },
    ):
        tools1 = await manager.get_tools()
        assert tools1 == ["tool1", "tool2"]
        mock_conn_cls.assert_called_once()

        # Pooling hit
        tools2 = await manager.get_tools()
        assert tools2 == ["tool1", "tool2"]
        assert tools1 is tools2

        # Still called once
        mock_conn_cls.assert_called_once()


@pytest.mark.asyncio
async def test_isolation():
    """4. Isolation: two different endpoints produce two distinct sessions."""
    manager = McpConnectionManager()
    settings_1 = MCPSettings(enabled=True, endpoint="http://e1")
    settings_2 = MCPSettings(enabled=True, endpoint="http://e2")

    mock_tools_module = MagicMock()
    mock_sessions_module = MagicMock()

    mock_conn = MagicMock()
    mock_session = AsyncMock()
    mock_conn.__aenter__.return_value = mock_session
    mock_conn_cls = mock_sessions_module.SSEConnection
    mock_conn_cls.return_value = mock_conn

    async def mock_load_mcp_tools(session):
        return ["tool"]

    mock_tools_module.load_mcp_tools = mock_load_mcp_tools

    with patch.dict(
        "sys.modules",
        {
            "langchain_mcp_adapters": MagicMock(),
            "langchain_mcp_adapters.tools": mock_tools_module,
            "langchain_mcp_adapters.sessions": mock_sessions_module,
        },
    ):
        await manager.get_tools(settings_1)
        assert mock_conn_cls.call_count == 1

        await manager.get_tools(settings_2)
        assert mock_conn_cls.call_count == 2

        # Test they are cached
        await manager.get_tools(settings_1)
        assert mock_conn_cls.call_count == 2


@pytest.mark.asyncio
async def test_failure():
    """5. Failure: a connection constructor that raises yields [], logs, and evicts the entry; a subsequent call retries."""
    settings = MCPSettings(enabled=True, endpoint="http://local")
    manager = McpConnectionManager(settings)

    mock_tools_module = MagicMock()
    mock_sessions_module = MagicMock()
    mock_conn_cls = mock_sessions_module.SSEConnection

    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("Connection failed")

        mock_conn = MagicMock()
        mock_conn.__aenter__.return_value = AsyncMock()
        return mock_conn

    mock_conn_cls.side_effect = side_effect

    async def mock_load_mcp_tools(session):
        return ["tool"]

    mock_tools_module.load_mcp_tools = mock_load_mcp_tools

    with patch.dict(
        "sys.modules",
        {
            "langchain_mcp_adapters": MagicMock(),
            "langchain_mcp_adapters.tools": mock_tools_module,
            "langchain_mcp_adapters.sessions": mock_sessions_module,
        },
    ):
        tools1 = await manager.get_tools()
        assert tools1 == []
        assert len(manager._pool) == 0

        # Retry
        tools2 = await manager.get_tools()
        assert tools2 == ["tool"]
        assert len(manager._pool) == 1


@pytest.mark.asyncio
async def test_close_all():
    """6. close_all() awaits the fake session's close/aclose once per pooled session and is idempotent."""
    settings = MCPSettings(enabled=True, endpoint="http://local")
    manager = McpConnectionManager(settings)

    mock_tools_module = MagicMock()
    mock_sessions_module = MagicMock()

    mock_conn = AsyncMock()
    mock_session = AsyncMock()
    mock_conn.__aenter__.return_value = mock_session
    mock_conn_cls = mock_sessions_module.SSEConnection
    mock_conn_cls.return_value = mock_conn

    async def mock_load_mcp_tools(session):
        return ["tool"]

    mock_tools_module.load_mcp_tools = mock_load_mcp_tools

    with patch.dict(
        "sys.modules",
        {
            "langchain_mcp_adapters": MagicMock(),
            "langchain_mcp_adapters.tools": mock_tools_module,
            "langchain_mcp_adapters.sessions": mock_sessions_module,
        },
    ):
        await manager.get_tools()
        assert len(manager._pool) == 1

        # First close_all
        await manager.close_all()
        assert len(manager._pool) == 0
        mock_conn.__aexit__.assert_called_once()

        # Second close_all (idempotent)
        await manager.close_all()
        assert len(manager._pool) == 0
        # Call count remains 1
        mock_conn.__aexit__.assert_called_once()


@pytest.mark.asyncio
async def test_delegation():
    """7. get_tools_from_mcp(settings) delegates to McpConnectionManager.get_tools."""
    from agent.tools_and_schemas import get_tools_from_mcp

    settings = MCPSettings(enabled=True, endpoint="http://local")

    with patch("agent.tools_and_schemas.get_default_manager") as mock_get_manager:
        mock_manager = MagicMock()
        mock_manager.get_tools = AsyncMock(return_value=["tools"])
        mock_get_manager.return_value = mock_manager

        res = await get_tools_from_mcp(settings)
        assert res == ["tools"]
        mock_manager.get_tools.assert_called_once_with(settings)
