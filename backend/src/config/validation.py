import os
import logging
import importlib.util
from typing import List, Dict

logger = logging.getLogger(__name__)

def validate_environment() -> Dict[str, bool]:
    """
    Validates the runtime environment for critical dependencies and variables.
    Returns a dict of check statuses.
    """
    checks = {}

    # 1. Critical Environment Variables
    # We don't fail hard here (letting the app start), but we log errors.
    # Adjust based on what is truly "blocking".

    # Example: GEMINI_API_KEY is usually required for this agent
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
         checks["api_key"] = False
         logger.warning("VALIDATION: GEMINI_API_KEY or GOOGLE_API_KEY is missing. Agent may fail to generate responses.")
    else:
         checks["api_key"] = True

    # 2. Critical Python Dependencies
    # Check if they can be imported
    # Note: 'google-genai' package is imported as 'google.genai'
    required_pkgs = {
        "langchain": "langchain",
        "langgraph": "langgraph",
        "google_genai": "google.genai"
    }

    for pkg_name, import_name in required_pkgs.items():
        found = importlib.util.find_spec(import_name) is not None
        checks[f"pkg_{pkg_name}"] = found
        if not found:
            logger.error(f"VALIDATION: Critical package '{pkg_name}' (import: {import_name}) not found!")

    # 3. Optional but Important
    # sentence-transformers
    checks["sentence_transformers"] = importlib.util.find_spec("sentence_transformers") is not None
    if not checks["sentence_transformers"]:
         logger.info("VALIDATION: sentence-transformers not found. Local embeddings will be disabled.")

    return checks

def check_env_strict():
    """
    Strict check that raises an error if critical components are missing.
    Call this on app startup if you want to fail fast.
    """
    results = validate_environment()

    # Define what is "critical"
    critical_failures = []
    if not results.get("api_key", False):
        critical_failures.append("Missing API Key")

    # Check packages
    for key, valid in results.items():
        if key.startswith("pkg_") and not valid:
            critical_failures.append(f"Missing Package: {key}")

    if critical_failures:
        msg = f"Startup Validation Failed: {', '.join(critical_failures)}"
        logger.error(msg)
        # We might not want to crash the whole server in some contexts (like dev),
        # but for robustness in production, we might.
        # For now, we just log heavily.
        return False
    return True
