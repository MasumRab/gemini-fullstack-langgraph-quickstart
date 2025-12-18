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

        # Basic HSTS (1 year) - good for production, usually safe for dev too
        # response.headers["Strict-Transport-Security"] = (
        #     "max-age=31536000; includeSubDomains"
        # )

        return response
