import pytest
import logging
from unittest.mock import MagicMock, AsyncMock
from agent.security import RateLimitMiddleware

@pytest.mark.asyncio
async def test_rate_limit_logging(caplog):
    # Setup
    app = AsyncMock()
    mw = RateLimitMiddleware(app, limit=1, window=60, protected_paths=["/api"])

    # Configure logging capture
    caplog.set_level(logging.WARNING, logger="agent.security")

    # Request 1: Allowed
    req1 = MagicMock()
    req1.url.path = "/api/test"
    req1.client.host = "192.168.1.1"
    req1.headers.get.return_value = None

    async def call_next(request):
        return "success"

    await mw.dispatch(req1, call_next)

    # Verify no warning logged
    assert len(caplog.records) == 0

    # Request 2: Blocked
    req2 = MagicMock()
    req2.url.path = "/api/test"
    req2.client.host = "192.168.1.1"
    req2.headers.get.return_value = None

    response = await mw.dispatch(req2, call_next)

    # Verify blocked
    assert response.status_code == 429

    # Verify warning logged
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert "Rate limit exceeded for 192.168.1.1 on /api/test" in caplog.records[0].message
