
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
            window=1,
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
        client = TestClient(app)

        # Exhaust limit
        for _ in range(5):
            client.get("/agent/test")

        response = client.get("/agent/test")
        assert response.status_code == 429

        # Wait for window
        time.sleep(1.1)

        # Should be allowed again
        response = client.get("/agent/test")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_memory_cleanup_trigger(self):
        from agent.security import RateLimitMiddleware
        app = FastAPI()
        mw = RateLimitMiddleware(app, limit=100, window=60, protected_paths=["/"])

        # Fill with 10001 entries
        for i in range(10001):
             mw.requests[f"fake_ip_{i}"] = [time.time()]

        assert len(mw.requests) > 10000

        # Create a mock request
        scope = {
            'type': 'http',
            'path': '/',
            'headers': [],
            'client': ('127.0.0.1', 8000),
            'method': 'GET',
            'scheme': 'http'
        }
        request = Request(scope)

        async def call_next(req):
            return Response("ok")

        await mw.dispatch(request, call_next)

        # Should be cleared (or at least significantly smaller, containing just the new one)
        # Our logic is "if > 10000: clear()". Then it adds the current one.
        # So size should be 1.
        assert len(mw.requests) == 1
