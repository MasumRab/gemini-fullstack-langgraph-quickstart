"""Security middleware for the agent application."""

import ipaddress
import logging
import math
import os
import time
from collections import defaultdict
from typing import List, Optional, Set

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# 🛡️ Sentinel: Configurable trusted proxy count for X-Forwarded-For extraction
# This should be set to the number of trusted proxies between the client and your server.
# For example, if you have a CDN + load balancer, set this to 2.
def _parse_int_env(env_var: str, default: int = 0) -> int:
    """Safely parse an integer environment variable.
    
    Args:
        env_var: The name of the environment variable.
        default: The default value if parsing fails or variable is not set.
    
    Returns:
        The parsed integer value, or default on failure.
    """
    value = os.getenv(env_var)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(
            f"Invalid integer value for {env_var}: '{value}', defaulting to {default}"
        )
        return default

TRUSTED_PROXY_COUNT = _parse_int_env("TRUSTED_PROXY_COUNT", 0)

# 🛡️ Sentinel: Optional set of trusted proxy IP addresses
# If set, we iterate from right to left and skip these IPs to find the first untrusted IP.
# This is more flexible than TRUSTED_PROXY_COUNT but requires knowing proxy IPs.
# Format: comma-separated IPs or CIDR ranges, e.g., "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
TRUSTED_PROXIES_ENV = os.getenv("TRUSTED_PROXIES", "")
TRUSTED_PROXIES: Set[str] = set()
if TRUSTED_PROXIES_ENV:
    TRUSTED_PROXIES = set(ip.strip() for ip in TRUSTED_PROXIES_ENV.split(",") if ip.strip())


def _is_ip_in_trusted_proxies(ip: str) -> bool:
    """Check if an IP address is in the trusted proxies set.
    
    Supports both direct IP matching and CIDR range matching.
    """
    if not TRUSTED_PROXIES:
        return False
    
    try:
        ip_obj = ipaddress.ip_address(ip.strip())
        for trusted in TRUSTED_PROXIES:
            trusted = trusted.strip()
            if "/" in trusted:
                # CIDR range
                try:
                    network = ipaddress.ip_network(trusted, strict=False)
                    if ip_obj in network:
                        return True
                except ValueError:
                    continue
            else:
                # Direct IP match
                try:
                    if ip_obj == ipaddress.ip_address(trusted):
                        return True
                except ValueError:
                    continue
        return False
    except ValueError:
        return False


