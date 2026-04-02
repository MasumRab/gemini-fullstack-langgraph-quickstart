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


def _scan_new_sdk(api_key, keyword, found_models):
    if not NEW_SDK:
        return
    try:
        client = genai.Client(api_key=api_key)
        for m in client.models.list():
            if keyword in m.name:
                found_models.append(m.name)
    except Exception as e:
        found_models.append(f"New SDK Error: {e}")


def _scan_old_sdk(api_key, keyword, found_models):
    if not OLD_SDK or found_models:
        return
    try:
        old_genai.configure(api_key=api_key)
        for m in old_genai.list_models():
            if keyword in m.name:
                found_models.append(m.name)
    except Exception as e:
        found_models.append(f"Old SDK Error: {e}")


def scan_for_models(keyword="gemma"):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return ["Error: GEMINI_API_KEY missing"]

    found_models = []
    _scan_new_sdk(api_key, keyword, found_models)
    _scan_old_sdk(api_key, keyword, found_models)
    return found_models


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
