import asyncio
import pytest
from unittest.mock import MagicMock, patch
from agent.tools_and_schemas import get_tools_from_mcp
from agent.mcp_config import MCPSettings

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
    config = MCPSettings(enabled=True, endpoint="http://localhost:8000/sse", api_key="test-key")

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
    with patch.dict("sys.modules", {
        "langchain_mcp_adapters": MagicMock(), # Root package
        "langchain_mcp_adapters.tools": mock_tools_module,
        "langchain_mcp_adapters.sessions": mock_sessions_module
    }):
        tools = await get_tools_from_mcp(config)

        assert tools == ["tool1", "tool2"]

        # Verify SSEConnection called with correct params
        mock_conn_cls.assert_called_once()
        _, kwargs = mock_conn_cls.call_args
        assert kwargs["url"] == "http://localhost:8000/sse"
        assert kwargs["headers"] == {"Authorization": "Bearer test-key"}

@pytest.mark.asyncio
async def test_get_tools_from_mcp_exception():
    config = MCPSettings(enabled=True, endpoint="http://localhost:8000/sse")

    mock_tools_module = MagicMock()
    mock_sessions_module = MagicMock()

    mock_load = mock_tools_module.load_mcp_tools
    async def async_raise(*args, **kwargs):
        raise Exception("Connection failed")
    mock_load.side_effect = async_raise

    with patch.dict("sys.modules", {
        "langchain_mcp_adapters": MagicMock(),
        "langchain_mcp_adapters.tools": mock_tools_module,
        "langchain_mcp_adapters.sessions": mock_sessions_module
    }):
        tools = await get_tools_from_mcp(config)
        assert tools == []
