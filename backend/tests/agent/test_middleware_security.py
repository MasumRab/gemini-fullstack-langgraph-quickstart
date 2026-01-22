import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from fastapi import Request, Response
from agent.app import app, ContentSizeLimitMiddleware

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

@pytest.mark.asyncio
async def test_content_size_limit_missing_length():
    """Test that ContentSizeLimitMiddleware rejects POST/PUT/PATCH without Content-Length."""

    async def mock_call_next(request):
        return Response("OK", status_code=200)

    app_mock = MagicMock()
    middleware = ContentSizeLimitMiddleware(app_mock)

    async def receive():
        return {'type': 'http.request', 'body': b'data'}

    # 1. POST without Content-Length
    scope = {
        'type': 'http',
        'method': 'POST',
        'headers': [], # No Content-Length
        'path': '/test',
    }
    request = Request(scope, receive)

    response = await middleware.dispatch(request, mock_call_next)
    assert response.status_code == 411
    assert response.body == b"Content-Length required"

    # 2. PUT without Content-Length
    scope['method'] = 'PUT'
    request = Request(scope, receive)
    response = await middleware.dispatch(request, mock_call_next)
    assert response.status_code == 411

    # 3. GET without Content-Length (Should pass)
    scope['method'] = 'GET'
    request = Request(scope, receive)
    response = await middleware.dispatch(request, mock_call_next)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_content_size_limit_invalid_length():
    """Test that ContentSizeLimitMiddleware handles invalid Content-Length gracefully."""

    async def mock_call_next(request):
        return Response("OK", status_code=200)

    app_mock = MagicMock()
    middleware = ContentSizeLimitMiddleware(app_mock)

    async def receive():
        return {'type': 'http.request', 'body': b'data'}

    # Invalid Content-Length
    scope = {
        'type': 'http',
        'method': 'POST',
        'headers': [(b'content-length', b'invalid')],
        'path': '/test',
    }
    request = Request(scope, receive)

    response = await middleware.dispatch(request, mock_call_next)
    assert response.status_code == 400
    assert response.body == b"Invalid Content-Length"
