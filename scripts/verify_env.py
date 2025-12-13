print("Hello from Python")
import sys
print(sys.executable)
try:
    import google.generativeai
    print("google.generativeai OK")
except ImportError as e:
    print(f"google.generativeai MISSING: {e}")

try:
    import langchain_google_genai
    print("langchain_google_genai OK")
except ImportError as e:
    print(f"langchain_google_genai MISSING: {e}")
