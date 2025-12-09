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
        validate(settings)
