from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.responses import PlainTextResponse

import agent.security
from agent.security import RateLimitMiddleware, extract_client_ip_from_forwarded

# --- shared scaffolding -----------------------------------------------------
# Every middleware test below drives the same minimal ASGI exchange. Keeping the
# stubs at module level instead of redefining them per test keeps duplicated
# lines on new code under the threshold SonarCloud enforces.


async def _ok_app(scope, receive, send):
    """Minimal downstream app that always answers 200 OK."""
    response = PlainTextResponse("OK")
    await response(scope, receive, send)


async def _receive(*args, **kwargs):
    return {"type": "http.request"}


async def _send(*args, **kwargs):
    return None


def _scope(client_ip, forwarded=None, path="/protected"):
    """Build an http scope for `client_ip`, optionally carrying X-Forwarded-For."""
    headers = [(b"host", b"localhost")]
    if forwarded is not None:
        headers.append((b"x-forwarded-for", forwarded.encode()))
    return {
        "type": "http",
        "path": path,
        "client": (client_ip, 1234),
        "headers": headers,
    }


def _middleware(trust_proxy_headers, protected_paths=("/protected",), limit=10, window=60):
    return RateLimitMiddleware(
        _ok_app,
        limit=limit,
        window=window,
        protected_paths=list(protected_paths),
        trust_proxy_headers=trust_proxy_headers,
    )


async def _hit(middleware, client_ip, forwarded=None):
    """Drive one request through `middleware`; return its rate-limit bucket map."""
    await middleware(_scope(client_ip, forwarded), _receive, _send)
    return middleware.requests


@pytest.mark.asyncio
async def test_proxy_security_default_secure():
    """Verify that by default (trust_proxy_headers=False), X-Forwarded-For is ignored."""
    # Real peer 1.2.3.4 with a spoofed header: only the peer may key the bucket.
    buckets = await _hit(_middleware(trust_proxy_headers=False), "1.2.3.4", "5.6.7.8")

    assert "1.2.3.4" in buckets
    assert "5.6.7.8" not in buckets


@pytest.mark.asyncio
async def test_proxy_security_trusted_enabled(monkeypatch):
    """Verify that when enabled, X-Forwarded-For IS used."""
    monkeypatch.setattr(agent.security, "TRUSTED_PROXY_COUNT", 1)
    # Peer 10.0.0.1 is the proxy; the client it reports is 5.6.7.8.
    buckets = await _hit(_middleware(trust_proxy_headers=True), "10.0.0.1", "5.6.7.8")

    assert "5.6.7.8" in buckets
    assert "10.0.0.1" not in buckets


@pytest.mark.asyncio
async def test_spoofing_vulnerability(monkeypatch):
    """
    With no trusted proxies configured, X-Forwarded-For is ignored entirely.

    The attacker sets a public IP in the header and a private one is appended by an
    upstream hop. Neither may become the rate-limit key: with TRUSTED_PROXY_COUNT=0
    nothing in the header was written by a proxy we trust, so the only trustworthy
    address is the connection peer.
    """

    # trust_proxy_headers=True but no trusted proxies: the header must still be dropped.
    monkeypatch.setattr(agent.security, "TRUSTED_PROXY_COUNT", 0)
    monkeypatch.setattr(agent.security, "TRUSTED_PROXIES", set())

    # Attacker spoofs "8.8.8.8"; an upstream hop appends "10.0.0.5"; peer is 10.0.0.1.
    buckets = await _hit(
        _middleware(trust_proxy_headers=True), "10.0.0.1", "8.8.8.8, 10.0.0.5"
    )

    # Tracked under the connection peer and under neither header value — otherwise
    # a client can mint a fresh bucket per request.
    assert "10.0.0.1" in buckets
    assert "8.8.8.8" not in buckets
    assert "10.0.0.5" not in buckets


@pytest.mark.asyncio
async def test_trusted_proxy_chain_uses_first_untrusted_hop(monkeypatch):
    """
    With the connection peer in TRUSTED_PROXIES, the right-to-left walk applies.

    Header "8.8.8.8, 10.0.0.5" read from peer 10.0.0.1: the walk skips trusted hops from
    the right and returns the first address it does not trust, which is 10.0.0.5.
    """
    monkeypatch.setattr(agent.security, "TRUSTED_PROXIES", {"10.0.0.1"})
    monkeypatch.setattr(agent.security, "TRUSTED_PROXY_COUNT", 0)

    buckets = await _hit(
        _middleware(trust_proxy_headers=True), "10.0.0.1", "8.8.8.8, 10.0.0.5"
    )

    assert "10.0.0.5" in buckets
    assert "10.0.0.1" not in buckets


async def _call_next(request):
    return "success"


def _fake_request(client_ip, forwarded=None, path="/api/test"):
    """A MagicMock request shaped the way RateLimitMiddleware.dispatch reads one."""
    request = MagicMock()
    request.url.path = path
    request.client.host = client_ip
    request.headers.get.return_value = forwarded
    return request


def _assert_rate_limited(response, message):
    """The middleware answers with a Response when it blocks, else call_next's value."""
    assert hasattr(response, "status_code"), message
    assert response.status_code == 429, message


