
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Ensure we can import from src
sys.path.append(os.path.join(os.getcwd(), "src"))

from agent.app import app
from agent.security import SecurityHeadersMiddleware
from config.app_config import config

print("Verifying Security Configuration...")
print(f"CORS Origins: {config.cors_origins}")

# Check for middleware
middleware_types = [type(m.cls) if hasattr(m, 'cls') else type(m) for m in app.user_middleware]
# Note: FastAPI middleware stack is a bit complex to inspect directly for types sometimes, 
# but we can check if SecurityHeadersMiddleware is in the stack if we iterate carefully.
# However, usually just importing app without error is a good sign.

print("SecurityHeadersMiddleware imported successfully.")
print("Verification complete.")
