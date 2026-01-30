from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.security import RateLimitMiddleware


@pytest.mark.asyncio
async def test_spoof_ignored_when_proxy_trust_disabled():
    """
    Verify that X-Forwarded-For is IGNORED when trust_proxy_headers is False.
    This ensures IP spoofing is prevented in direct deployments.
    """
    app = AsyncMock()
    # trust_proxy_headers=False (default)
    mw = RateLimitMiddleware(app, limit=10, window=60, protected_paths=["/api"], trust_proxy_headers=False)

    req = MagicMock()
    req.url.path = "/api/test"
    req.client.host = "127.0.0.1" # Real connection IP

    def get_header(key, default=None):
        if key == "X-Forwarded-For":
            return "1.2.3.4" # Spoofed IP
        return default

    req.headers.get.side_effect = get_header

    async def call_next(request):
        return "success"

    await mw.dispatch(req, call_next)

    # Check internal state: Should use REAL IP ("127.0.0.1"), NOT spoofed ("1.2.3.4")
    assert "1.2.3.4" not in mw.requests
    assert "127.0.0.1" in mw.requests


@pytest.mark.asyncio
async def test_spoof_accepted_when_proxy_trust_enabled():
    """
    Verify that X-Forwarded-For is RESPECTED when trust_proxy_headers is True.
    This ensures functionality for valid proxy deployments (e.g. Render, AWS).
    """
    app = AsyncMock()
    # trust_proxy_headers=True
    mw = RateLimitMiddleware(app, limit=10, window=60, protected_paths=["/api"], trust_proxy_headers=True)

    req = MagicMock()
    req.url.path = "/api/test"
    req.client.host = "127.0.0.1" # LB IP

    def get_header(key, default=None):
        if key == "X-Forwarded-For":
            return "1.2.3.4" # Client IP (forwarded by proxy)
        return default

    req.headers.get.side_effect = get_header

    async def call_next(request):
        return "success"

    await mw.dispatch(req, call_next)

    # Check internal state: Should use FORWARDED IP ("1.2.3.4")
    assert "1.2.3.4" in mw.requests
    assert "127.0.0.1" not in mw.requests
