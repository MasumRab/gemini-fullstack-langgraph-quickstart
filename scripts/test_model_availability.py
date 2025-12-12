
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

    models_to_test = [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash-exp",
        "gemini-1.5-flash"
    ]

    results = {}
    for model in models_to_test:
        results[model] = test_model(model)

    print("\n\n=== Final Summary ===")
    for model, exists in results.items():
        status = "AVAILABLE" if exists else "UNAVAILABLE"
        print(f"{model}: {status}")
