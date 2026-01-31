
import pytest
from unittest.mock import MagicMock, AsyncMock
from agent.security import RateLimitMiddleware

class MockApp:
    pass

@pytest.mark.asyncio
async def test_untrusted_proxy_ignores_header():
    """Verify that X-Forwarded-For is ignored when trust_proxy_headers is False."""
    app = AsyncMock()
    # Initialize with trust_proxy_headers=False
    mw = RateLimitMiddleware(app, limit=10, window=60, protected_paths=["/api"], trust_proxy_headers=False)

    req = MagicMock()
    req.url.path = "/api/test"
    req.client.host = "1.2.3.4" # Real IP (e.g. attacker direct connection)
    req.headers.get.return_value = "9.9.9.9" # Spoofed IP via X-Forwarded-For

    async def call_next(request):
        return "success"

    await mw.dispatch(req, call_next)

    # Check the internal requests map
    # Should use 1.2.3.4 (real IP), NOT 9.9.9.9 (spoofed header)
    assert "1.2.3.4" in mw.requests
    assert "9.9.9.9" not in mw.requests

@pytest.mark.asyncio
async def test_trusted_proxy_uses_header():
    """Verify that X-Forwarded-For is used when trust_proxy_headers is True."""
    app = AsyncMock()
    mw = RateLimitMiddleware(app, limit=10, window=60, protected_paths=["/api"], trust_proxy_headers=True)

    req = MagicMock()
    req.url.path = "/api/test"
    req.client.host = "10.0.0.1" # Internal LB IP
    # X-Forwarded-For: client, proxy1, proxy2
    # The logic traverses from end.
    req.headers.get.return_value = "5.6.7.8, 10.0.0.1"

    async def call_next(request):
        return "success"

    await mw.dispatch(req, call_next)

    # Should use 5.6.7.8 (the public client IP)
    # The current logic tries to find the first non-private IP from the right.
    # 10.0.0.1 is private. 5.6.7.8 is public.
    assert "5.6.7.8" in mw.requests
