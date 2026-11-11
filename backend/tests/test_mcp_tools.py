from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import agent.mcp_config
from agent.mcp_config import MCPSettings
from agent.tools_and_schemas import get_tools_from_mcp


@pytest.fixture(autouse=True)
def reset_manager():
    original = getattr(agent.mcp_config, "_default_manager", None)
    agent.mcp_config._default_manager = None
    yield
    agent.mcp_config._default_manager = original


@pytest.mark.asyncio
async def test_get_tools_from_mcp_disabled():
    config = MCPSettings(enabled=False, endpoint="http://localhost:8000")
    tools = await get_tools_from_mcp(config)
    assert tools == []


@pytest.mark.asyncio
async def test_get_tools_from_mcp_no_endpoint():
    config = MCPSettings(enabled=True, endpoint=None)
    tools = await get_tools_from_mcp(config)
    assert tools == []


@pytest.mark.asyncio
async def test_get_tools_from_mcp_success():
    config = MCPSettings(
        enabled=True, endpoint="http://localhost:8000/sse", api_key="test-key"
    )

    # Create mock modules for langchain_mcp_adapters
    mock_tools_module = MagicMock()
    mock_sessions_module = MagicMock()

    # Configure the mocks
    mock_load = mock_tools_module.load_mcp_tools
    # We must use AsyncMock for awaitable functions if load_mcp_tools is awaited
    # The implementation calls: tools = await load_mcp_tools(connection=connection)
    mock_load.return_value = ["tool1", "tool2"]

    # If the real function is async, the mock should return a coroutine or be an AsyncMock.
    # MagicMock return_value is not awaited automatically unless we configure it.
    async def async_return(*args, **kwargs):
        return ["tool1", "tool2"]

    mock_load.side_effect = async_return

    mock_conn_cls = mock_sessions_module.SSEConnection

    # Patch sys.modules to inject our mocks
    with patch.dict(
        "sys.modules",
        {
            "langchain_mcp_adapters": MagicMock(),  # Root package
            "langchain_mcp_adapters.tools": mock_tools_module,
            "langchain_mcp_adapters.sessions": mock_sessions_module,
        },
    ):
        tools = await get_tools_from_mcp(config)

        assert tools == ["tool1", "tool2"]

        # Verify SSEConnection called with correct params
        mock_conn_cls.assert_called_once()
        _, kwargs = mock_conn_cls.call_args
        assert kwargs["url"] == "http://localhost:8000/sse"
        assert kwargs["headers"] == {"Authorization": "Bearer test-key"}


@pytest.mark.asyncio
async def test_get_tools_from_mcp_exception_propagates():
    """A broken enabled endpoint must not look like a disabled one.

    ``get_tools_from_mcp`` previously swallowed every error and returned [],
    which is indistinguishable from "MCP is off"; the lifespan treats that as an
    empty tool list and the agent silently runs without the tools it declared.
    The failure now reaches the caller, and the opened connection is released.
    """
    config = MCPSettings(enabled=True, endpoint="http://localhost:8000/sse")

    mock_tools_module = MagicMock()
    mock_sessions_module = MagicMock()

    async def async_raise(*args, **kwargs):
        raise RuntimeError("Connection failed")

    mock_tools_module.load_mcp_tools.side_effect = async_raise

    conn = MagicMock()
    conn.__aenter__ = AsyncMock(return_value=AsyncMock())
    conn.__aexit__ = AsyncMock(return_value=None)
    mock_sessions_module.SSEConnection.return_value = conn

    with patch.dict(
        "sys.modules",
        {
            "langchain_mcp_adapters": MagicMock(),
            "langchain_mcp_adapters.tools": mock_tools_module,
            "langchain_mcp_adapters.sessions": mock_sessions_module,
        },
    ):
        with pytest.raises(RuntimeError, match="Connection failed"):
            await get_tools_from_mcp(config)

    conn.__aexit__.assert_awaited_once()
