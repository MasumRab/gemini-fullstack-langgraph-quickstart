"""Security middleware for the agent application."""

import ipaddress
import logging
import time
from collections import defaultdict
from typing import List

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


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
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # Permissions Policy
        # Restrict access to sensitive features the agent doesn't need
        response.headers["Permissions-Policy"] = (
            "geolocation=(), camera=(), microphone=(), payment=(), usb=()"
        )

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

    def get_client_key(self, ip: str) -> str:
        """Normalize IP address to a rate limit key.

        For IPv4, returns the IP.
        For IPv6, returns the /64 prefix to prevent subnet rotation attacks.
        """
        try:
            obj = ipaddress.ip_address(ip)
            if isinstance(obj, ipaddress.IPv6Address):
                # Mask to /64
                val = int(obj)
                mask = (1 << 128) - (1 << 64)
                masked = val & mask
                return str(ipaddress.IPv6Address(masked)) + "/64"
            return str(obj)
        except ValueError:
            # If not a valid IP, just return as is (could be "unknown" or malformed)
            return ip

    def __init__(
        self,
        app,
        limit: int = 100,
        window: int = 60,
        protected_paths: List[str] | None = None,
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
        # 🛡️ Sentinel: Optimize cleanup frequency to prevent DoS via Iteration attacks
        self.last_cleanup = 0
        self.cleanup_interval = 60  # seconds

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
            # 🛡️ Sentinel: Support X-Forwarded-For for proxies (Render/Load Balancers)
            # Prioritize X-Forwarded-For to correctly identify clients behind load balancers.
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                # 🛡️ Sentinel: Prevent spoofing by traversing from the end (trusted proxies)
                # Proxies (like Render) append the verified client IP to the end.
                # We traverse backwards to find the first non-private IP to avoid blocking the proxy itself.
                try:
                    ips = [ip.strip() for ip in forwarded.split(",")]
                    client_ip = ips[-1]  # Default to last IP
                    for ip in reversed(ips):
                        try:
                            # Check if IP is public (not private, not loopback)
                            ip_obj = ipaddress.ip_address(ip)
                            if not ip_obj.is_private and not ip_obj.is_loopback:
                                client_ip = ip
                                break
                        except ValueError:
                            continue  # Skip invalid IPs
                except Exception:
                    # Fallback to simple extraction if parsing fails
                    client_ip = forwarded.split(",")[-1].strip()

                # Truncate to 100 chars to prevent memory exhaustion attacks
                client_ip = client_ip[:100]
            else:
                client_ip = request.client.host if request.client else "unknown"

            # 🛡️ Sentinel: Group IPv6 addresses by /64 prefix to prevent subnet rotation attacks
            client_key = self.get_client_key(client_ip)

            now = time.time()

            # Clean old requests (simple sliding window)
            current_requests = self.requests[client_key]
            # Prune old timestamps
            active_requests = [t for t in current_requests if now - t < self.window]

            if len(active_requests) >= self.limit:
                # Update map with pruned list before returning
                self.requests[client_key] = active_requests
                logger.warning(f"Rate limit exceeded for {client_key} on {path}")
                return Response("Too Many Requests", status_code=429)

            active_requests.append(now)

            # Simple Memory Leak Prevention:
            # If dictionary gets too large, perform cleanup to prevent OOM.
            # 🛡️ Sentinel: Throttle cleanup to prevent CPU exhaustion (DoS) via O(N) loop
            if now - self.last_cleanup > self.cleanup_interval:
                self.last_cleanup = now
                # Cleanup: Remove clients that haven't made a request within the window.
                # Since active_requests for each client might not be updated until they make a request,
                # we need to check the last timestamp in their list.
                # Note: This is an O(N) operation where N is number of clients.
                if len(self.requests) > 10000:
                    stale_ips = []
                    for ip, timestamps in self.requests.items():
                        # If list is empty (shouldn't happen with logic above but possible)
                        # or if the most recent request is older than window
                        if not timestamps or (now - timestamps[-1] > self.window):
                            stale_ips.append(ip)

                    for ip in stale_ips:
                        del self.requests[ip]

            # Fallback: If still too large (active attack with >10k distinct IPs),
            # 🛡️ Sentinel: Do NOT clear everything, as that allows attackers to reset everyone's limit.
            # Instead, if we are full, REJECT new clients.
            if len(self.requests) > 10000:
                # If the client is already known, we updated them above.
                # But wait, if we are > 10000, and this is a NEW client_ip (or one that was just added),
                # we should remove it and block.
                # However, we already added `now` to `active_requests` and set `self.requests[client_ip]`.

                # We need to check if we just added a NEW key that pushed us over.
                # If client_ip was already in requests, we are fine (we are just updating an existing slot).
                # If client_ip is NEW, and size > 10000, we should reject.

                # Optimization: Move the check BEFORE adding to `self.requests`.
                # But we used `defaultdict`, so accessing `self.requests[client_ip]` already created the entry if missing.

                # So, if we are over limit:
                # Check if we should allow this IP.
                # If we just created it (len=1), delete it and 503.
                if (
                    len(active_requests) == 1
                ):  # This was a new entry (or re-entry after expiry)
                    # Safe delete using pop to avoid KeyErrors in race conditions
                    self.requests.pop(client_key, None)
                    logger.warning(
                        f"Server busy (max clients): rejected new client {client_key} on {path}"
                    )
                    return Response("Server Busy", status_code=503)

            self.requests[client_key] = active_requests

        return await call_next(request)
