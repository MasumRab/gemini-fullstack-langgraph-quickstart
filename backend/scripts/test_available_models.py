#!/usr/bin/env python3
"""Test which Gemini models are accessible via the google-genai SDK.
"""

import os
import sys
from pathlib import Path

# Force UTF-8 output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from google import genai

# Add backend/src to path to import models
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.append(str(BACKEND_SRC))

try:
    from agent.models import (
        _DEPRECATED_MODELS,
        GEMINI_FLASH,
        GEMINI_FLASH_LITE,
        GEMINI_PRO,
    )
except ImportError:
    print("[ERROR] Could not import agent.models. Check backend/src path.")
    sys.exit(1)

# List of models to test
MODELS_TO_TEST = [
    # Active Models (from constants)
    GEMINI_FLASH,
    GEMINI_FLASH_LITE,
    GEMINI_PRO,
]


def test_model(client: genai.Client, model_name: str) -> tuple[bool, str]:
    """Test if a model is accessible."""
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Say hello"
        )
        return True, response.text[:50] if response.text else "OK"
    except Exception as e:
        return False, str(e)[:100]


def _load_api_key_from_env(env_path: Path) -> str | None:
    """Load API key from .env file."""
    if not env_path.exists():
        return None
    
    env_vars = {}
    with open(env_path, encoding='utf-8') as f:
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
    return env_vars.get('GEMINI_API_KEY') or env_vars.get('GOOGLE_API_KEY3') or env_vars.get('GOOGLE_API_KEY')


def _get_api_key() -> str | None:
    """Get API key from .env file or environment variable."""
    env_path = Path(__file__).parent / ".env"
    api_key = _load_api_key_from_env(env_path)
    if api_key:
        print("[OK] Loaded API key from .env")
        return api_key
    
    # Fallback to environment variable
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def _test_models(client: genai.Client) -> tuple[list[str], list[str]]:
    """Test all models and return working/failed lists."""
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
    
    return working_models, failed_models


def _print_summary(working_models: list[str], failed_models: list[str]) -> None:
    """Print summary of test results."""
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


def main() -> None:
    api_key = _get_api_key()
    
    if not api_key:
        print("[ERROR] No API key found!")
        print("   Please set GEMINI_API_KEY in .env or environment")
        return
    
    # Initialize client
    client = genai.Client(api_key=api_key)
    
    print("\n[TEST] Gemini Model Availability")
    print("=" * 70)
    
    working_models, failed_models = _test_models(client)
    _print_summary(working_models, failed_models)


if __name__ == "__main__":
    main()
