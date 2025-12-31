"""Security middleware for the agent application."""

import time
from collections import defaultdict
from typing import List, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        """Process the request and add security headers to the response."""
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Protect against clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Strict Transport Security (HSTS)
        # Max-age: 1 year. Include subdomains.
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Permissions Policy
        # Restrict access to sensitive features the agent doesn't need
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(), payment=(), usb=()"

        # Content Security Policy (CSP)
        # Default to very strict (API only), but allow styles/images if needed for simple UI
        # Since this is primarily an API backend, we start strict.
        # We allow 'self' for both because we serve frontend from /app on same origin.
        # We also allow 'unsafe-inline' for styles because many React apps use it,
        # but for scripts we try to be strict.
        csp_policy = (
            "default-src 'self'; "
            "img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp_policy

        # XSS Protection (legacy but good defense in depth)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""

    def __init__(
        self,
        app,
        limit: int = 100,
        window: int = 60,
        protected_paths: Optional[List[str]] = None,
    ):
        """Initialize the rate limiter.

        Args:
            app: The FastAPI application.
            limit: Maximum requests allowed per window.
            window: Time window in seconds.
            protected_paths: List of path prefixes to apply rate limiting to.
                             If None, applies to all paths.
        """
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.protected_paths = protected_paths if protected_paths is not None else []
        self.requests = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        """Check rate limit for API endpoints."""
        path = request.url.path

        # Check if path is protected
        is_protected = False
        if not self.protected_paths:
            # If no paths specified, protect everything? Or protect nothing?
            # Usually strict default means protect everything.
            # But here we want to protect specific API endpoints.
            # Let's assume if list is empty, we don't limit (or user should provide paths).
            # To be safe, if protected_paths is None/Empty in __init__, we default to [] which means effectively disabled
            # unless we change default.
            # Let's adhere to "explicit is better than implicit". If list is empty, nothing is protected.
            pass
        else:
            for prefix in self.protected_paths:
                if path.startswith(prefix):
                    is_protected = True
                    break

        if is_protected:
            # Support for proxies (e.g. Render/Nginx)
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                # The first IP is the original client
                client_ip = forwarded.split(",")[0].strip()
                # Basic safety: limit length to prevent memory exhaustion attacks with huge headers
                if len(client_ip) > 100:
                    client_ip = client_ip[:100]
            else:
                client_ip = request.client.host if request.client else "unknown"

            now = time.time()

            # Clean old requests (simple sliding window)
            current_requests = self.requests[client_ip]
            # Prune old timestamps
            active_requests = [t for t in current_requests if now - t < self.window]

            if len(active_requests) >= self.limit:
                # Update map with pruned list before returning
                self.requests[client_ip] = active_requests
                return Response("Too Many Requests", status_code=429)

            active_requests.append(now)

            # Simple Memory Leak Prevention:
            # If dictionary gets too large, perform cleanup to prevent OOM.
            if len(self.requests) > 10000:
                # Cleanup: Remove clients that haven't made a request within the window.
                # Since active_requests for each client might not be updated until they make a request,
                # we need to check the last timestamp in their list.
                # Note: This is an O(N) operation where N is number of clients.
                # It only runs when we hit the threshold.
                stale_ips = []
                for ip, timestamps in self.requests.items():
                    # If list is empty (shouldn't happen with logic above but possible)
                    # or if the most recent request is older than window
                    if not timestamps or (now - timestamps[-1] > self.window):
                        stale_ips.append(ip)

                for ip in stale_ips:
                    del self.requests[ip]

                # Fallback: If still too large (active attack with >10k distinct IPs),
                # we must clear to protect memory.
                if len(self.requests) > 10000:
                    self.requests.clear()

            self.requests[client_ip] = active_requests

        return await call_next(request)
