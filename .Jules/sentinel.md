## 2025-02-18 - Rate Limit IP Spoofing Vulnerability
**Vulnerability:** The `RateLimitMiddleware` implicitly trusted the `X-Forwarded-For` header, allowing direct attackers to spoof their IP address and bypass rate limits by injecting a fake header.
**Learning:** Default middleware configurations often assume a trusted proxy environment (like Render/Heroku). In mixed or direct deployments, this assumption leads to security gaps.
**Prevention:** Always gate `X-Forwarded-For` trust behind an explicit configuration flag (e.g., `TRUST_PROXY_HEADERS`). Default this flag to `False` (secure by default).
