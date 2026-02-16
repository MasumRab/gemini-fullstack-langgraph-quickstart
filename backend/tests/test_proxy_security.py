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
        mock_app, limit=10, window=60, protected_paths=["/protected"], trust_proxy_headers=False
    )

    # Simulate request with spoofed header
    # Real IP: 1.2.3.4
    # Spoofed Header: 5.6.7.8
    headers = [
        (b"host", b"localhost"),
        (b"x-forwarded-for", b"5.6.7.8")
    ]

    scope = {
        "type": "http",
        "path": "/protected",
        "client": ("1.2.3.4", 1234),
        "headers": headers,
    }

    async def mock_send(message): pass
    async def mock_receive(): return {"type": "http.request"}

    await middleware(scope, mock_receive, mock_send)

    # Expectation: The request should be tracked under the Real IP (1.2.3.4), NOT the spoofed one
    assert "1.2.3.4" in middleware.requests
    assert "5.6.7.8" not in middleware.requests

@pytest.mark.asyncio
async def test_proxy_security_trusted_enabled():
    """Verify that when enabled, X-Forwarded-For IS used."""

    # Mock App
    async def mock_app(scope, receive, send):
        response = PlainTextResponse("OK")
        await response(scope, receive, send)

    # Initialize middleware with trust_proxy_headers=True
    middleware = RateLimitMiddleware(
        mock_app, limit=10, window=60, protected_paths=["/protected"], trust_proxy_headers=True
    )

    # Simulate request
    # Real IP: 10.0.0.1 (Proxy)
    # Header: 5.6.7.8 (Client)
    headers = [
        (b"host", b"localhost"),
        (b"x-forwarded-for", b"5.6.7.8")
    ]

    scope = {
        "type": "http",
        "path": "/protected",
        "client": ("10.0.0.1", 1234),
        "headers": headers,
    }

    async def mock_send(message): pass
    async def mock_receive(): return {"type": "http.request"}

    await middleware(scope, mock_receive, mock_send)

    # Expectation: The request should be tracked under the Client IP (5.6.7.8)
    assert "5.6.7.8" in middleware.requests
    assert "10.0.0.1" not in middleware.requests