def extract_client_ip_from_forwarded(
    forwarded: str, 
    trusted_proxy_count: int = TRUSTED_PROXY_COUNT,
    fallback_ip: Optional[str] = None
) -> Optional[str]:
    """Extract the real client IP from X-Forwarded-For header using trust-bound extraction.
    
    🛡️ Sentinel: This implements secure IP extraction to prevent IP spoofing attacks.
    
    The X-Forwarded-For header format is: client, proxy1, proxy2, ...
    Each proxy appends its IP to the right. However, the leftmost IP is 
    attacker-controllable if the request passed through an untrusted network.
    
    Trust-bound extraction works by:
    1. If TRUSTED_PROXIES is configured: iterate from right to left, skip trusted 
       proxy IPs, return the first untrusted IP.
    2. If only TRUSTED_PROXY_COUNT is set: pick ips[-(trusted_proxy_count + 1)].
    
    Args:
        forwarded: The X-Forwarded-For header value.
        trusted_proxy_count: Number of trusted proxies between client and server.
        fallback_ip: IP to return if no valid candidate is found.
    
    Returns:
        The extracted client IP, or fallback_ip if no valid candidate found.
    """
    if not forwarded:
        return fallback_ip
    
    try:
        # Parse and validate all IPs in the chain
        ips = []
        for ip_str in forwarded.split(","):
            ip_str = ip_str.strip()
            if not ip_str:
                continue
            # Validate IP format
            try:
                ipaddress.ip_address(ip_str)
                ips.append(ip_str)
            except ValueError:
                # Invalid IP format, skip
                logger.warning(f"Invalid IP in X-Forwarded-For: {ip_str}")
                continue
        
        if not ips:
            return fallback_ip
        
        # Method 1: Use trusted proxies list if available (more flexible)
        if TRUSTED_PROXIES:
            # Iterate from right to left, skip trusted proxies
            for ip in reversed(ips):
                if not _is_ip_in_trusted_proxies(ip):
                    return ip
            # All IPs are trusted proxies - this shouldn't happen in normal operation.
            # Return fallback_ip for safety since ips[0] is attacker-controllable.
            logger.error(
                f"All IPs in X-Forwarded-For matched trusted proxies (ips={ips}), "
                f"using safe fallback (fallback_ip={fallback_ip})"
            )
            return fallback_ip
        
        # Method 2: Use trusted proxy count
        if trusted_proxy_count > 0:
            # Pick ips[-(trusted_proxy_count + 1)]
            # For example, if trusted_proxy_count=1 and ips=[client, proxy1],
            # we want ips[-2] = client
            idx = -(trusted_proxy_count + 1)
            if abs(idx) <= len(ips):
                return ips[idx]
            else:
                # Not enough IPs in the chain, return leftmost
                logger.warning(
                    f"Not enough IPs in X-Forwarded-For for trusted_proxy_count={trusted_proxy_count}, "
                    f"using leftmost IP"
                )
                return ips[0] if ips else fallback_ip
        
        # No trusted proxies configured - return fallback for safety
        # This prevents IP spoofing when trust_proxy_headers is True but no proxies are configured
        logger.warning(
            "X-Forwarded-For header present but no trusted proxies configured. "
            "Using fallback IP for security. Set TRUSTED_PROXY_COUNT or TRUSTED_PROXIES."
        )
        return fallback_ip
        
    except Exception as e:
        logger.warning(f"Error parsing X-Forwarded-For header: {e}")
        return fallback_ip


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
            # If not a valid IP, return "unknown" to prevent log injection/key pollution
            return "unknown"

    def __init__(
        self,
        app,
        limit: int = 100,
        window: int = 60,
        protected_paths: List[str] | None = None,
        trust_proxy_headers: bool = False,
    ):
        """Initialize the rate limiter.

        Args:
            app: The FastAPI application.
            limit: Maximum requests allowed per window.
            window: Time window in seconds.
            protected_paths: List of path prefixes to apply rate limiting to.
                             If None, applies to all paths.
            trust_proxy_headers: Whether to trust X-Forwarded-For headers.
        """
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.protected_paths = protected_paths if protected_paths is not None else []
        self.trust_proxy_headers = trust_proxy_headers
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
            # Use trust-bound extraction to prevent IP spoofing attacks.
            forwarded = request.headers.get("X-Forwarded-For")
            fallback_ip = request.client.host if request.client else "unknown"
            
            if forwarded and self.trust_proxy_headers:
                # 🛡️ Sentinel: Use trust-bound IP extraction instead of naive ips[0]
                # The leftmost IP is attacker-controllable; we must use trust-bound extraction.
                client_ip = extract_client_ip_from_forwarded(
                    forwarded=forwarded,
                    fallback_ip=fallback_ip
                )
                if client_ip is None:
                    client_ip = fallback_ip
                    
                # Truncate to 100 chars to prevent memory exhaustion attacks
                client_ip = client_ip[:100]
            else:
                client_ip = fallback_ip

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

                # Calculate retry_after
                oldest_request_time = active_requests[0]
                reset_time = oldest_request_time + self.window
                retry_after = max(1, int(math.ceil(reset_time - now)))

                logger.warning(f"Rate limit exceeded for {client_key} on {path}")

                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too Many Requests", "retry_after": retry_after},
                    headers={"Retry-After": str(retry_after)},
                )

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
                    return Response("Server Busy", status_code=503)

            self.requests[client_key] = active_requests

        return await call_next(request)