@pytest.mark.asyncio
async def test_x_forwarded_for_ignored_by_default():
    """
    Test that X-Forwarded-For is IGNORED by default to prevent spoofing.
    This test expects SECURE behavior (Req 2 blocked).
    """
    # Limit 1 request per window, default trust_proxy_headers=False
    mw = RateLimitMiddleware(AsyncMock(), limit=1, window=60, protected_paths=["/api"])
    client_ip = "1.2.3.4"

    # Request 1: normal request, no header.
    assert await mw.dispatch(_fake_request(client_ip), _call_next) == "success"

    # Request 2: attacker spoofs X-Forwarded-For. The header is ignored, so this
    # still counts against 1.2.3.4, which is already over its limit.
    response2 = await mw.dispatch(_fake_request(client_ip, "10.0.0.1"), _call_next)
    _assert_rate_limited(response2, "Rate limit bypassed via X-Forwarded-For!")


@pytest.mark.asyncio
async def test_x_forwarded_for_trusted_when_configured(monkeypatch):
    """
    Test that X-Forwarded-For IS respected when trust_proxy_headers is True.
    This is for legitimate use cases (behind load balancer).
    """
    monkeypatch.setattr(agent.security, "TRUSTED_PROXY_COUNT", 1)
    # Limit 1 request per window, BUT we trust proxies.
    mw = RateLimitMiddleware(
        AsyncMock(), limit=1, window=60, protected_paths=["/api"], trust_proxy_headers=True
    )
    lb_ip = "10.0.0.1"  # Load balancer address every client connects from

    # Client A and client B share the LB peer but are distinct rate-limit keys.
    assert await mw.dispatch(_fake_request(lb_ip, "1.2.3.4"), _call_next) == "success"
    assert await mw.dispatch(_fake_request(lb_ip, "5.6.7.8"), _call_next) == "success"

    # Client A again: its bucket is now exhausted.
    response3 = await mw.dispatch(_fake_request(lb_ip, "1.2.3.4"), _call_next)
    _assert_rate_limited(response3, "Client A should have been rate limited on second request.")


# ---------------------------------------------------------------------------
# Direct unit tests for extract_client_ip_from_forwarded
#
# These call the function with explicit arguments rather than monkeypatching the
# module globals, so each row exercises one branch on its own. Note the
# None-vs-empty distinction: `trusted_proxies=None` means "fall back to the
# TRUSTED_PROXIES global", while `set()` means "explicitly no trusted proxies"
# and selects the count-based path. The last case depends on that difference.
# ---------------------------------------------------------------------------

_DIRECT_CASES = [
    pytest.param(
        "203.0.113.9, 10.0.0.1, 10.0.0.2",
        {"trusted_proxies": {"10.0.0.1", "10.0.0.2"}},
        "203.0.113.9",
        id="trusted-proxies-skips-from-the-right",
    ),
    pytest.param(
        "1.2.3.4, 203.0.113.9, 10.0.0.1",
        {"trusted_proxies": {"10.0.0.1"}},
        "203.0.113.9",
        id="trusted-proxies-prefers-rightmost-untrusted-hop",
    ),
    pytest.param(
        "203.0.113.9, 10.8.0.4",
        {"trusted_proxies": {"10.0.0.0/8"}},
        "203.0.113.9",
        id="trusted-proxies-supports-cidr-entries",
    ),
    pytest.param(
        "203.0.113.9, 10.0.0.1",
        {"trusted_proxy_count": 1, "trusted_proxies": set()},
        "203.0.113.9",
        id="count-selects-the-element-before-the-trusted-hops",
    ),
    pytest.param(
        "198.51.100.7, 10.0.0.1",
        {"trusted_proxy_count": 1, "trusted_proxies": set()},
        "198.51.100.7",
        id="count-equal-to-chain-length-returns-leftmost",
    ),
    pytest.param(
        "203.0.113.9",
        {"trusted_proxy_count": 0, "trusted_proxies": set(), "fallback_ip": "127.0.0.1"},
        "127.0.0.1",
        id="no-trust-configured-returns-fallback",
    ),
    pytest.param(
        "not-an-ip, 203.0.113.9, 10.0.0.1",
        {"trusted_proxies": {"10.0.0.1"}},
        "203.0.113.9",
        id="invalid-entries-are-skipped",
    ),
    pytest.param(
        "10.0.0.2, 10.0.0.1",
        {"trusted_proxies": {"10.0.0.1", "10.0.0.2"}},
        "10.0.0.2",
        id="all-hops-trusted-returns-leftmost",
    ),
    pytest.param("", {"fallback_ip": "127.0.0.1"}, "127.0.0.1", id="empty-header"),
]


@pytest.mark.parametrize(("header", "kwargs", "expected"), _DIRECT_CASES)
def test_extract_client_ip(header, kwargs, expected):
    """One row per branch of the trusted-hop walk."""
    assert extract_client_ip_from_forwarded(header, **kwargs) == expected


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


def test_direct_none_reads_the_global_not_an_empty_set(monkeypatch):
    """`trusted_proxies=None` must fall back to the module global, not to empty."""
    monkeypatch.setattr(agent.security, "TRUSTED_PROXIES", {"10.0.0.1"})
    assert (
        extract_client_ip_from_forwarded("203.0.113.9, 10.0.0.1", trusted_proxies=None)
        == "203.0.113.9"
    )
