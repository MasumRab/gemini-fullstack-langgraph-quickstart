
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
        from agent.security import RateLimitMiddleware

        app = FastAPI()
        # Protect only /agent paths
        app.add_middleware(
            RateLimitMiddleware,
            limit=5,
            window=1,
            protected_paths=["/agent"]
        )

        @app.get("/agent/test")
        def agent_endpoint():
            return {"status": "ok"}

        @app.get("/public")
        def public_endpoint():
            return {"status": "ok"}

        return app

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

    def test_memory_cleanup_logic(self):
        """Test that dictionary is cleared if it gets too large."""
        from agent.security import RateLimitMiddleware
        app = FastAPI()
        middleware = RateLimitMiddleware(app, limit=100, window=60, protected_paths=["/"])

        # Simulate many IPs
        for i in range(10002):
            middleware.requests[f"ip_{i}"] = [time.time()]

        # Trigger dispatch to check cleanup (we need to mock request)
        async def call_next(request):
            return Response("ok")

        scope = {"type": "http", "path": "/", "headers": [], "client": ("127.0.0.1", 1234)}
        request = Request(scope)

        # We can't easily call dispatch directly because it's async and part of Starlette flow.
        # But we can verify the logic by calling a helper or just invoking the middleware logic if exposed.
        # Since logic is in dispatch, we'll rely on the implementation detail that it clears if > 10000.

        # Actually, let's construct a test that hits the endpoint
        middleware.requests.clear()
        # Fill it up
        for i in range(10001):
             middleware.requests[f"1.2.3.{i}"] = [time.time()]

        assert len(middleware.requests) > 10000

        # Now make a request
        # We need a proper app setup to run dispatch
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, limit=100, window=60, protected_paths=["/"])

        # We need to access the middleware instance to inject data
        # FastAPI wraps middleware in a way that's hard to access instance directly.
        # So we'll instantiate the class directly for unit testing logic.

        mw = RateLimitMiddleware(app, limit=100, window=60, protected_paths=["/"])
        for i in range(10001):
             mw.requests[f"1.2.3.{i}"] = [time.time()]

        assert len(mw.requests) > 10000

        # Mock request
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/"
        mock_request.client.host = "127.0.0.1"

        # Run dispatch logic? dispatch is async.
        # Let's just trust the code or run it in an async test loop?
        # Creating an async test is easier.
        pass

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
