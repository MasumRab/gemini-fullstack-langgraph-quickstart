## 2025-02-18 - Rate Limit IP Spoofing Vulnerability
**Vulnerability:** The `RateLimitMiddleware` implicitly trusted the `X-Forwarded-For` header, allowing direct attackers to spoof their IP address and bypass rate limits by injecting a fake header.
**Learning:** Default middleware configurations often assume a trusted proxy environment (like Render/Heroku). In mixed or direct deployments, this assumption leads to security gaps.
**Prevention:** Always gate `X-Forwarded-For` trust behind an explicit configuration flag (e.g., `TRUST_PROXY_HEADERS`). Default this flag to `False` (secure by default).

## 2025-02-19 - IP Spoofing via Trusted Proxy Traversal
**Vulnerability:** Even with `trust_proxy_headers=True`, the middleware logic searched backwards for the first "Public" IP to identify the client. This allowed attackers to spoof a public IP (e.g., `8.8.8.8`) at the start of the header, which would be prioritized over a legitimate Private IP (e.g., VPN user `10.0.0.5`) if the real client was on a private network.
**Learning:** "Public vs Private" IP classification is a dangerous heuristic for client identification when the network topology includes private subnets (VPNs, Intranets).
**Prevention:** When trusting proxies, rely on the chain of trust (the last IP appended by the trusted proxy) rather than guessing based on IP class.

## 2025-05-23 - Rate Limit Bypass via X-Forwarded-For
**Vulnerability:** The `RateLimitMiddleware` blindly trusted the `X-Forwarded-For` header, allowing attackers to bypass rate limits by spoofing random IPs in this header.
**Learning:** Middleware often defaults to "dev-friendly" (trusting headers) which is insecure for production. Implicit trust in headers creates silent vulnerabilities.
**Prevention:** Always default to NOT trusting `X-Forwarded-For`. Require explicit configuration (`TRUST_PROXY_HEADERS`) to enable it.

## 2026-01-25 - [HIGH] XSS Defense in Depth via Sanitization
**Vulnerability:** The ChatMessagesView component rendered Markdown content using `ReactMarkdown` without explicit HTML sanitization (`rehype-sanitize`). While `ReactMarkdown` v9+ is safe by default, adding plugins or future configuration changes could introduce Stored XSS vulnerabilities.
**Learning:** Security tools often require careful configuration to avoid breaking functionality. Default sanitization schemas can be too aggressive, stripping attributes needed for styling (like `className` for code highlighting or `align` for GFM tables).
**Prevention:** Always include `rehype-sanitize` when rendering user content. Explicitly configure the schema to allow necessary safe attributes (e.g., `className` on `code` blocks) to balance security and functionality.
