"""Security middleware and utilities for the agent."""

import logging
import re
from typing import List, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from agent.rate_limiter import RateLimiter, RateLimitExceeded

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        """Process the request and add security headers."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limits."""

    def __init__(
        self,
        app,
        limit: int = 100,
        window: int = 60,
        protected_paths: Optional[List[str]] = None,
        trust_proxy_headers: bool = False,
    ):
        """Initialize the rate limiter.

        Args:
            app: The ASGI application.
            limit: Number of requests allowed per window.
            window: Time window in seconds.
            protected_paths: List of paths to apply rate limiting to.
            trust_proxy_headers: Whether to trust X-Forwarded-For headers.
        """
        super().__init__(app)
        self.limiter = RateLimiter(limit, window)
        self.protected_paths = protected_paths or []
        self.trust_proxy_headers = trust_proxy_headers

    def get_client_key(self, request: Request) -> str:
        """Extract client identifier (IP) from request.

        Attempts to find the client's IP address.
        If trust_proxy_headers is True, checks X-Forwarded-For.
        Falls back to request.client.host.
        Sanitizes the result to prevent log injection.
        """
        client_ip = "unknown"

        if self.trust_proxy_headers:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                # Direct split and strip, no try/except needed as split never raises
                ips = [ip.strip() for ip in forwarded.split(",")]
                # Use the last IP in the list as it's the most trusted (closest to our server)
                # or the first if we want the original client (but that's spoofable).
                # Standard practice for identifying the *connecting* client in a trusted chain is often the last one added by the trusted proxy.
                # However, for rate limiting user origin, usually the *first* is used if we trust the chain.
                # If trust_proxy_headers is True, we assume we are behind a trusted proxy (like Render/Cloudflare)
                # which appends the real client IP to the end or beginning depending on config.
                # Let's use the last one as it is the one that connected to the proxy.
                # Actually, X-Forwarded-For: <client>, <proxy1>, <proxy2>
                # If we trust the proxy, the *last* IP is the one that connected to *us* (the proxy),
                # but we want the *original* client.
                # If we trust the proxy, we can trust the *first* non-private IP, or just the first one if strict.
                # Let's stick to the previous logic but simplified: last IP is safer against spoofing if we only trust the immediate upstream.
                if ips:
                    client_ip = ips[-1]

        if client_ip == "unknown" and request.client and request.client.host:
            client_ip = request.client.host

        # Sanitize to prevent log injection
        # Allow only alphanumeric, dots, colons (IPv6)
        if not re.match(r"^[a-zA-Z0-9.:]+$", client_ip):
            return "unknown"

        return client_ip

    async def dispatch(self, request: Request, call_next):
        """Check rate limit for protected paths."""
        # Check if path is protected
        is_protected = any(
            request.url.path.startswith(path) for path in self.protected_paths
        )

        if not is_protected:
            return await call_next(request)

        client_key = self.get_client_key(request)

        try:
            self.limiter.wait_if_needed(client_key)
        except RateLimitExceeded as e:
            logger.warning(f"Rate limit exceeded for {client_key}: {e}")
            return Response("Rate limit exceeded", status_code=429)

        return await call_next(request)
