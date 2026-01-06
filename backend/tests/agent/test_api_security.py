
import unittest
from unittest.mock import MagicMock, patch
import time
from fastapi import FastAPI, Response, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
import pytest

class TestAPISecurity:

    @pytest.fixture
    def app(self):
        """Create a simple FastAPI app with the middleware."""
        from agent.security import RateLimitMiddleware, SecurityHeadersMiddleware

        app = FastAPI()
        # Protect only /agent paths
        app.add_middleware(
            RateLimitMiddleware,
            limit=5,
            window=60, # Increased window to be more realistic/robust for mocking
            protected_paths=["/agent"]
        )
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/agent/test")
        def agent_endpoint():
            return {"status": "ok"}

        @app.get("/public")
        def public_endpoint():
            return {"status": "ok"}

        return app

    def test_security_headers_presence(self, app):
        client = TestClient(app)
        response = client.get("/public")

        headers = response.headers
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
        assert "geolocation=()" in headers["Permissions-Policy"]
        assert "script-src 'self'" in headers["Content-Security-Policy"]

    def test_rate_limit_enforced_on_protected_path(self, app):
        client = TestClient(app)

        # Should allow 5 requests
        for _ in range(5):
            response = client.get("/agent/test")
            assert response.status_code == 200

        # 6th request should fail
        response = client.get("/agent/test")
        assert response.status_code == 429
        assert "Too Many Requests" in response.text

    def test_public_endpoint_not_limited(self, app):
        client = TestClient(app)

        # Should allow > 5 requests
        for _ in range(10):
            response = client.get("/public")
            assert response.status_code == 200

    def test_limit_resets_after_window(self, app):
        """Test that rate limit resets after the window using mocked time."""
        # Use a large window to ensure we don't accidentally expire if tests are slow,
        # since we are controlling time explicitly.
        # Note: The app fixture already sets window=60.

        client = TestClient(app)

        # We need to mock time.time in the module where RateLimitMiddleware is defined.
        # agent.security is imported inside the fixture, but the class is defined there.
        # We should patch 'agent.security.time.time'.

        # Initial time
        initial_time = 1000.0

        with patch('agent.security.time.time', return_value=initial_time) as mock_time:
            # Exhaust limit
            for _ in range(5):
                client.get("/agent/test")

            # Verify we are blocked
            response = client.get("/agent/test")
            assert response.status_code == 429

            # Advance time past the window (60s)
            mock_time.return_value = initial_time + 61.0

            # Should be allowed again
            response = client.get("/agent/test")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_memory_cleanup_preserves_active_clients(self):
        """Test that memory cleanup removes stale clients but keeps active ones."""
        from agent.security import RateLimitMiddleware
        app = FastAPI()
        mw = RateLimitMiddleware(app, limit=100, window=60, protected_paths=["/"])

        now = time.time()
        # Add 5000 stale entries (older than window=60s)
        for i in range(5000):
             mw.requests[f"stale_ip_{i}"] = [now - 100]

        # Add 5002 active entries (newer than window)
        # Note: We need total > 10000 to trigger cleanup logic
        for i in range(5002):
             mw.requests[f"active_ip_{i}"] = [now - 10]

        assert len(mw.requests) == 10002

        # Create a mock request from a NEW client
        scope = {
            'type': 'http',
            'path': '/',
            'headers': [],
            'client': ('new_client_ip', 8000),
            'method': 'GET',
            'scheme': 'http'
        }
        request = Request(scope)

        async def call_next(req):
            return Response("ok")

        await mw.dispatch(request, call_next)

        # Expected behavior:
        # 1. Cleanup runs because len > 10000.
        # 2. Stale IPs (5000) are removed.
        # 3. Active IPs (5002) are kept.
        # 4. New client IP is added.
        # Total should be 5003.

        # Assert that we kept active clients (Smart Cleanup) rather than wiping everything (Nuclear Option)
        assert len(mw.requests) > 5000, "Should NOT wipe active clients"
        assert len(mw.requests) == 5003, "Should have exactly active + new client"

        assert "stale_ip_0" not in mw.requests
        assert "active_ip_0" in mw.requests
        assert "new_client_ip" in mw.requests
