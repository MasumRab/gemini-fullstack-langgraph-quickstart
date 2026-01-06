
import asyncio
import sys
import json
from pathlib import Path
# Add backend/src to path
sys.path.append(str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from agent.app import InvokeRequest
from pydantic import ValidationError

def verify_input_limit():
    print("Verify: Checking input length validation...")

    # Create a massive string (100k chars)
    massive_string = "a" * 100000

    try:
        req = InvokeRequest(
            input={"search_query": massive_string},
            config={}
        )
        print("FAILED: InvokeRequest accepted 100k char input.")
        print("⚠️ VULNERABILITY: Input length not restricted.")
    except ValidationError as e:
        print("SUCCESS: InvokeRequest rejected large input.")
        print(f"Error: {e}")
        print("✅ Secure: Input length limited.")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    verify_input_limit()
