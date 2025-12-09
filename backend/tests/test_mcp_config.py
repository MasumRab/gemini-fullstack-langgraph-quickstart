import os
import unittest
from unittest import mock
from agent.mcp_config import load_mcp_settings, validate, MCPSettings

class TestMCPSettings(unittest.TestCase):
    def test_default_settings(self):
        """Test that default settings are disabled."""
        # Ensure env is clear for this test
        with mock.patch.dict(os.environ, {}, clear=True):
            settings = load_mcp_settings()
            self.assertFalse(settings.enabled)
            self.assertEqual(settings.timeout_seconds, 30)
            self.assertEqual(settings.tool_whitelist, ())

    def test_enable_settings(self):
        """Test enabling via env var."""
        env = {
            "MCP_ENABLED": "true",
            "MCP_ENDPOINT": "http://localhost:8080",
            "MCP_TIMEOUT": "60",
            "MCP_TOOL_WHITELIST": "read_file,write_file"
        }
        with mock.patch.dict(os.environ, env):
            settings = load_mcp_settings()
            self.assertTrue(settings.enabled)
            self.assertEqual(settings.endpoint, "http://localhost:8080")
            self.assertEqual(settings.timeout_seconds, 60)
            self.assertEqual(settings.tool_whitelist, ("read_file", "write_file"))

    def test_validation_error(self):
        """Test that validation fails if enabled but no endpoint."""
        settings = MCPSettings(enabled=True, endpoint=None)
        with self.assertRaises(ValueError):
            validate(settings)

    def test_validation_success(self):
        """Test that validation passes if enabled and endpoint present."""
        settings = MCPSettings(enabled=True, endpoint="http://local")

    def test_invalid_timeout_defaults_to_30(self):
        """Test that invalid timeout values default to 30."""
        env = {
            "MCP_ENABLED": "true",
            "MCP_ENDPOINT": "http://localhost:8080",
            "MCP_TIMEOUT": "invalid"
        }
        with mock.patch.dict(os.environ, env):
            settings = load_mcp_settings()
            self.assertEqual(settings.timeout_seconds, 30)

    def test_whitelist_parsing_empty_string(self):
        """Test that empty whitelist string results in empty tuple."""
        env = {
            "MCP_ENABLED": "true",
            "MCP_ENDPOINT": "http://localhost:8080",
            "MCP_TOOL_WHITELIST": ""
        }
        with mock.patch.dict(os.environ, env):
            settings = load_mcp_settings()
            self.assertEqual(settings.tool_whitelist, ())

    def test_whitelist_parsing_with_spaces(self):
        """Test that whitelist properly strips spaces."""
        env = {
            "MCP_ENABLED": "true",
            "MCP_ENDPOINT": "http://localhost:8080",
            "MCP_TOOL_WHITELIST": " read_file , write_file , list_dir "
        }
        with mock.patch.dict(os.environ, env):
            settings = load_mcp_settings()
            self.assertEqual(settings.tool_whitelist, ("read_file", "write_file", "list_dir"))

    def test_whitelist_single_tool(self):
        """Test whitelist with single tool."""
        env = {
            "MCP_ENABLED": "true",
            "MCP_ENDPOINT": "http://localhost:8080",
            "MCP_TOOL_WHITELIST": "read_file"
        }
        with mock.patch.dict(os.environ, env):
            settings = load_mcp_settings()
            self.assertEqual(settings.tool_whitelist, ("read_file",))

    def test_enabled_case_insensitive(self):
        """Test that MCP_ENABLED is case insensitive."""
        for value in ["True", "TRUE", "tRuE"]:
            with mock.patch.dict(os.environ, {"MCP_ENABLED": value}):
                settings = load_mcp_settings()
                self.assertTrue(settings.enabled, f"Failed for value: {value}")

    def test_disabled_case_insensitive(self):
        """Test that non-true values disable MCP."""
        for value in ["False", "FALSE", "no", "0", ""]:
            with mock.patch.dict(os.environ, {"MCP_ENABLED": value}):
                settings = load_mcp_settings()
                self.assertFalse(settings.enabled, f"Failed for value: {value}")

    def test_api_key_loaded(self):
        """Test that API key is loaded from environment."""
        env = {
            "MCP_ENABLED": "true",
            "MCP_ENDPOINT": "http://localhost:8080",
            "MCP_API_KEY": "test-api-key-12345"
        }
        with mock.patch.dict(os.environ, env):
            settings = load_mcp_settings()
            self.assertEqual(settings.api_key, "test-api-key-12345")

    def test_mcp_settings_immutable(self):
        """Test that MCPSettings is frozen (immutable)."""
        settings = MCPSettings(enabled=True, endpoint="http://test")
        with self.assertRaises(Exception):  # FrozenInstanceError or AttributeError
            settings.enabled = False

    def test_validation_passes_when_disabled(self):
        """Test that validation passes when MCP is disabled regardless of endpoint."""
        settings = MCPSettings(enabled=False, endpoint=None)
        # Should not raise
        validate(settings)

    def test_timeout_parsing_edge_cases(self):
        """Test timeout parsing with various edge cases."""
        test_cases = [
            ("0", 0),
            ("1", 1),
            ("999999", 999999),
            ("-5", -5),  # Negative values should be parsed
        ]
        for timeout_str, expected in test_cases:
            env = {
                "MCP_ENABLED": "true",
                "MCP_ENDPOINT": "http://localhost:8080",
                "MCP_TIMEOUT": timeout_str
            }
            with mock.patch.dict(os.environ, env):
                settings = load_mcp_settings()
                self.assertEqual(settings.timeout_seconds, expected, f"Failed for timeout: {timeout_str}")

    def test_mcp_connection_manager_initialization(self):
        """Test that McpConnectionManager can be initialized."""
        from agent.mcp_config import McpConnectionManager
        settings = MCPSettings(enabled=True, endpoint="http://localhost:8080")
        manager = McpConnectionManager(settings)
        self.assertEqual(manager.settings, settings)
        self.assertEqual(manager.clients, [])

    def test_mcp_connection_manager_get_tools_disabled(self):
        """Test that get_tools returns empty list when disabled."""
        import asyncio
        from agent.mcp_config import McpConnectionManager
        settings = MCPSettings(enabled=False)
        manager = McpConnectionManager(settings)
        tools = asyncio.run(manager.get_tools())
        self.assertEqual(tools, [])

    def test_mcp_connection_manager_get_tools_enabled(self):
        """Test that get_tools returns empty list (stub) when enabled."""
        import asyncio
        from agent.mcp_config import McpConnectionManager
        settings = MCPSettings(enabled=True, endpoint="http://localhost:8080")
        manager = McpConnectionManager(settings)
        tools = asyncio.run(manager.get_tools())
        self.assertEqual(tools, [])  # Currently a stub


if __name__ == "__main__":
    unittest.main()
