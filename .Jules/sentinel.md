## 2025-05-23 - Rate Limit Bypass via X-Forwarded-For
**Vulnerability:** The `RateLimitMiddleware` blindly trusted the `X-Forwarded-For` header, allowing attackers to bypass rate limits by spoofing random IPs in this header.
**Learning:** Middleware often defaults to "dev-friendly" (trusting headers) which is insecure for production. Implicit trust in headers creates silent vulnerabilities.
**Prevention:** Always default to NOT trusting `X-Forwarded-For`. Require explicit configuration (`TRUST_PROXY_HEADERS`) to enable it.
