## 2025-05-24 - Rate Limit Proxy Vulnerability
**Vulnerability:** The `RateLimitMiddleware` used `request.client.host` to identify clients. On platforms like Render, this resolves to the internal proxy IP (e.g., `10.x.x.x`), causing all users to share the same rate limit bucket. This meant a single active user could exhaust the quota for the entire platform.
**Learning:** Cloud deployment environments (Render, AWS, Heroku) terminate SSL and forward traffic, obscuring the original client IP. Middleware must explicitly handle `X-Forwarded-For` to function correctly.
**Prevention:** Always check `X-Forwarded-For` headers in middleware when deploying behind load balancers. Implemented a truncation safety check (100 chars) to prevent memory exhaustion attacks from spoofed long headers.
