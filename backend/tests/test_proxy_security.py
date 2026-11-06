from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.responses import PlainTextResponse

import agent.security
from agent.security import RateLimitMiddleware, extract_client_ip_from_forwarded


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
    # Real IP: 1.2.3.4
    # Spoofed Header: 5.6.7.8
    headers = [(b"host", b"localhost"), (b"x-forwarded-for", b"5.6.7.8")]

    scope = {
        "type": "http",
        "path": "/protected",
        "client": ("1.2.3.4", 1234),
        "headers": headers,
    }

    async def mock_send(*args, **kwargs):
        pass

    async def mock_receive(*args, **kwargs):
        return {"type": "http.request"}

    await middleware(scope, mock_receive, mock_send)

    # Expectation: The request should be tracked under the Real IP (1.2.3.4), NOT the spoofed one
    assert "1.2.3.4" in middleware.requests
    assert "5.6.7.8" not in middleware.requests


@pytest.mark.asyncio
async def test_proxy_security_trusted_enabled(monkeypatch):
    """Verify that when enabled, X-Forwarded-For IS used."""

    # Mock App
    async def mock_app(scope, receive, send):
        response = PlainTextResponse("OK")
        await response(scope, receive, send)

    # Initialize middleware with trust_proxy_headers=True
    monkeypatch.setattr(agent.security, "TRUSTED_PROXY_COUNT", 1)

    middleware = RateLimitMiddleware(
        mock_app,
        limit=10,
        window=60,
        protected_paths=["/protected"],
        trust_proxy_headers=True,
    )

    # Simulate request
    # Real IP: 10.0.0.1 (Proxy)
    # Header: 5.6.7.8 (Client)
    headers = [(b"host", b"localhost"), (b"x-forwarded-for", b"5.6.7.8")]

    scope = {
        "type": "http",
        "path": "/protected",
        "client": ("10.0.0.1", 1234),
        "headers": headers,
    }

    async def mock_send(*args, **kwargs):
        pass

    async def mock_receive(*args, **kwargs):
        return {"type": "http.request"}

    await middleware(scope, mock_receive, mock_send)

    # Expectation: The request should be tracked under the Client IP (5.6.7.8)
    assert "5.6.7.8" in middleware.requests
    assert "10.0.0.1" not in middleware.requests


@pytest.mark.asyncio
async def test_spoofing_vulnerability(monkeypatch):
    """
    With no trusted proxies configured, X-Forwarded-For is ignored entirely.

    The attacker sets a public IP in the header and a private one is appended by an
    upstream hop. Neither may become the rate-limit key: with TRUSTED_PROXY_COUNT=0
    nothing in the header was written by a proxy we trust, so the only trustworthy
    address is the connection peer.
    """

    # Mock App
    async def mock_app(scope, receive, send):
        response = PlainTextResponse("OK")
        await response(scope, receive, send)

    # trust_proxy_headers=True but no trusted proxies: the header must still be dropped
    monkeypatch.setattr(agent.security, "TRUSTED_PROXY_COUNT", 0)
    monkeypatch.setattr(agent.security, "TRUSTED_PROXIES", set())

    middleware = RateLimitMiddleware(
        mock_app,
        limit=10,
        window=60,
        protected_paths=["/protected"],
        trust_proxy_headers=True,
    )

    # Scenario:
    # Attacker Spoofs Header: "8.8.8.8" (Public)
    # Upstream hop appends: "10.0.0.5"
    # Connection peer: 10.0.0.1

    headers = [(b"host", b"localhost"), (b"x-forwarded-for", b"8.8.8.8, 10.0.0.5")]

    scope = {
        "type": "http",
        "path": "/protected",
        "client": ("10.0.0.1", 1234),  # Connection from Proxy
        "headers": headers,
    }

    async def mock_send(*args, **kwargs):
        pass

    async def mock_receive(*args, **kwargs):
        return {"type": "http.request"}

    await middleware(scope, mock_receive, mock_send)

    # Expectation: the request is tracked under the connection peer, and under neither
    # header value — otherwise a client can mint a fresh bucket per request.
    assert "10.0.0.1" in middleware.requests
    assert "8.8.8.8" not in middleware.requests
    assert "10.0.0.5" not in middleware.requests


