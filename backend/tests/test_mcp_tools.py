import asyncio
import pytest
from unittest.mock import MagicMock, patch
from backend.src.agent.tools_and_schemas import get_tools_from_mcp
from backend.src.agent.mcp_config import MCPSettings

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

    # Mock load_mcp_tools and SSEConnection where they are defined
    with patch("langchain_mcp_adapters.tools.load_mcp_tools") as mock_load:
        with patch("langchain_mcp_adapters.sessions.SSEConnection") as mock_conn:
            # Setup mock return
            mock_load.return_value = ["tool1", "tool2"]

            tools = await get_tools_from_mcp(config)

            assert tools == ["tool1", "tool2"]

            # Verify SSEConnection called with correct params
            mock_conn.assert_called_once()
            _, kwargs = mock_conn.call_args
            assert kwargs["url"] == "http://localhost:8000/sse"
            assert kwargs["headers"] == {"Authorization": "Bearer test-key"}

            # Verify load_mcp_tools called with the connection object
            mock_load.assert_called_once()

@pytest.mark.asyncio
async def test_get_tools_from_mcp_exception():
    config = MCPSettings(enabled=True, endpoint="http://localhost:8000/sse")

    with patch("langchain_mcp_adapters.tools.load_mcp_tools") as mock_load:
        with patch("langchain_mcp_adapters.sessions.SSEConnection"):
            mock_load.side_effect = Exception("Connection failed")

            tools = await get_tools_from_mcp(config)
            assert tools == []
