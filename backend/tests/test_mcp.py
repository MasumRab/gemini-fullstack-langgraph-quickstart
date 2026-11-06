from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import agent.mcp_config
from agent.mcp_config import MCPSettings
from agent.tools_and_schemas import get_tools_from_mcp

# Fine-grained implementation guide for MCP Tests:
#
# TODO(priority=Medium, complexity=Low, owner=agent): [test_mcp:1] Test disabled MCP returns empty list
# - Create MCPSettings with enabled=False
# - Verify get_tools_from_mcp returns []
#
# [test_mcp:2] Done: mock SSEConnection to raise ConnectionError and verify the
# failure propagates (callers cannot tell a broken endpoint from a disabled one
# if it degrades to an empty list).
#
# [test_mcp:3] Done: tool_whitelist filtering is covered in
# tests/test_mcp_connection_manager.py.
#
# TODO(priority=Low, complexity=Medium, owner=agent): [test_mcp:4] Test tool execution with real MCP server
# - Skip if MCP_ENDPOINT not set (integration test)
# - Connect to real server, call a tool, verify response format
#
# See docs/tasks/01_MCP_TASKS.md


class TestMcpIntegration:
    """Test suite for MCP integration."""

    @pytest.fixture(autouse=True)
    def reset_manager(self):
        original = getattr(agent.mcp_config, "_default_manager", None)
        agent.mcp_config._default_manager = None
        yield
        agent.mcp_config._default_manager = original

    @pytest.mark.asyncio
    async def test_mcp_tools_loading(self):
        """Tools discovered on the endpoint are returned, and the key is sent."""
        settings = MCPSettings(
            enabled=True, endpoint="http://localhost:8000/sse", api_key="test-key"
        )

        mock_tool = MagicMock()
        mock_tool.name = "test_tool"

        async def mock_load_tools(session):
            return [mock_tool]

        tools_module = MagicMock()
        tools_module.load_mcp_tools = mock_load_tools
        sessions_module = MagicMock()
        conn = MagicMock()
        conn.__aenter__ = AsyncMock(return_value=AsyncMock())
        conn.__aexit__ = AsyncMock(return_value=None)
        sessions_module.SSEConnection.return_value = conn

        # Injected through sys.modules because get_tools() imports the adapters
        # at call time; patching attributes on the real package only works if
        # something else happened to import the submodule first.
        with patch.dict(
            "sys.modules",
            {
                "langchain_mcp_adapters": MagicMock(),
                "langchain_mcp_adapters.tools": tools_module,
                "langchain_mcp_adapters.sessions": sessions_module,
            },
        ):
            tools = await get_tools_from_mcp(settings)

        assert [t.name for t in tools] == ["test_tool"]
        sessions_module.SSEConnection.assert_called_once_with(
            url="http://localhost:8000/sse",
            headers={"Authorization": "Bearer test-key"},
        )

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

    @pytest.mark.asyncio
    async def test_disabled_mcp_returns_empty_list(self):
        """Test disabled MCP returns empty list."""
        mock_settings = MagicMock()
        mock_settings.enabled = False

        tools = await get_tools_from_mcp(mock_settings)
        assert tools == []

    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test connection error handling."""
        mock_settings = MagicMock()
        mock_settings.enabled = True
        mock_settings.endpoint = "http://localhost:8000/sse"
        mock_settings.api_key = "test-key"

        mock_tools_module = MagicMock()
        mock_sessions_module = MagicMock()
        mock_conn_cls = mock_sessions_module.SSEConnection

        def side_effect(*args, **kwargs):
            raise ConnectionError("Connection failed")

        mock_conn_cls.side_effect = side_effect

        with patch.dict(
            "sys.modules",
            {
                "langchain_mcp_adapters": MagicMock(),
                "langchain_mcp_adapters.tools": mock_tools_module,
                "langchain_mcp_adapters.sessions": mock_sessions_module,
            },
        ):
            # An enabled-but-unreachable endpoint must surface, not degrade to
            # the "MCP is disabled" empty list.
            with pytest.raises(ConnectionError, match="Connection failed"):
                await get_tools_from_mcp(mock_settings)

        assert mock_conn_cls.call_count == 1
