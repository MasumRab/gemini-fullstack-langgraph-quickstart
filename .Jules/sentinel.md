## 2024-05-22 - Blind Trust of X-Forwarded-For Header
**Vulnerability:** The `RateLimitMiddleware` blindly accepted the `X-Forwarded-For` header to determine the client IP address.
**Learning:** Custom middleware often reimplements logic (like proxy header parsing) that frameworks usually handle, but without the necessary configuration flags (like "trust proxy"). This allows attackers to spoof their IP address and bypass rate limits or IP-based restrictions.
**Prevention:** Always gate proxy header parsing behind an explicit configuration flag (e.g., `TRUST_PROXY_HEADERS`). Default to secure (false) and require operators to opt-in when they know they are behind a trusted proxy.
