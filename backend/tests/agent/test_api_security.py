import time
from unittest.mock import patch

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient


class TestAPISecurity:
    @pytest.fixture
    def app(self):
        """Create a simple FastAPI app with the middleware."""
        from agent.security import RateLimitMiddleware, SecurityHeadersMiddleware

        app = FastAPI()
        # Protect only /agent paths
        app.add_middleware(
            RateLimitMiddleware, limit=5, window=1, protected_paths=["/agent"]
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
        assert (
            headers["Strict-Transport-Security"]
            == "max-age=31536000; includeSubDomains"
        )
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
        # We need to patch time.time logic so it is consistent.
        # Patching agent.security.time.time ensures that RateLimitMiddleware uses our mock time.
        with patch("agent.security.time.time") as mock_time:
            # Start at a fixed time
            mock_time.return_value = 1000.0

            client = TestClient(app)

            # Exhaust limit
            for _ in range(5):
                client.get("/agent/test")

            # The 6th request (blocked)
            response = client.get("/agent/test")
            assert response.status_code == 429

            # Advance time beyond the window (window=1)
            mock_time.return_value = 1000.0 + 1.1

            # Should be allowed again
            response = client.get("/agent/test")
            assert response.status_code == 200

    def test_rate_limit_respects_x_forwarded_for(self, app):
        """Test that rate limiting uses the X-Forwarded-For header when present."""
        client = TestClient(app)

        # Simulate 5 requests from IP A (via proxy)
        headers_a = {"X-Forwarded-For": "10.0.0.1, 10.0.0.2"}
        for _ in range(5):
            response = client.get("/agent/test", headers=headers_a)
            assert response.status_code == 200

        # 6th request from IP A should be blocked
        response = client.get("/agent/test", headers=headers_a)
        assert response.status_code == 429

        # Requests from IP B should still be allowed (distinct from IP A)
        # Even if they come from the same "client host" (mock client doesn't change)
        headers_b = {"X-Forwarded-For": "10.0.0.3"}
        response = client.get("/agent/test", headers=headers_b)
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
            "type": "http",
            "path": "/",
            "headers": [],
            "client": ("new_client_ip", 8000),
            "method": "GET",
            "scheme": "http",
        }
        request = Request(scope)

        async def call_next(req):
            return Response("ok")

        # 🛡️ Sentinel: Manually reset last_cleanup to ensure logic triggers
        mw.last_cleanup = 0

        await mw.dispatch(request, call_next)

        # Expected behavior:
        # 1. Cleanup runs because len > 10000 AND last_cleanup is old.
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

    @pytest.mark.asyncio
    async def test_memory_cleanup_throttled(self):
        """Test that cleanup DOES NOT run if called too frequently."""
        from agent.security import RateLimitMiddleware

        app = FastAPI()
        mw = RateLimitMiddleware(app, limit=100, window=60, protected_paths=["/"])

        now = time.time()
        # Add 10001 stale entries (older than window=60s)
        for i in range(10001):
            mw.requests[f"stale_ip_{i}"] = [now - 100]

        # Set last_cleanup to NOW (simulating it just ran)
        mw.last_cleanup = now

        scope = {
            "type": "http",
            "path": "/",
            "headers": [],
            "client": ("new_client_ip", 8000),
            "method": "GET",
            "scheme": "http",
        }
        request = Request(scope)

        async def call_next(req):
            return Response("ok")

        # Dispatch should SKIP cleanup
        await mw.dispatch(request, call_next)

        # Should still be full (minus manual edits if any) + 1 new client
        # Wait, if it skips cleanup, it checks fallback:
        # if len > 10000: if new client: remove and 503.
        # So it should be 10001 (original) and request Rejected.

        # But wait, logic is:
        # 1. Add current_requests.append(now)
        # 2. Check len(active) > limit (no, new client has 1)
        # 3. Check len(self.requests) > 10000 (Yes, 10001+1=10002)
        # 4. Check throttle (Skipped because recently cleaned)
        # 5. Fallback: len > 10000 check.
        #    if len(active_requests) == 1: pop and 503.

        # So "new_client_ip" is removed. Size remains 10001.
        assert len(mw.requests) == 10001
        assert "stale_ip_0" in mw.requests  # Was NOT cleaned

        # Now reset last_cleanup to 0 and try again
        mw.last_cleanup = 0

        # Dispatch should RUN cleanup
        await mw.dispatch(request, call_next)

        # Should be cleaned: 10001 stale removed. 1 new added.
        assert len(mw.requests) == 1
        assert "new_client_ip" in mw.requests
