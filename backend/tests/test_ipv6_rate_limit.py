from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.security import RateLimitMiddleware


class MockApp:
    pass


def test_get_client_key_ipv4():
    mw = RateLimitMiddleware(MockApp())
    assert mw.get_client_key("192.168.1.1") == "192.168.1.1"


def test_get_client_key_ipv6():
    mw = RateLimitMiddleware(MockApp())
    # Same subnet (first 4 groups match: 2001:db8:85a3:8d3)
    ip1 = "2001:db8:85a3:8d3:1319:8a2e:370:7348"
    ip2 = "2001:db8:85a3:8d3:1319:8a2e:370:7349"
    # Different subnet (4th group differs)
    ip3 = "2001:db8:85a3:8d4:1319:8a2e:370:7348"

    key1 = mw.get_client_key(ip1)
    key2 = mw.get_client_key(ip2)
    key3 = mw.get_client_key(ip3)

    assert key1 == key2
    assert key1.endswith("/64")
    assert key1 != key3


def test_get_client_key_invalid():
    mw = RateLimitMiddleware(MockApp())
    assert mw.get_client_key("invalid_ip") == "invalid_ip"


@pytest.mark.asyncio
async def test_ipv6_rate_limiting_shared_bucket():
    app = AsyncMock()
    # Limit 1 per window
    mw = RateLimitMiddleware(app, limit=1, window=60, protected_paths=["/api"])

    # First request
    req1 = MagicMock()
    req1.url.path = "/api/test"
    req1.client.host = "2001:db8::1"
    req1.headers.get.return_value = None  # No X-Forwarded-For

    async def call_next(request):
        return "success"

    response1 = await mw.dispatch(req1, call_next)
    assert response1 == "success"

    # Second request from DIFFERENT IP in SAME subnet (2001:db8::/64)
    # 2001:db8::1 -> 2001:0db8:0000:0000:0000:0000:0000:0001
    # 2001:db8::2 -> 2001:0db8:0000:0000:0000:0000:0000:0002
    # Both share 2001:0db8:0000:0000::/64

    req2 = MagicMock()
    req2.url.path = "/api/test"
    req2.client.host = "2001:db8::2"
    req2.headers.get.return_value = None

    response2 = await mw.dispatch(req2, call_next)

    # Should be rate limited (429 response object)
    # The response is a Starlette Response object
    assert response2.status_code == 429
    assert response2.body == b"Too Many Requests"


@pytest.mark.asyncio
async def test_ipv6_rate_limiting_different_bucket():
    app = AsyncMock()
    mw = RateLimitMiddleware(app, limit=1, window=60, protected_paths=["/api"])

    # First request
    req1 = MagicMock()
    req1.url.path = "/api/test"
    req1.client.host = "2001:db8::1"
    req1.headers.get.return_value = None

    async def call_next(request):
        return "success"

    response1 = await mw.dispatch(req1, call_next)
    assert response1 == "success"

    # Second request from DIFFERENT subnet
    # 2001:db8:0:1::1 vs 2001:db8::1
    # 2001:0db8:0000:0000 vs 2001:0db8:0000:0001

    req2 = MagicMock()
    req2.url.path = "/api/test"
    req2.client.host = "2001:db8:0:1::1"
    req2.headers.get.return_value = None

    response2 = await mw.dispatch(req2, call_next)

    assert response2 == "success"
