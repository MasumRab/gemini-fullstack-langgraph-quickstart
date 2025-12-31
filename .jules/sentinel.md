## 2025-02-18 - [Sentinel Initialization]
**Vulnerability:** N/A
**Learning:** Initialized security journal.
**Prevention:** N/A

## 2025-02-18 - [Shadowed Startup Validation]
**Vulnerability:** Duplicate `lifespan` function definitions in `backend/src/agent/app.py` caused the first definition (containing `check_env_strict()`) to be silently overwritten by the second one.
**Learning:** Python allows redefinition of functions in the same scope without warning, which can lead to critical initialization logic (like security checks) being skipped if they are split across multiple identically-named functions.
**Prevention:** Ensure a single `lifespan` context manager handles all startup/shutdown logic, or use a modular approach where multiple startup hooks are explicitly registered and aggregated.

## 2025-02-23 - [Missing API Rate Limiting]
**Vulnerability:** API endpoints (`/agent/*`, `/threads/*`) were unprotected against high-volume requests, exposing the backend to DoS attacks and potential LLM cost overruns.
**Learning:** While `RateLimiter` logic existed for outbound LLM calls, inbound API traffic was unrestricted. Security controls must be applied at both the edge (API) and the resource (LLM) layers.
**Prevention:** Implemented `RateLimitMiddleware` using a simple in-memory sliding window (requests per IP) and applied it to sensitive API routes, ensuring basic protection without adding complex dependencies.

## 2025-02-24 - [Proxy-Aware Rate Limiting]
**Vulnerability:** `RateLimitMiddleware` relied solely on `request.client.host`, which correctly identifies the client IP in direct connections but targets the Load Balancer (LB) IP when deployed behind a proxy (like Render). This could cause the LB to be rate-limited, blocking all legitimate traffic (DoS), or allow attackers to bypass limits by spoofing IPs if not carefully handled.
**Learning:** Deployment topology dictates how "client identity" is determined. Middleware must be "proxy-aware" but also "spoof-resistant" (e.g., verifying trusted proxies, though hard in simple setups).
**Prevention:** Enhanced `RateLimitMiddleware` to check `X-Forwarded-For` headers (common in LBs). Added input validation (truncation) on the header value to prevent memory exhaustion from maliciously large headers.
