import pytest
import logging
from fastapi import FastAPI
from fastapi.testclient import TestClient
from agent.security import RateLimitMiddleware
from agent.app import ContentSizeLimitMiddleware
from agent.mcp_server import FilesystemMCPServer
from pathlib import Path

# Setup simple app for middleware testing
def create_rate_limit_app():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, limit=1, window=60, protected_paths=["/test"])

    @app.get("/test")
    def test_route():
        return {"message": "ok"}

    return app

def create_content_size_app():
    app = FastAPI()
    app.add_middleware(ContentSizeLimitMiddleware, max_upload_size=10) # Small limit for testing

    @app.post("/upload")
    def upload_route(data: dict):
        return {"message": "uploaded"}

    return app

class TestSecurityLogging:

    def test_rate_limit_logging(self, caplog):
        """Test that rate limit violations are logged with path."""
        app = create_rate_limit_app()
        client = TestClient(app)

        # First request ok
        client.get("/test")

        # Second request blocked
        with caplog.at_level(logging.WARNING):
            client.get("/test")

        # Check logs
        assert "Rate limit exceeded" in caplog.text
        # We expect the path to be in the log now (failing initially)
        assert "/test" in caplog.text

    def test_content_size_logging(self, caplog):
        """Test that content size violations are logged."""
        app = create_content_size_app()
        client = TestClient(app)

        # Large payload
        large_data = "x" * 20

        with caplog.at_level(logging.WARNING):
            client.post("/upload", content=large_data, headers={"Content-Length": str(len(large_data))})

        # Check logs
        assert "Request entity too large" in caplog.text

    @pytest.mark.asyncio
    async def test_mcp_path_traversal_logging(self, caplog, tmp_path):
        """Test that MCP path traversal attempts are logged."""
        server = FilesystemMCPServer([str(tmp_path)])

        # Attempt traversal
        bad_path = str(tmp_path / "../outside.txt")

        with caplog.at_level(logging.WARNING):
            await server.read_file(bad_path)

        # Check logs
        assert "Path traversal attempt blocked" in caplog.text
        assert bad_path in caplog.text
