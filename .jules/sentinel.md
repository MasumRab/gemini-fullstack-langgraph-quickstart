# Sentinel's Journal

## 2025-02-24 - [Rate Limit Bypass via Spoofing]
**Vulnerability:** `RateLimitMiddleware` used the *first* IP in `X-Forwarded-For` (`split(",")[0]`). Attackers can trivially spoof this by sending `X-Forwarded-For: fake_ip`. The trusted proxy (Render) appends the real IP to the end, but the middleware ignored it, allowing attackers to bypass rate limits by rotating the fake IP.
**Learning:** In standard proxy setups (like Render), `X-Forwarded-For` is `client, proxy1, proxy2`. The *last* IP is the one added by the immediate upstream (Render) and is the only one we can implicitly trust without a strict IP whitelist.
**Prevention:** Changed logic to use `split(",")[-1]` (the last IP). This ensures we rate limit based on the IP verified by our infrastructure, not the one claimed by the user.

## 2025-02-23 - [Proxy-Unaware Rate Limiting]
**Vulnerability:** `RateLimitMiddleware` relied solely on `request.client.host`, which resolves to the Load Balancer/Proxy IP in deployed environments (e.g., Render), effectively sharing a single rate limit quota across all users.
**Learning:** Middleware operating in cloud environments must account for reverse proxies. Trusting the direct connection IP causes "deny all" outages when traffic scales.
**Prevention:** Updated middleware to prioritize the `X-Forwarded-For` header, extracting the first IP (real client) and truncating it to prevent memory exhaustion.

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

## 2025-02-24 - [Content-Length Bypass Mitigation]
**Vulnerability:** `ContentSizeLimitMiddleware` relied solely on `Content-Length` header, which can be bypassed using `Transfer-Encoding: chunked`. Attackers could send infinite streams (DoS) or smuggle requests past the size limit.
**Learning:** Middleware relying on `Content-Length` must explicitly handle or reject `Transfer-Encoding: chunked` if it doesn't support stream inspection. WAFs/Proxies often treat these differently, leading to "smuggling" gaps.
**Prevention:** Updated `ContentSizeLimitMiddleware` to explicitly reject requests with `Transfer-Encoding: chunked` (HTTP 411/400), ensuring strictly defined content lengths for API security. Also fixed bare `except:` blocks in `tool_adapter.py` to prevent masking of system errors.

## 2025-02-24 - [Deep Recursion DoS]
**Vulnerability:** The `InvokeRequest` input validation was vulnerable to deeply nested JSON payloads (`RecursionError`). Furthermore, the default FastAPI error handler crashed when attempting to serialize these deeply nested inputs back to the client, resulting in a 500 error instead of a 422.
**Learning:** Validating input structure is not enough if the error reporting mechanism itself is vulnerable to the same structure. Deeply nested objects can crash serializers (like `jsonable_encoder`) even after validation fails.
**Prevention:** Implemented a `validate_input_complexity` validator (checking depth and total size) AND a custom `RequestValidationError` handler that strips the `input` field from the error response to prevent serialization crashes.
