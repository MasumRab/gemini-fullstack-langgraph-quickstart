from unittest.mock import patch

import pytest
from starlette.responses import PlainTextResponse

from agent.security import RateLimitMiddleware


@pytest.mark.asyncio
async def test_proxy_security_default_secure():
    """Verify that by default (trust_proxy_headers=False), X-Forwarded-For is ignored."""

    # Mock App
    async def mock_app(scope, receive, send):
        response = PlainTextResponse("OK")
        await response(scope, receive, send)

    # Initialize middleware with default (trust_proxy_headers=False)
    middleware = RateLimitMiddleware(
        mock_app,
        limit=10,
        window=60,
        protected_paths=["/protected"],
        trust_proxy_headers=False,
    )

    # Simulate request with spoofed header
    # Real IP: 192.0.2.1
    # Spoofed Header: 198.51.100.1
    headers = [(b"host", b"localhost"), (b"x-forwarded-for", b"198.51.100.1")]

    scope = {
        "type": "http",
        "path": "/protected",
        "client": ("192.0.2.1", 1234),
        "headers": headers,
    }

    async def mock_send(message):
        pass

    async def mock_receive():
        return {"type": "http.request"}

    await middleware(scope, mock_receive, mock_send)

    # Expectation: The request should be tracked under the Real IP (192.0.2.1), NOT the spoofed one
    assert "192.0.2.1" in middleware.requests
    assert "198.51.100.1" not in middleware.requests


@pytest.mark.asyncio
@patch("agent.security.TRUSTED_PROXIES", set())
@patch("agent.security.TRUSTED_PROXY_COUNT", 1)
async def test_proxy_security_trusted_enabled():
    """Verify that when enabled, X-Forwarded-For IS used."""

    # Mock App
    async def mock_app(scope, receive, send):
        response = PlainTextResponse("OK")
        await response(scope, receive, send)

    # Initialize middleware with trust_proxy_headers=True
    middleware = RateLimitMiddleware(
        mock_app,
        limit=10,
        window=60,
        protected_paths=["/protected"],
        trust_proxy_headers=True,
    )

    # Simulate request
    # Real IP: 192.0.2.100 (Proxy)
    # Header: 198.51.100.1 (Client)
    headers = [(b"host", b"localhost"), (b"x-forwarded-for", b"198.51.100.1")]

    scope = {
        "type": "http",
        "path": "/protected",
        "client": ("192.0.2.100", 1234),
        "headers": headers,
    }

    async def mock_send(message):
        pass

    async def mock_receive():
        return {"type": "http.request"}

    await middleware(scope, mock_receive, mock_send)

    # Expectation: The request should be tracked under the Client IP (198.51.100.1)
    assert "198.51.100.1" in middleware.requests
    assert "192.0.2.100" not in middleware.requests


@pytest.mark.asyncio
@patch("agent.security.TRUSTED_PROXIES", set())
@patch("agent.security.TRUSTED_PROXY_COUNT", 1)
async def test_spoofing_vulnerability():
    """
    Verify that the middleware correctly identifies the client IP even if it's private,
    when it is the last IP in the trusted proxy chain.
    Prevents spoofing by injecting a public IP at the start of X-Forwarded-For.
    """

    # Mock App
    async def mock_app(scope, receive, send):
        response = PlainTextResponse("OK")
        await response(scope, receive, send)

    # Initialize middleware with trust_proxy_headers=True
    middleware = RateLimitMiddleware(
        mock_app,
        limit=10,
        window=60,
        protected_paths=["/protected"],
        trust_proxy_headers=True,
    )

    # Scenario:
    # Attacker Real IP (seen by proxy): 192.0.2.105 (Private)
    # Attacker Spoofs Header: "203.0.113.1" (Public)
    # Trusted Proxy appends Real IP.
    # Header: "203.0.113.1, 192.0.2.105"

    headers = [(b"host", b"localhost"), (b"x-forwarded-for", b"203.0.113.1, 192.0.2.105")]

    scope = {
        "type": "http",
        "path": "/protected",
        "client": ("192.0.2.100", 1234),  # Connection from Proxy
        "headers": headers,
    }

    async def mock_send(message):
        pass

    async def mock_receive():
        return {"type": "http.request"}

    await middleware(scope, mock_receive, mock_send)

    # Expectation: The request should be tracked under the Real IP (192.0.2.105)
    # If vulnerable, it would be under 203.0.113.1
    assert "192.0.2.105" in middleware.requests
    assert "203.0.113.1" not in middleware.requests
