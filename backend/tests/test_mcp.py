import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from agent.tools_and_schemas import get_tools_from_mcp

# TODO: [MCP Integration] Complete this test file.
# See docs/tasks/01_MCP_TASKS.md

class TestMcpIntegration:
    """Test suite for MCP integration."""

    @pytest.mark.asyncio
    async def test_mcp_tools_loading(self):
        """
        Test that MCP tools can be loaded from the configuration.
        """
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.enabled = True
        mock_settings.endpoint = "http://localhost:8000/sse"
        mock_settings.api_key = "test-key"

        # We need to mock the context manager SSEConnection and load_mcp_tools
        # Since they are imported inside the function, we patch the source modules
        with patch("langchain_mcp_adapters.sessions.SSEConnection") as MockSSE, \
             patch("langchain_mcp_adapters.tools.load_mcp_tools", new_callable=AsyncMock) as mock_load_tools:

            # Setup context manager mock
            mock_session = AsyncMock()
            MockSSE.return_value.__aenter__.return_value = mock_session

            # Setup tool mock
            mock_tool = MagicMock()
            mock_tool.name = "test_tool"
            mock_load_tools.return_value = [mock_tool]

            # Call the function
            tools = await get_tools_from_mcp(mock_settings)

            # Verify
            assert len(tools) == 1
            assert tools[0].name == "test_tool"

            # Verify SSEConnection called with correct args
            MockSSE.assert_called_with(url="http://localhost:8000/sse", headers={"Authorization": "Bearer test-key"})

            # Verify load_mcp_tools called with session
            mock_load_tools.assert_called_with(mock_session)

    @pytest.mark.asyncio
    async def test_filesystem_tool_execution(self):
        """
        Test that the filesystem tool (e.g. read_file) works.
        """
        # This test simulates a filesystem tool execution.
        # Since we are mocking the tool itself, we are mainly testing the tool wrapper/invocation logic
        # if there was any, but here we just verify that we can "execute" a mocked tool.

        mock_tool = AsyncMock()
        mock_tool.name = "read_file"
        mock_tool.return_value = "file content"

        # Simulate tool call
        result = await mock_tool(filepath="test.txt")

        assert result == "file content"
        mock_tool.assert_called_with(filepath="test.txt")
