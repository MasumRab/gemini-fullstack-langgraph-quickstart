
import os
import sys

# Try imports
try:
    from google import genai
    NEW_SDK = True
except ImportError:
    NEW_SDK = False

try:
    import google.generativeai as old_genai
    OLD_SDK = True
except ImportError:
    OLD_SDK = False

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None
    print("❌ Error: langchain_google_genai not installed.")

from google.api_core.exceptions import NotFound, ResourceExhausted, InvalidArgument

def list_all_models():
    print("\n--- Listing All Available Models ---")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found.")
        return []

    gemma_models = []
    
    # Try New SDK
    if NEW_SDK:
        print("Using google.genai (New SDK)...")
        try:
            client = genai.Client(api_key=api_key)
            # Iterate over paginated list
            for m in client.models.list():
                if "gemma" in m.name:
                    gemma_models.append(m.name)
                    print(f" - {m.name}")
            return gemma_models
        except Exception as e:
            print(f"New SDK List failed: {e}")

    # Try Old SDK
    if OLD_SDK and not gemma_models:
        print("Using google.generativeai (Old SDK)...")
        old_genai.configure(api_key=api_key)
        try:
            for m in old_genai.list_models():
                if "gemma" in m.name:
                    gemma_models.append(m.name)
                    print(f" - {m.name}")
            return gemma_models
        except Exception as e:
            print(f"Old SDK List failed: {e}")
            
    if not NEW_SDK and not OLD_SDK:
        print("❌ Neither Google SDK is installed/importable.")
        
    return gemma_models

def test_model(model_name):
    print(f"\n--- Testing Model: {model_name} ---")
    api_key = os.environ.get("GEMINI_API_KEY")
    clean_name = model_name.replace("models/", "")

    try:
        # We rely on LangChain wrapper which handles the underlying client
        llm = ChatGoogleGenerativeAI(
            model=clean_name,
            temperature=0,
            google_api_key=api_key
        )
        response = llm.invoke("Hello")
        print(f"✅ Success! Response: {response.content}")
        return True
    except NotFound:
        print(f"❌ Error: 404 Not Found.")
    except ResourceExhausted:
        print(f"⚠️ Warning: 429 Resource Exhausted (Quota).")
        return True # It exists
    except Exception as e:
        print(f"❌ Error: {e}")
    return False

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    found_models = list_all_models()
    
    candidates = [
        "gemma-2-27b-it",
        "gemma-2-9b-it"
    ]
    
    # Add found ones
    for m in found_models:
        clean = m.replace("models/", "")
        if clean not in candidates:
            candidates.append(clean)
            
    print(f"\n--- Testing Candidates: {candidates} ---")
    results = {}
    for m in candidates:
        if m in results: continue
        results[m] = test_model(m)
        
    print("\n=== Summary ===")
    for m, status in results.items():
        print(f"{m}: {'AVAILABLE' if status else 'UNAVAILABLE'}")
