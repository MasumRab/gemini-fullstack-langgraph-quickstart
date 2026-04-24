[1mdiff --cc backend/src/agent/app.py[m
[1mindex c2e0e8d,984eb62..0000000[m
[1m--- a/backend/src/agent/app.py[m
[1m+++ b/backend/src/agent/app.py[m
[36m@@@ -26,7 -24,6 +26,10 @@@[m [mfrom config.validation import check_env[m
  [m
  logger = logging.getLogger(__name__)[m
  [m
[32m++<<<<<<< HEAD[m
[32m +[m
[32m++=======[m
[32m++>>>>>>> 2e98e37 (feat(security): add logging for rejected requests in middleware)[m
  # Define Middleware for Content Size Limit (Defense against DoS)[m
  class ContentSizeLimitMiddleware(BaseHTTPMiddleware):[m
      """Middleware to limit the size of the request body."""[m
[36m@@@ -42,24 -37,26 +45,42 @@@[m
              # 🛡️ Sentinel: Reject 'Transfer-Encoding: chunked' to prevent Content-Length bypass (Request Smuggling/DoS)[m
              transfer_encoding = request.headers.get("transfer-encoding", "").lower()[m
              if "chunked" in transfer_encoding:[m
[32m++<<<<<<< HEAD[m
[32m +                logger.warning("Request blocked: Chunked encoding not allowed")[m
[32m++=======[m
[32m+                 logger.warning("Rejected chunked transfer encoding (DoS protection)")[m
[32m++>>>>>>> 2e98e37 (feat(security): add logging for rejected requests in middleware)[m
                  return Response("Chunked encoding not allowed", status_code=411)[m
  [m
              content_length = request.headers.get("content-length")[m
              if not content_length:[m
                  # 🛡️ Sentinel: Enforce Content-Length for state-changing methods to prevent streaming DoS[m
[32m++<<<<<<< HEAD[m
[32m +                logger.warning("Request blocked: Content-Length required")[m
[32m++=======[m
[32m+                 logger.warning("Rejected request missing Content-Length (DoS protection)")[m
[32m++>>>>>>> 2e98e37 (feat(security): add logging for rejected requests in middleware)[m
                  return Response("Content-Length required", status_code=411)[m
  [m
              try:[m
                  # 🛡️ Sentinel: Prevent 500 crashes from malformed Content-Length headers[m
                  if int(content_length) > self.max_upload_size:[m
                      logger.warning([m
[32m++<<<<<<< HEAD[m
[32m +                        f"Request blocked: Request entity too large ({content_length} > {self.max_upload_size})"[m
[32m +                    )[m
[32m +                    return Response("Request entity too large", status_code=413)[m
[32m +            except ValueError:[m
[32m +                logger.warning("Request blocked: Invalid Content-Length")[m
[32m++=======[m
[32m+                         f"Rejected request with content length {content_length} > {self.max_upload_size}"[m
[32m+                     )[m
[32m+                     return Response("Request entity too large", status_code=413)[m
[32m+             except ValueError:[m
[32m+                 logger.warning([m
[32m+                     f"Rejected request with invalid content length: {content_length}"[m
[32m+                 )[m
[32m++>>>>>>> 2e98e37 (feat(security): add logging for rejected requests in middleware)[m
                  return Response("Invalid Content-Length", status_code=400)[m
          return await call_next(request)[m
  [m
[1mdiff --cc backend/src/agent/security.py[m
[1mindex 200c3b0,b783769..0000000[m
[1m--- a/backend/src/agent/security.py[m
[1m+++ b/backend/src/agent/security.py[m
[36m@@@ -2,156 -2,15 +2,162 @@@[m
  [m
  import ipaddress[m
  import logging[m
[32m++<<<<<<< HEAD[m
[32m +import math[m
[32m +import os[m
[32m++=======[m
[32m++>>>>>>> 2e98e37 (feat(security): add logging for rejected requests in middleware)[m
  import time[m
  from collections import defaultdict[m
[31m -from typing import List[m
[32m +from typing import List, Set[m
  [m
  from fastapi import Request, Response[m
[32m +from fastapi.responses import JSONResponse[m
  from starlette.middleware.base import BaseHTTPMiddleware[m
  [m
  logger = logging.getLogger(__name__)[m
  [m
[32m++<<<<<<< HEAD[m
[32m +# 🛡️ Sentinel: Configurable trusted proxy count for X-Forwarded-For extraction[m
[32m +# This should be set to the number of trusted proxies between the client and your server.[m
[32m +# For example, if you have a CDN + load balancer, set this to 2.[m
[32m +TRUSTED_PROXY_COUNT = int(os.getenv("TRUSTED_PROXY_COUNT", "0"))[m
[32m +[m
[32m +# 🛡️ Sentinel: Optional set of trusted proxy IP addresses[m
[32m +# If set, we iterate from right to left and skip these IPs to find the first untrusted IP.[m
[32m +# This is more flexible than TRUSTED_PROXY_COUNT but requires knowing proxy IPs.[m
[32m +# Format: comma-separated IPs or CIDR ranges, e.g., "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"[m
[32m +TRUSTED_PROXIES_ENV = os.getenv("TRUSTED_PROXIES", "")[m
[32m +TRUSTED_PROXIES: Set[str] = set()[m
[32m +if TRUSTED_PROXIES_ENV:[m
[32m +    TRUSTED_PROXIES = set([m
[32m +        ip.strip() for ip in TRUSTED_PROXIES_ENV.split(",") if ip.strip()[m
[32m +    )[m
[32m +[m
[32m +[m
[32m +def _is_ip_in_trusted_proxies(ip: str) -> bool:[m
[32m +    """Check if an IP address is in the trusted proxies set.[m
[32m +[m
[32m +    Supports both direct IP matching and CIDR range matching.[m
[32m +    """[m
[32m +    if not TRUSTED_PROXIES:[m
[32m +        return False[m
[32m +[m
[32m +    try:[m
[32m +        ip_obj = ipaddress.ip_address(ip.strip())[m
[32m +        for trusted in TRUSTED_PROXIES:[m
[32m +            trusted = trusted.strip()[m
[32m +            if "/" in trusted:[m
[32m +                # CIDR range[m
[32m +                try:[m
[32m +                    network = ipaddress.ip_network(trusted, strict=False)[m
[32m +                    if ip_obj in network:[m
[32m +                        return True[m
[32m +                except ValueError:[m
[32m +                    continue[m
[32m +            else:[m
[32m +                # Direct IP match[m
[32m +                try:[m
[32m +                    if ip_obj == ipaddress.ip_address(trusted):[m
[32m +                        return True[m
[32m +                except ValueError:[m
[32m +                    continue[m
[32m +        return False[m
[32m +    except ValueError:[m
[32m +        return False[m
[32m +[m
[32m +[m
[32m +def extract_client_ip_from_forwarded([m
[32m +    forwarded: str,[m
[32m +    trusted_proxy_count: int = TRUSTED_PROXY_COUNT,[m
[32m +    fallback_ip: str | None = None,[m
[32m +) -> str | None:[m
[32m +    """Extract the real client IP from X-Forwarded-For header using trust-bound extraction.[m
[32m +[m
[32m +    🛡️ Sentinel: This implements secure IP extraction to prevent IP spoofing attacks.[m
[32m +[m
[32m +    The X-Forwarded-For header format is: client, proxy1, proxy2, ...[m
[32m +    Each proxy appends its IP to the right. However, the leftmost IP is[m
[32m +    attacker-controllable if the request passed through an untrusted network.[m
[32m +[m
[32m +    Trust-bound extraction works by:[m
[32m +    1. If TRUSTED_PROXIES is configured: iterate from right to left, skip trusted[m
[32m +       proxy IPs, return the first untrusted IP.[m
[32m +    2. If only TRUSTED_PROXY_COUNT is set: pick ips[-(trusted_proxy_count + 1)].[m
[32m +[m
[32m +    Args:[m
[32m +        forwarded: The X-Forwarded-For header value.[m
[32m +        trusted_proxy_count: Number of trusted proxies between client and server.[m
[32m +        fallback_ip: IP to return if no valid candidate is found.[m
[32m +[m
[32m +    Returns:[m
[32m +        The extracted client IP, or fallback_ip if no valid candidate found.[m
[32m +    """[m
[32m +    if not forwarded:[m
[32m +        return fallback_ip[m
[32m +[m
[32m +    try:[m
[32m +        # Parse and validate all IPs in the chain[m
[32m +        ips = [][m
[32m +        for ip_str in forwarded.split(","):[m
[32m +            ip_str = ip_str.strip()[m
[32m +            if not ip_str:[m
[32m +                continue[m
[32m +            # Validate IP format[m
[32m +            try:[m
[32m +                ipaddress.ip_address(ip_str)[m
[32m +                ips.append(ip_str)[m
[32m +            except ValueError:[m
[32m +                # Invalid IP format, skip[m
[32m +                logger.warning(f"Invalid IP in X-Forwarded-For: {ip_str}")[m
[32m +                continue[m
[32m +[m
[32m +        if not ips:[m
[32m +            return fallback_ip[m
[32m +[m
[32m +        # Method 1: Use trusted proxies list if available (more flexible)[m
[32m +        if TRUSTED_PROXIES:[m
[32m +            # Iterate from right to left, skip trusted proxies[m
[32m +            for ip in reversed(ips):[m
[32m +                if not _is_ip_in_trusted_proxies(ip):[m
[32m +                    return ip[m
[32m +            # All IPs are trusted proxies, return the leftmost (original client)[m
[32m +            # This shouldn't happen in normal operation[m
[32m +            logger.warning([m
[32m +                "All IPs in X-Forwarded-For are trusted proxies, using leftmost"[m
[32m +            )[m
[32m +            return ips[0] if ips else fallback_ip[m
[32m +[m
[32m +        # Method 2: Use trusted proxy count[m
[32m +        if trusted_proxy_count > 0:[m
[32m +            # Pick ips[-(trusted_proxy_count + 1)][m
[32m +            # For example, if trusted_proxy_count=1 and ips=[client, proxy1],[m
[32m +            # we want ips[-2] = client[m
[32m +            idx = -(trusted_proxy_count + 1)[m
[32m +            if abs(idx) <= len(ips):[m
[32m +                return ips[idx][m
[32m +            else:[m
[32m +                # Not enough IPs in the chain, return leftmost[m
[32m +                logger.warning([m
[32m +                    f"Not enough IPs in X-Forwarded-For for trusted_proxy_count={trusted_proxy_count}, "[m
[32m +                    f"using leftmost IP"[m
[32m +                )[m
[32m +                return ips[0] if ips else fallback_ip[m
[32m +[m
[32m +        # No trusted proxies configured - return fallback for safety[m
[32m +        # This prevents IP spoofing when trust_proxy_headers is True but no proxies are configured[m
[32m +        logger.warning([m
[32m +            "X-Forwarded-For header present but no trusted proxies configured. "[m
[32m +            "Using fallback IP for security. Set TRUSTED_PROXY_COUNT or TRUSTED_PROXIES."[m
[32m +        )[m
[32m +        return fallback_ip[m
[32m +[m
[32m +    except Exception as e:[m
[32m +        logger.warning(f"Error parsing X-Forwarded-For header: {e}")[m
[32m +        return fallback_ip[m
[32m +[m
[32m++=======[m
[32m++>>>>>>> 2e98e37 (feat(security): add logging for rejected requests in middleware)[m
  [m
  class SecurityHeadersMiddleware(BaseHTTPMiddleware):[m
      """Middleware to add security headers to every response."""[m
[36m@@@ -295,19 -173,10 +301,26 @@@[m [mclass RateLimitMiddleware(BaseHTTPMiddl[m
              if len(active_requests) >= self.limit:[m
                  # Update map with pruned list before returning[m
                  self.requests[client_key] = active_requests[m
[32m++<<<<<<< HEAD[m
[32m +[m
[32m +                # Calculate retry_after[m
[32m +                oldest_request_time = active_requests[0][m
[32m +                reset_time = oldest_request_time + self.window[m
[32m +                retry_after = max(1, int(math.ceil(reset_time - now)))[m
[32m +[m
[32m +                logger.warning(f"Rate limit exceeded for {client_key} on {path}")[m
[32m +[m
[32m +                return JSONResponse([m
[32m +                    status_code=429,[m
[32m +                    content={"detail": "Too Many Requests", "retry_after": retry_after},[m
[32m +                    headers={"Retry-After": str(retry_after)},[m
[32m +                )[m
[32m++=======[m
[32m+                 logger.warning([m
[32m+                     f"Rate limit exceeded for client {client_key} on path {path}"[m
[32m+                 )[m
[32m+                 return Response("Too Many Requests", status_code=429)[m
[32m++>>>>>>> 2e98e37 (feat(security): add logging for rejected requests in middleware)[m
  [m
              active_requests.append(now)[m
  [m
[1mdiff --cc backend/tests/test_security_logging.py[m
[1mindex 01bf369,370d006..0000000[m
[1m--- a/backend/tests/test_security_logging.py[m
[1m+++ b/backend/tests/test_security_logging.py[m
[36m@@@ -1,79 -1,54 +1,136 @@@[m
[32m++<<<<<<< HEAD[m
[32m +import logging[m
[32m +[m
[32m +import pytest[m
[32m +from fastapi import FastAPI[m
[32m +from fastapi.testclient import TestClient[m
[32m +[m
[32m +from agent.app import ContentSizeLimitMiddleware[m
[32m +from agent.mcp_server import FilesystemMCPServer[m
[32m +from agent.security import RateLimitMiddleware[m
[32m +[m
[32m +[m
[32m +# Setup simple app for middleware testing[m
[32m +def create_rate_limit_app():[m
[32m +    app = FastAPI()[m
[32m +    app.add_middleware(RateLimitMiddleware, limit=1, window=60, protected_paths=["/test"])[m
[32m +[m
[32m +    @app.get("/test")[m
[32m +    def test_route():[m
[32m +        return {"message": "ok"}[m
[32m +[m
[32m +    return app[m
[32m +[m
[32m +def create_content_size_app():[m
[32m +    app = FastAPI()[m
[32m +    app.add_middleware(ContentSizeLimitMiddleware, max_upload_size=10) # Small limit for testing[m
[32m +[m
[32m +    @app.post("/upload")[m
[32m +    def upload_route(data: dict):[m
[32m +        return {"message": "uploaded"}[m
[32m +[m
[32m +    return app[m
[32m +[m
[32m +class TestSecurityLogging:[m
[32m +[m
[32m +    def test_rate_limit_logging(self, caplog):[m
[32m +        """Test that rate limit violations are logged with path."""[m
[32m +        app = create_rate_limit_app()[m
[32m +        client = TestClient(app)[m
[32m +[m
[32m +        # First request ok[m
[32m +        client.get("/test")[m
[32m +[m
[32m +        # Second request blocked[m
[32m +        with caplog.at_level(logging.WARNING):[m
[32m +            client.get("/test")[m
[32m +[m
[32m +        # Check logs[m
[32m +        assert "Rate limit exceeded" in caplog.text[m
[32m +        # We expect the path to be in the log now (failing initially)[m
[32m +        assert "/test" in caplog.text[m
[32m +[m
[32m +    def test_content_size_logging(self, caplog):[m
[32m +        """Test that content size violations are logged."""[m
[32m +        app = create_content_size_app()[m
[32m +        client = TestClient(app)[m
[32m +[m
[32m +        # Large payload[m
[32m +        large_data = "x" * 20[m
[32m +[m
[32m +        with caplog.at_level(logging.WARNING):[m
[32m +            client.post("/upload", content=large_data, headers={"Content-Length": str(len(large_data))})[m
[32m +[m
[32m +        # Check logs[m
[32m +        assert "Request entity too large" in caplog.text[m
[32m +[m
[32m +    @pytest.mark.asyncio[m
[32m +    async def test_mcp_path_traversal_logging(self, caplog, tmp_path):[m
[32m +        """Test that MCP path traversal attempts are logged."""[m
[32m +        server = FilesystemMCPServer([str(tmp_path)])[m
[32m +[m
[32m +        # Attempt traversal[m
[32m +        bad_path = str(tmp_path / "../outside.txt")[m
[32m +[m
[32m +        with caplog.at_level(logging.WARNING):[m
[32m +            await server.read_file(bad_path)[m
[32m +[m
[32m +        # Check logs[m
[32m +        assert "Path traversal attempt blocked" in caplog.text[m
[32m +        assert bad_path in caplog.text[m
[32m++=======[m
[32m+ import pytest[m
[32m+ import logging[m
[32m+ from unittest.mock import MagicMock, AsyncMock[m
[32m+ from agent.security import RateLimitMiddleware[m
[32m+ from agent.app import ContentSizeLimitMiddleware[m
[32m+ [m
[32m+ @pytest.mark.asyncio[m
[32m+ async def test_rate_limit_logging(caplog):[m
[32m+     app = AsyncMock()[m
[32m+     # Limit 0 to fail immediately[m
[32m+     mw = RateLimitMiddleware(app, limit=0, window=60, protected_paths=["/api"])[m
[32m+ [m
[32m+     req = MagicMock()[m
[32m+     req.url.path = "/api/test"[m
[32m+     req.client.host = "1.2.3.4"[m
[32m+     req.headers.get.return_value = None # No X-Forwarded-For[m
[32m+ [m
[32m+     async def call_next(request):[m
[32m+         return "success"[m
[32m+ [m
[32m+     # Capture logs[m
[32m+     with caplog.at_level(logging.WARNING):[m
[32m+         response = await mw.dispatch(req, call_next)[m
[32m+ [m
[32m+     assert response.status_code == 429[m
[32m+ [m
[32m+     # Assert log message - specific messages will be added in implementation[m
[32m+     # We expect some log containing "Rate limit" and the IP[m
[32m+     log_text = caplog.text[m
[32m+     assert "Rate limit" in log_text or "Too Many Requests" in log_text[m
[32m+     assert "1.2.3.4" in log_text[m
[32m+     assert "/api/test" in log_text[m
[32m+ [m
[32m+ @pytest.mark.asyncio[m
[32m+ async def test_content_size_limit_logging(caplog):[m
[32m+     app = AsyncMock()[m
[32m+     mw = ContentSizeLimitMiddleware(app, max_upload_size=100)[m
[32m+ [m
[32m+     req = MagicMock()[m
[32m+     req.method = "POST"[m
[32m+     req.headers = {[m
[32m+         "content-length": "200" # Exceeds 100[m
[32m+     }[m
[32m+ [m
[32m+     async def call_next(request):[m
[32m+         return "success"[m
[32m+ [m
[32m+     with caplog.at_level(logging.WARNING):[m
[32m+         response = await mw.dispatch(req, call_next)[m
[32m+ [m
[32m+     assert response.status_code == 413[m
[32m+ [m
[32m+     log_text = caplog.text[m
[32m+     assert "Rejected request with content length" in log_text[m
[32m++>>>>>>> 2e98e37 (feat(security): add logging for rejected requests in middleware)[m
