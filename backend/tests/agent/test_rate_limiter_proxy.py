import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from agent.app import app
from agent.security import RateLimitMiddleware
from starlette.responses import PlainTextResponse

# ----------------------------------------------------------------------
# 1. Integration Test with FastAPI App
# ----------------------------------------------------------------------
# This confirms the middleware doesn't crash the app and basics work.

client = TestClient(app, base_url="http://localhost")

def test_rate_limiter_integration():
    """Test that the app still works with the modified middleware."""
    response = client.get("/health")
    assert response.status_code == 200

# ----------------------------------------------------------------------
# 2. Unit Test for RateLimitMiddleware Logic (Proxy Support)
# ----------------------------------------------------------------------
# We verify that X-Forwarded-For is correctly used to identify clients.

@pytest.mark.asyncio
async def test_rate_limiter_proxy_logic():
    """Unit test for RateLimitMiddleware proxy logic."""

    # Mock App
    async def mock_app(scope, receive, send):
        response = PlainTextResponse("OK")
        await response(scope, receive, send)

    # Create middleware instance with low limit (2 per minute)
    # We use a distinct path prefix to ensure we hit the logic
    middleware = RateLimitMiddleware(mock_app, limit=2, window=60, protected_paths=["/protected"])

    # Helper to simulate request
    async def call_middleware(path, client_host, x_forwarded_for=None):
        headers = [(b"host", b"localhost")]
        if x_forwarded_for:
            headers.append((b"x-forwarded-for", x_forwarded_for.encode()))

        scope = {
            "type": "http",
            "path": path,
            "client": (client_host, 1234),
            "headers": headers,
        }

        sent_messages = []
        async def mock_send(message):
            sent_messages.append(message)

        async def mock_receive():
            return {"type": "http.request"}

        await middleware(scope, mock_receive, mock_send)
        return sent_messages

    # Scenario:
    # Client A (Real IP: 1.2.3.4) -> Proxy (Trusted LB) -> App
    # The Trusted LB appends the real client IP to the end of X-Forwarded-For.
    # The Middleware selects the LAST IP in the list to prevent spoofing.

    # 1. Client A sends requests
    # Header: "spoofed_ip, 1.2.3.4" (Client sends "spoofed_ip", Trusted LB appends "1.2.3.4")
    header_a = "spoofed_ip, 1.2.3.4"

    # We simulate the request coming from the Proxy IP (10.0.0.1) as the direct peer
    await call_middleware("/protected", "10.0.0.1", header_a)
    await call_middleware("/protected", "10.0.0.1", header_a)

    # 2. Client B sends requests
    # Header: "spoofed_ip, 5.6.7.8"
    header_b = "spoofed_ip, 5.6.7.8"

    await call_middleware("/protected", "10.0.0.1", header_b)

    # 3. Verify Internal State
    # middleware.requests should track "1.2.3.4" (2 requests) and "5.6.7.8" (1 request).

    print(f"\nMiddleware State: {middleware.requests}")

    assert "1.2.3.4" in middleware.requests
    assert len(middleware.requests["1.2.3.4"]) == 2

    assert "5.6.7.8" in middleware.requests
    assert len(middleware.requests["5.6.7.8"]) == 1

    # "10.0.0.1" (Proxy IP) should NOT be tracked as a client
    # nor should "spoofed_ip"
    assert "10.0.0.1" not in middleware.requests
    assert "spoofed_ip" not in middleware.requests

@pytest.mark.asyncio
async def test_rate_limiter_truncation():
    """Test that extremely long headers are truncated to prevent memory exhaustion."""

    async def mock_app(scope, receive, send):
        response = PlainTextResponse("OK")
        await response(scope, receive, send)

    middleware = RateLimitMiddleware(mock_app, limit=10, window=60, protected_paths=["/protected"])

    long_ip = "1.2.3.4" + "a" * 1000 # Very long string
    headers = [(b"x-forwarded-for", long_ip.encode())]

    scope = {
        "type": "http",
        "path": "/protected",
        "client": ("127.0.0.1", 1234),
        "headers": headers,
    }

    async def mock_send(message): pass
    async def mock_receive(): return {"type": "http.request"}

    await middleware(scope, mock_receive, mock_send)

    # Verify the key in requests is truncated
    keys = list(middleware.requests.keys())
    assert len(keys) == 1
    assert len(keys[0]) <= 100
    assert keys[0] == long_ip[:100]
