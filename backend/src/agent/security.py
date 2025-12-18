"""Security middleware for the agent application."""

from fastapi import Request
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

        # Content Security Policy (CSP)
        # Default to very strict (API only), but allow styles/images if needed for simple UI
        # Since this is primarily an API backend, we start strict.
        # Note: If serving a frontend from this backend, this might need adjustment.
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

        # Basic HSTS (1 year) - good for production, usually safe for dev too
        # response.headers["Strict-Transport-Security"] = (
        #     "max-age=31536000; includeSubDomains"
        # )

        return response
