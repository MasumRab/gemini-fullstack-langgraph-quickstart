

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


def _scan_with_new_sdk(api_key: str, keyword: str) -> list[str]:
    """Scan for models using the new Google SDK."""
    try:
        client = genai.Client(api_key=api_key)
        return [m.name for m in client.models.list() if keyword in m.name]
    except Exception as e:
        return [f"New SDK Error: {e}"]


def _scan_with_old_sdk(api_key: str, keyword: str) -> list[str]:
    """Scan for models using the old Google SDK."""
    try:
        old_genai.configure(api_key=api_key)
        return [m.name for m in old_genai.list_models() if keyword in m.name]
    except Exception as e:
        return [f"Old SDK Error: {e}"]


def scan_for_models(keyword: str = "gemma") -> list[str]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return ["Error: GEMINI_API_KEY missing"]

    # Try New SDK first
    if NEW_SDK:
        return _scan_with_new_sdk(api_key, keyword)

    # Try Old SDK as fallback
    if OLD_SDK:
        return _scan_with_old_sdk(api_key, keyword)

    return ["Error: No Google SDK available"]

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check for Gemma 3 specifically
    gemma3 = scan_for_models("gemma-3")
    
    # Also get all gemma to be sure
    all_gemma = scan_for_models("gemma")
    
    with open("model_scan_results.txt", "w") as f:
        f.write("=== Gemma 3 Scan ===\n")
        if gemma3:
            for m in gemma3:
                f.write(f"{m}\n")
        else:
            f.write("No 'gemma-3' models found.\n")
            
        f.write("\n=== All Gemma Models ===\n")
        for m in all_gemma:
            f.write(f"{m}\n")
            
    print("Scan complete. Check model_scan_results.txt")