@pytest.mark.asyncio
async def test_trusted_proxy_chain_uses_first_untrusted_hop(monkeypatch):
    """
    With the connection peer in TRUSTED_PROXIES, the right-to-left walk applies.

    Header "8.8.8.8, 10.0.0.5" read from peer 10.0.0.1: the walk skips trusted hops from
    the right and returns the first address it does not trust, which is 10.0.0.5.
    """
    monkeypatch.setattr(agent.security, "TRUSTED_PROXIES", {"10.0.0.1"})
    monkeypatch.setattr(agent.security, "TRUSTED_PROXY_COUNT", 0)

    async def mock_app(scope, receive, send):
        response = PlainTextResponse("OK")
        await response(scope, receive, send)

    middleware = RateLimitMiddleware(
        mock_app,
        limit=10,
        window=60,
        protected_paths=["/protected"],
        trust_proxy_headers=True,
    )

    headers = [(b"host", b"localhost"), (b"x-forwarded-for", b"8.8.8.8, 10.0.0.5")]
    scope = {
        "type": "http",
        "path": "/protected",
        "client": ("10.0.0.1", 1234),
        "headers": headers,
    }

    async def mock_send(*args, **kwargs):
        pass

    async def mock_receive(*args, **kwargs):
        return {"type": "http.request"}

    await middleware(scope, mock_receive, mock_send)

    assert "10.0.0.5" in middleware.requests
    assert "10.0.0.1" not in middleware.requests


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
    req1.headers.get.return_value = None  # No X-Forwarded-For

    response1 = await mw.dispatch(req1, call_next)
    assert response1 == "success"

    # Request 2: Attacker tries to bypass by spoofing X-Forwarded-For
    req2 = MagicMock()
    req2.url.path = "/api/test"
    req2.client.host = client_ip  # Same real IP
    req2.headers.get.return_value = "10.0.0.1"  # Spoofed IP

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
async def test_x_forwarded_for_trusted_when_configured(monkeypatch):
    """
    Test that X-Forwarded-For IS respected when trust_proxy_headers is True.
    This is for legitimate use cases (behind load balancer).
    """
    app = AsyncMock()
    # Limit 1 request per window, BUT we trust proxies
    monkeypatch.setattr(agent.security, "TRUSTED_PROXY_COUNT", 1)

    mw = RateLimitMiddleware(
        app, limit=1, window=60, protected_paths=["/api"], trust_proxy_headers=True
    )

    # Real Client IP (Load Balancer IP)
    lb_ip = "10.0.0.1"

    async def call_next(request):
        return "success"

    # Request 1: Client A behind LB
    req1 = MagicMock()
    req1.url.path = "/api/test"
    req1.client.host = lb_ip
    req1.headers.get.return_value = "1.2.3.4"  # Client A

    response1 = await mw.dispatch(req1, call_next)
    assert response1 == "success"

    # Request 2: Client B behind LB
    req2 = MagicMock()
    req2.url.path = "/api/test"
    req2.client.host = lb_ip  # Same LB IP
    req2.headers.get.return_value = "5.6.7.8"  # Client B

    response2 = await mw.dispatch(req2, call_next)

    # Since we trust the proxy header, Client B should be treated as a different user.
    # So it should PASS (success), not 429.
    assert response2 == "success"

    # Request 3: Client A again (should be blocked now)
    req3 = MagicMock()
    req3.url.path = "/api/test"
    req3.client.host = lb_ip
    req3.headers.get.return_value = "1.2.3.4"  # Client A again

    response3 = await mw.dispatch(req3, call_next)
    if hasattr(response3, "status_code"):
        assert response3.status_code == 429
    else:
        pytest.fail("Client A should have been rate limited on second request.")


# ---------------------------------------------------------------------------
# Direct unit tests for extract_client_ip_from_forwarded
#
# These call the function with explicit arguments rather than monkeypatching the
# module globals, so each case exercises one branch on its own. Note the
# None-vs-empty distinction: `trusted_proxies=None` means "fall back to the
# TRUSTED_PROXIES global", while `set()` means "explicitly no trusted proxies"
# and selects the count-based path. Two cases below depend on that difference.
# ---------------------------------------------------------------------------


