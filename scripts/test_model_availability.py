
import os
import sys
from langchain_google_genai import ChatGoogleGenerativeAI
from google.api_core.exceptions import NotFound, ResourceExhausted, InvalidArgument

def test_model(model_name):
    print(f"\n--- Testing Model: {model_name} ---")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in environment variables.")
        return

    try:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0,
            google_api_key=api_key
        )
        response = llm.invoke("Hello, are you standard Gemini 1.5 or the new Gemini 2.5? Reply with your version.")
        print(f"✅ Success! Response: {response.content}")
        return True
    except NotFound:
        print(f"❌ Error: Model '{model_name}' not found (404). It might not exist or your API key lacks access.")
    except ResourceExhausted:
        print(f"⚠️ Warning: Model '{model_name}' exists but quota is exhausted (429).")
        return True # It exists!
    except InvalidArgument as e:
        print(f"❌ Error: Invalid Argument: {e}")
    except Exception as e:
        print(f"❌ Error: Unexpected error: {e}")
    return False

if __name__ == "__main__":
    print(f"Python Version: {sys.version}")
    # Force load .env if present
    from dotenv import load_dotenv
    load_dotenv()
    
    # Add backend/src to path for imports
    backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    try:
        from agent.models import GEMINI_FLASH, GEMINI_PRO, GEMINI_FLASH_LITE
        models_to_test = [GEMINI_FLASH, GEMINI_PRO, GEMINI_FLASH_LITE]
    except ImportError:
        print("Could not import agent.models, using defaults")
        models_to_test = [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
        ]
    
    results = {}
    for model in models_to_test:
        results[model] = test_model(model)
        
    print("\n\n=== Final Summary ===")
    for model, exists in results.items():
        status = "AVAILABLE" if exists else "UNAVAILABLE"
        print(f"{model}: {status}")
