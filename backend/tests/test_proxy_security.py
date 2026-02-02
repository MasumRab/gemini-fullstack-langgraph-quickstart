
import pytest
from unittest.mock import MagicMock, AsyncMock
from agent.security import RateLimitMiddleware

@pytest.mark.asyncio
async def test_x_forwarded_for_ignored_by_default():
    """
    Test that X-Forwarded-For is IGNORED by default to prevent spoofing.
    This test expects SECURE behavior (Req 2 blocked).
    """
    app = AsyncMock()
    # Limit 1 request per window, default trust_proxy_headers=False
    mw = RateLimitMiddleware(app, limit=1, window=60, protected_paths=["/api"])

    # Real Client IP
    client_ip = "1.2.3.4"

    async def call_next(request):
        return "success"

    # Request 1: Normal request
    req1 = MagicMock()
    req1.url.path = "/api/test"
    req1.client.host = client_ip
    req1.headers.get.return_value = None # No X-Forwarded-For

    response1 = await mw.dispatch(req1, call_next)
    assert response1 == "success"

    # Request 2: Attacker tries to bypass by spoofing X-Forwarded-For
    req2 = MagicMock()
    req2.url.path = "/api/test"
    req2.client.host = client_ip # Same real IP
    req2.headers.get.return_value = "10.0.0.1" # Spoofed IP

    response2 = await mw.dispatch(req2, call_next)

    # Secure behavior: The spoofed header is IGNORED.
    # So this request counts towards '1.2.3.4', which is already over limit.
    # Should return 429.

    # NOTE: The middleware returns a Response object, checking status_code
    if hasattr(response2, "status_code"):
         assert response2.status_code == 429, "Rate limit bypassed via X-Forwarded-For!"
    else:
         # If it returned "success" string (from call_next default mock), it means it passed
         pytest.fail("Rate limit bypassed! Response was success instead of 429.")

@pytest.mark.asyncio
async def test_x_forwarded_for_trusted_when_configured():
    """
    Test that X-Forwarded-For IS respected when trust_proxy_headers is True.
    This is for legitimate use cases (behind load balancer).
    """
    app = AsyncMock()
    # Limit 1 request per window, BUT we trust proxies
    mw = RateLimitMiddleware(app, limit=1, window=60, protected_paths=["/api"], trust_proxy_headers=True)

    # Real Client IP (Load Balancer IP)
    lb_ip = "10.0.0.1"

    async def call_next(request):
        return "success"

    # Request 1: Client A behind LB
    req1 = MagicMock()
    req1.url.path = "/api/test"
    req1.client.host = lb_ip
    req1.headers.get.return_value = "1.2.3.4" # Client A

    response1 = await mw.dispatch(req1, call_next)
    assert response1 == "success"

    # Request 2: Client B behind LB
    req2 = MagicMock()
    req2.url.path = "/api/test"
    req2.client.host = lb_ip # Same LB IP
    req2.headers.get.return_value = "5.6.7.8" # Client B

    response2 = await mw.dispatch(req2, call_next)

    # Since we trust the proxy header, Client B should be treated as a different user.
    # So it should PASS (success), not 429.
    assert response2 == "success"

    # Request 3: Client A again (should be blocked now)
    req3 = MagicMock()
    req3.url.path = "/api/test"
    req3.client.host = lb_ip
    req3.headers.get.return_value = "1.2.3.4" # Client A again

    response3 = await mw.dispatch(req3, call_next)
    if hasattr(response3, "status_code"):
         assert response3.status_code == 429
    else:
         pytest.fail("Client A should have been rate limited on second request.")