def test_direct_trusted_proxies_skips_from_the_right():
    """Rightmost trusted hops are skipped; the first untrusted IP wins."""
    assert (
        extract_client_ip_from_forwarded(
            "203.0.113.9, 10.0.0.1, 10.0.0.2",
            trusted_proxies={"10.0.0.1", "10.0.0.2"},
        )
        == "203.0.113.9"
    )


def test_direct_trusted_proxies_prefers_rightmost_untrusted_hop():
    """A hop closer to the server beats a client-supplied leftmost value."""
    assert (
        extract_client_ip_from_forwarded(
            "1.2.3.4, 203.0.113.9, 10.0.0.1",
            trusted_proxies={"10.0.0.1"},
        )
        == "203.0.113.9"
    )


def test_direct_trusted_proxies_supports_cidr_entries():
    """Trusted entries may be CIDR ranges, not only single addresses."""
    assert (
        extract_client_ip_from_forwarded(
            "203.0.113.9, 10.8.0.4",
            trusted_proxies={"10.0.0.0/8"},
        )
        == "203.0.113.9"
    )


def test_direct_count_selects_the_element_before_the_trusted_hops():
    """count=1 over [client, proxy1] returns ips[-2], the client."""
    assert (
        extract_client_ip_from_forwarded(
            "203.0.113.9, 10.0.0.1",
            trusted_proxy_count=1,
            trusted_proxies=set(),
        )
        == "203.0.113.9"
    )


def test_direct_count_len_equal_to_chain_returns_leftmost():
    """count spanning the whole chain still has a valid index: ips[-len]."""
    assert (
        extract_client_ip_from_forwarded(
            "198.51.100.7, 10.0.0.1",
            trusted_proxy_count=1,
            trusted_proxies=set(),
        )
        == "198.51.100.7"
    )


def test_direct_count_beyond_chain_falls_back_to_leftmost(caplog):
    """An over-large count warns and degrades to ips[0] instead of raising."""
    with caplog.at_level("WARNING"):
        got = extract_client_ip_from_forwarded(
            "203.0.113.9, 10.0.0.1",
            trusted_proxy_count=5,
            trusted_proxies=set(),
        )
    assert got == "203.0.113.9"
    assert any("Not enough IPs" in r.message for r in caplog.records)


def test_direct_no_trust_configured_returns_fallback():
    """count=0 with no trusted proxies must not trust the header at all."""
    assert (
        extract_client_ip_from_forwarded(
            "203.0.113.9",
            trusted_proxy_count=0,
            trusted_proxies=set(),
            fallback_ip="127.0.0.1",
        )
        == "127.0.0.1"
    )


def test_direct_invalid_entries_are_skipped():
    """Unparseable hops are dropped before indexing."""
    assert (
        extract_client_ip_from_forwarded(
            "not-an-ip, 203.0.113.9, 10.0.0.1",
            trusted_proxies={"10.0.0.1"},
        )
        == "203.0.113.9"
    )


def test_direct_all_hops_trusted_returns_leftmost():
    """If every hop is trusted there is no untrusted candidate; use the leftmost."""
    assert (
        extract_client_ip_from_forwarded(
            "10.0.0.2, 10.0.0.1",
            trusted_proxies={"10.0.0.1", "10.0.0.2"},
        )
        == "10.0.0.2"
    )


def test_direct_empty_header_returns_fallback():
    assert extract_client_ip_from_forwarded("", fallback_ip="127.0.0.1") == "127.0.0.1"


def test_direct_none_reads_the_global_not_an_empty_set(monkeypatch):
    """`trusted_proxies=None` must fall back to the module global."""
    monkeypatch.setattr(agent.security, "TRUSTED_PROXIES", {"10.0.0.1"})
    assert (
        extract_client_ip_from_forwarded(
            "203.0.113.9, 10.0.0.1",
            trusted_proxies=None,
        )
        == "203.0.113.9"
    )
