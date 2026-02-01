from fastapi import FastAPI
from starlette.testclient import TestClient

from agent.security import RateLimitMiddleware


def test_rate_limit_secure_default():
    """
    Verify that by default (trust_proxy_headers=False),
    X-Forwarded-For headers are IGNORED.
    This prevents IP spoofing attacks.
    """
    app = FastAPI()

    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}

    # Secure default: trust_proxy_headers=False
    app.add_middleware(
        RateLimitMiddleware,
        limit=1,
        window=60,
        protected_paths=["/test"],
        trust_proxy_headers=False,
    )

    client = TestClient(app)

    # Request 1: Should pass
    response1 = client.get("/test", headers={"X-Forwarded-For": "1.1.1.1"})
    assert response1.status_code == 200

    # Request 2: From same actual client, but trying to spoof different IP
    # Since we ignore the header, both look like the same client (127.0.0.1 or testclient).
    # This should be RATE LIMITED (429).
    response2 = client.get("/test", headers={"X-Forwarded-For": "2.2.2.2"})

    assert response2.status_code == 429, "Rate limit bypassed via IP spoofing!"


def test_rate_limit_trusted_proxy():
    """
    Verify that when configured (trust_proxy_headers=True),
    X-Forwarded-For headers ARE used.
    This supports legitimate proxy setups.
    """
    app = FastAPI()

    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}

    # Explicit trust enabled
    app.add_middleware(
        RateLimitMiddleware,
        limit=1,
        window=60,
        protected_paths=["/test"],
        trust_proxy_headers=True,
    )

    client = TestClient(app)

    # Request 1: From IP 1.1.1.1
    response1 = client.get("/test", headers={"X-Forwarded-For": "1.1.1.1"})
    assert response1.status_code == 200

    # Request 2: From IP 2.2.2.2 (different spoofed/proxied IP)
    # Since we trust headers, this is seen as a NEW client.
    # Should PASS (200).
    response2 = client.get("/test", headers={"X-Forwarded-For": "2.2.2.2"})
    assert response2.status_code == 200

    # Request 3: From IP 1.1.1.1 again (should be limited now)
    response3 = client.get("/test", headers={"X-Forwarded-For": "1.1.1.1"})
    assert response3.status_code == 429
