from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from starlette.responses import PlainTextResponse

from agent.app import app
from agent.security import RateLimitMiddleware

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
@patch("agent.security.TRUSTED_PROXIES", set())
@patch("agent.security.TRUSTED_PROXY_COUNT", 1)
async def test_rate_limiter_proxy_logic():
    """Unit test for RateLimitMiddleware proxy logic."""

    # Mock App
    async def mock_app(scope, receive, send):
        response = PlainTextResponse("OK")
        await response(scope, receive, send)

    # Create middleware instance with low limit (2 per minute)
    # We use a distinct path prefix to ensure we hit the logic
    # 🛡️ Sentinel: Explicitly enable trust_proxy_headers for this test as we want to test X-Forwarded-For logic
    middleware = RateLimitMiddleware(
        mock_app,
        limit=2,
        window=60,
        protected_paths=["/protected"],
        trust_proxy_headers=True,
    )

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
    # Client A (Real IP: 192.0.2.1) -> Proxy (IP: 192.0.2.100) -> App
    # Client B (Real IP: 198.51.100.1) -> Proxy (IP: 192.0.2.100) -> App

    # 1. Client A sends requests
    # The trusted proxy (Render) appends the REAL client IP to the end of X-Forwarded-For.
    # So if Client A is 192.0.2.1, the header seen by app is "..., 192.0.2.1"
    header_a = "192.0.2.1"

    await call_middleware("/protected", "192.0.2.100", header_a)
    await call_middleware("/protected", "192.0.2.100", header_a)

    # 2. Client B sends requests
    header_b = "198.51.100.1"

    await call_middleware("/protected", "192.0.2.100", header_b)

    # 3. Verify Internal State
    # We verify that the middleware tracks the IPs from X-Forwarded-For (Client A/B)
    # and ignores the direct connection IP (192.0.2.100 - the proxy).

    print(f"\nMiddleware State: {middleware.requests}")

    assert "192.0.2.1" in middleware.requests
    assert len(middleware.requests["192.0.2.1"]) == 2

    assert "198.51.100.1" in middleware.requests
    assert len(middleware.requests["198.51.100.1"]) == 1

    # "192.0.2.100" (Proxy IP) should NOT be tracked as a client
    assert "192.0.2.100" not in middleware.requests


@pytest.mark.asyncio
@patch("agent.security.TRUSTED_PROXIES", set())
@patch("agent.security.TRUSTED_PROXY_COUNT", 1)
async def test_rate_limiter_truncation():
    """Test that extremely long headers are truncated to prevent memory exhaustion."""

    async def mock_app(scope, receive, send):
        response = PlainTextResponse("OK")
        await response(scope, receive, send)

    # 🛡️ Sentinel: Enable proxy trust to test header parsing
    middleware = RateLimitMiddleware(
        mock_app,
        limit=10,
        window=60,
        protected_paths=["/protected"],
        trust_proxy_headers=True,
    )

    # Use a syntactically valid but very long IP to test truncation
    # This ensures extract_client_ip_from_forwarded doesn't reject it as invalid
    # and the middleware actually truncates it at line 334
    long_ip = "192.0.2." + "1," + "192.0.2." * 100  # Valid IP pattern, very long
    headers = [(b"x-forwarded-for", long_ip.encode())]

    scope = {
        "type": "http",
        "path": "/protected",
        "client": ("127.0.0.1", 1234),
        "headers": headers,
    }

    async def mock_send(message):
        return None  # NOSONAR

    async def mock_receive():
        return {"type": "http.request"}  # NOSONAR

    await middleware(scope, mock_receive, mock_send)

    # Verify the key in requests is truncated to 100 chars
    keys = list(middleware.requests.keys())
    assert len(keys) == 1
    # The client_ip should be extracted from X-Forwarded-For and then truncated to 100 chars
    # Verify truncation worked - key should be <= 100 chars
    assert len(keys[0]) <= 100, f"Client key {len(keys[0])} chars exceeds 100 char limit"
