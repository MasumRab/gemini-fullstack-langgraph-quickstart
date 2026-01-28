import pytest
import logging
from unittest.mock import MagicMock, AsyncMock
from agent.security import RateLimitMiddleware
from agent.app import ContentSizeLimitMiddleware

@pytest.mark.asyncio
async def test_rate_limit_logging(caplog):
    app = AsyncMock()
    # Limit 0 to fail immediately
    mw = RateLimitMiddleware(app, limit=0, window=60, protected_paths=["/api"])

    req = MagicMock()
    req.url.path = "/api/test"
    req.client.host = "1.2.3.4"
    req.headers.get.return_value = None # No X-Forwarded-For

    async def call_next(request):
        return "success"

    # Capture logs
    with caplog.at_level(logging.WARNING):
        response = await mw.dispatch(req, call_next)

    assert response.status_code == 429

    # Assert log message - specific messages will be added in implementation
    # We expect some log containing "Rate limit" and the IP
    log_text = caplog.text
    assert "Rate limit" in log_text or "Too Many Requests" in log_text
    assert "1.2.3.4" in log_text
    assert "/api/test" in log_text

@pytest.mark.asyncio
async def test_content_size_limit_logging(caplog):
    app = AsyncMock()
    mw = ContentSizeLimitMiddleware(app, max_upload_size=100)

    req = MagicMock()
    req.method = "POST"
    req.headers = {
        "content-length": "200" # Exceeds 100
    }

    async def call_next(request):
        return "success"

    with caplog.at_level(logging.WARNING):
        response = await mw.dispatch(req, call_next)

    assert response.status_code == 413

    log_text = caplog.text
    assert "Rejected request with content length" in log_text
