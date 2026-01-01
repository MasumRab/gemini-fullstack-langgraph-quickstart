import pytest
from fastapi.testclient import TestClient
from agent.app import app

# Initialize TestClient with a trusted host (localhost) to pass TrustedHostMiddleware
client = TestClient(app, base_url="http://localhost")

def test_content_size_limit():
    """Test that requests exceeding the size limit are rejected."""
    # The limit is 10MB.
    # We will simulate a large Content-Length header.
    # Note: TestClient does not automatically enforcing content-length for internal calls
    # the same way a real server does with middleware if we just pass 'json'.
    # We need to manually set the header to simulate the check in ContentSizeLimitMiddleware.

    # 1. Valid size
    response = client.get("/health")
    assert response.status_code == 200

    # 2. Invalid size (simulated via header)
    # The middleware checks header "content-length".
    headers = {"content-length": str(20 * 1024 * 1024)} # 20MB
    response = client.post("/agent/invoke", headers=headers, json={"input": {}})
    assert response.status_code == 413
    assert response.text == "Request entity too large"

def test_trusted_host_middleware():
    """Test that requests with invalid Host headers are rejected."""
    # Config default is localhost, 127.0.0.1.

    # 1. Valid Host
    response = client.get("/health", headers={"host": "localhost"})
    assert response.status_code == 200

    response = client.get("/health", headers={"host": "127.0.0.1"})
    assert response.status_code == 200

    # 2. Invalid Host
    # TrustedHostMiddleware returns 400 for invalid hosts
    # Note: We must explicitly set the Host header to override the client's default (localhost)
    response = client.get("/health", headers={"host": "evil.com"})
    assert response.status_code == 400
