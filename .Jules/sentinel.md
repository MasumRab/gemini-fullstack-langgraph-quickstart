## 2025-02-18 - Rate Limit IP Spoofing Vulnerability
**Vulnerability:** The `RateLimitMiddleware` implicitly trusted the `X-Forwarded-For` header, allowing direct attackers to spoof their IP address and bypass rate limits by injecting a fake header.
**Learning:** Default middleware configurations often assume a trusted proxy environment (like Render/Heroku). In mixed or direct deployments, this assumption leads to security gaps.
**Prevention:** Always gate `X-Forwarded-For` trust behind an explicit configuration flag (e.g., `TRUST_PROXY_HEADERS`). Default this flag to `False` (secure by default).

## 2025-02-19 - IP Spoofing via Trusted Proxy Traversal
**Vulnerability:** Even with `trust_proxy_headers=True`, the middleware logic searched backwards for the first "Public" IP to identify the client. This allowed attackers to spoof a public IP (e.g., `8.8.8.8`) at the start of the header, which would be prioritized over a legitimate Private IP (e.g., VPN user `10.0.0.5`) if the real client was on a private network.
**Learning:** "Public vs Private" IP classification is a dangerous heuristic for client identification when the network topology includes private subnets (VPNs, Intranets).
**Prevention:** When trusting proxies, rely on the chain of trust (the last IP appended by the trusted proxy) rather than guessing based on IP class.
