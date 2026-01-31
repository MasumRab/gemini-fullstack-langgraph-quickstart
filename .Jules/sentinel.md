# Sentinel's Journal

## 2026-01-31 - Blind Trust in X-Forwarded-For
**Vulnerability:** The `RateLimitMiddleware` blindly trusted the `X-Forwarded-For` header, allowing attackers to bypass rate limits by spoofing the header when the server is directly exposed.
**Learning:** Default configurations should always assume untrusted input. Trusting proxy headers must be an opt-in decision (`TRUST_PROXY_HEADERS`) to prevent IP spoofing in non-proxied environments.
**Prevention:** Gate access to `X-Forwarded-For` behind a configuration flag. Verify that the request actually comes from a trusted proxy before trusting the header, or at least require explicit opt-in.
