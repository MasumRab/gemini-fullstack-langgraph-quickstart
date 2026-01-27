## 2024-05-23 - Rate Limit Bypass via X-Forwarded-For Spoofing
**Vulnerability:** The `RateLimitMiddleware` blindly trusted the `X-Forwarded-For` header to determine the client IP. An attacker could spoof this header to bypass rate limits when the application is deployed directly to the internet or behind a proxy that doesn't sanitize the header.
**Learning:** Middleware that relies on headers for security controls must verify the source of those headers. `X-Forwarded-For` should only be trusted if the request comes from a known trusted proxy.
**Prevention:** Explicitly configure a `TRUST_PROXY_HEADERS` setting (defaulting to False) and only parse the header when this setting is enabled.
