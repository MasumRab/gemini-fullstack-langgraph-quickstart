import re

with open('backend/src/agent/security.py', 'r') as f:
    content = f.read()

# Fix RateLimitMiddleware to use the last IP in X-Forwarded-For per the memory prompt and test requirements
fix = """            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded and self.trust_proxy_headers:
                # 🛡️ Sentinel: The rightmost IP (ips[-1]) is the original client IP as appended by the nearest trusted proxy.
                # Attackers can spoof ips[0], so we trust the last IP added by our infrastructure.
                try:
                    ips = [ip.strip() for ip in forwarded.split(",")]
                    client_ip = ips[-1]  # IP appended by the trusted proxy (rightmost)
                except Exception:
                    # Fallback to simple extraction if parsing fails
                    client_ip = forwarded.split(",")[-1].strip()

                # Truncate to 100 chars to prevent memory exhaustion attacks
                client_ip = client_ip[:100]"""

content = re.sub(r'            forwarded = request\.headers\.get\("X-Forwarded-For"\).*?client_ip = client_ip\[:100\]', fix, content, flags=re.DOTALL)

with open('backend/src/agent/security.py', 'w') as f:
    f.write(content)
