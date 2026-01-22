import time
import pytest
from unittest.mock import MagicMock, AsyncMock
from agent.security import RateLimitMiddleware

@pytest.mark.asyncio
async def test_rate_limit_cleanup_throttling():
    """Verify that cleanup is throttled to prevent DoS."""
    app = MagicMock()
    mw = RateLimitMiddleware(app, limit=100, window=60, protected_paths=["/test"])

    # 1. Fill table to limit
    # We cheat and directly populate the dict to save time
    for i in range(10000):
        mw.requests[f"client_{i}"] = [time.time()]

    # 2. Add 10001st client - should trigger cleanup (first run)
    # We need to ensure last_cleanup is 0 (it is by default)
    # And we need to make sure now - last_cleanup > 60.
    # time.time() is huge, so it will trigger.

    req = MagicMock()
    req.url.path = "/test/1"
    req.headers = {}
    req.client.host = "trigger_1"

    call_next = AsyncMock(return_value="ok")

    # Capture initial cleanup timestamp
    await mw.dispatch(req, call_next)

    first_cleanup_time = mw.last_cleanup
    assert first_cleanup_time > 0
    assert len(mw.requests) >= 10000 # Might have cleaned up or not depending on timestamps

    # 3. Add 10002nd client immediately - should NOT trigger cleanup
    req2 = MagicMock()
    req2.url.path = "/test/2"
    req2.headers = {}
    req2.client.host = "trigger_2"

    # We expect this to NOT update last_cleanup
    await mw.dispatch(req2, call_next)

    assert mw.last_cleanup == first_cleanup_time

    # 4. Verify fallback logic: if full and no cleanup, new client gets 503
    # We need to fill it to 10001+ without cleanup running
    # Since we added trigger_1 and trigger_2, we have at least 10002 items
    # (assuming none were expired/cleaned in step 2).
    # Since we populated with time.time(), they are all fresh (<60s).
    # So step 2 cleanup ran but removed nothing.
    # So len is 10001.
    # Step 3 added trigger_2. len is 10002.
    # Step 3 did NOT run cleanup.
    # But wait, if len > 10000, fallback runs.
    # In step 3, len was 10001 (trigger_1 + 10000).
    # We added trigger_2 (len 10002).
    # Fallback check: if len > 10000. True.
    # if len(active_requests) == 1. True (trigger_2 is new).
    # Should return 503.

    # So step 3 should actually fail with 503!
    # Let's verify that.

    req3 = MagicMock()
    req3.url.path = "/test/3"
    req3.headers = {}
    req3.client.host = "trigger_3"

    response = await mw.dispatch(req3, call_next)
    # Check if response is 503
    # dispatch returns Response object or await call_next
    if isinstance(response, str) and response == "ok":
        assert False, "Should have been rejected with 503"
    else:
        assert response.status_code == 503

@pytest.mark.asyncio
async def test_memory_cleanup_preserves_active_clients():
    """Verify that cleanup doesn't remove active clients when it actually runs."""
    app = MagicMock()
    mw = RateLimitMiddleware(app, limit=100, window=60, protected_paths=["/test"])

    # Force cleanup to run
    mw.last_cleanup = 0

    # Add active client
    mw.requests["active"] = [time.time()]
    # Add stale client
    mw.requests["stale"] = [time.time() - 61]

    # Fill to limit with stale clients to trigger cleanup
    for i in range(10000):
        mw.requests[f"stale_{i}"] = [time.time() - 61]

    req = MagicMock()
    req.url.path = "/test/trigger"
    req.headers = {}
    req.client.host = "trigger"

    call_next = AsyncMock(return_value="ok")

    await mw.dispatch(req, call_next)

    # "active" should remain
    assert "active" in mw.requests
    # "stale" should be gone
    assert "stale" not in mw.requests
    # "trigger" should be added
    assert "trigger" in mw.requests
