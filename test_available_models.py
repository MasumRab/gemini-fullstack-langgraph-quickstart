#!/usr/bin/env python3
"""
Test which Gemini models are accessible via the google-genai SDK.
"""

import os
import sys
from pathlib import Path

# Force UTF-8 output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from google import genai

# List of models to test
MODELS_TO_TEST = [
    # Gemini 1.5 series
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",

    # Gemini 2.0 series
    "gemini-2.0-flash",
    "gemini-2.0-flash-exp",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash-lite-preview-02-05",

    # Gemini 2.5 series
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
]

def test_model(client, model_name):
    """Test if a model is accessible."""
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Say hello"
        )
        return True, response.text[:50] if response.text else "OK"
    except Exception as e:
        return False, str(e)[:100]

def main():
    # Load .env file manually to handle variable expansion
    env_path = Path(__file__).parent / ".env"
    api_key = None

    if env_path.exists():
        env_vars = {}
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes
                    value = value.strip().strip('"').strip("'")
                    env_vars[key] = value

        # Resolve variable references
        for key, value in env_vars.items():
            if value.startswith('${') and value.endswith('}'):
                ref_key = value[2:-1]
                if ref_key in env_vars:
                    env_vars[key] = env_vars[ref_key]

        # Try to get API key from various sources
        api_key = env_vars.get('GEMINI_API_KEY') or env_vars.get('GOOGLE_API_KEY3') or env_vars.get('GOOGLE_API_KEY')
        print("[OK] Loaded API key from .env")

    # Fallback to environment variable
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    if not api_key:
        print("[ERROR] No API key found!")
        print("   Please set GEMINI_API_KEY in .env or environment")
        return

    # Initialize client
    client = genai.Client(api_key=api_key)

    print("\n[TEST] Gemini Model Availability")
    print("=" * 70)

    working_models = []
    failed_models = []

    for model in MODELS_TO_TEST:
        print(f"\n[TEST] {model}")
        success, result = test_model(client, model)

        if success:
            print(f"   [OK] WORKING - Response: {result}...")
            working_models.append(model)
        else:
            print(f"   [FAIL] Error: {result}")
            failed_models.append(model)

    # Summary
    print("\n" + "=" * 70)
    print(f"\n[OK] Working Models ({len(working_models)}):")
    for model in working_models:
        print(f"   - {model}")

    print(f"\n[FAIL] Failed Models ({len(failed_models)}):")
    for model in failed_models:
        print(f"   - {model}")

    # Generate recommended configuration
    print("\n" + "=" * 70)
    print("\n[INFO] Recommended Model Configuration:")
    if working_models:
        print(f"   Default Model: {working_models[0]}")
        print(f"   Available Options: {', '.join(working_models)}")
    else:
        print("   [WARN] No working models found!")

if __name__ == "__main__":
    main()
