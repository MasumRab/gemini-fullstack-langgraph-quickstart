import importlib.util
import logging
import os
from typing import Dict

logger = logging.getLogger(__name__)


def validate_environment() -> Dict[str, bool]:
    """
    Validate runtime environment for required API keys and Python packages.
    
    The returned dictionary includes:
    - "api_key": `True` if either GEMINI_API_KEY or GOOGLE_API_KEY is set, `False` otherwise.
    - "pkg_<name>": `True` if the corresponding required package (by import path) is importable, `False` otherwise. Present keys include "pkg_langchain", "pkg_langgraph", and "pkg_google_genai".
    - "sentence_transformers": `True` if the optional `sentence_transformers` package is importable, `False` otherwise.
    
    Returns:
        A dict mapping check names to boolean results: `True` if the check passed, `False` otherwise.
    """
    checks = {}

    # 1. Critical Environment Variables
    # We don't fail hard here (letting the app start), but we log errors.
    # Adjust based on what is truly "blocking".

    # Example: GEMINI_API_KEY is usually required for this agent
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
        checks["api_key"] = False
        logger.warning(
            "VALIDATION: GEMINI_API_KEY or GOOGLE_API_KEY is missing. Agent may fail to generate responses."
        )
    else:
        checks["api_key"] = True

    # 2. Critical Python Dependencies
    # Check if they can be imported
    # Note: 'google-genai' package is imported as 'google.genai'
    required_pkgs = {
        "langchain": "langchain",
        "langgraph": "langgraph",
        "google_genai": "google.genai",
    }

    for pkg_name, import_name in required_pkgs.items():
        found = importlib.util.find_spec(import_name) is not None
        checks[f"pkg_{pkg_name}"] = found
        if not found:
            logger.error(
                f"VALIDATION: Critical package '{pkg_name}' (import: {import_name}) not found!"
            )

    # 3. Optional but Important
    # sentence-transformers
    checks["sentence_transformers"] = (
        importlib.util.find_spec("sentence_transformers") is not None
    )
    if not checks["sentence_transformers"]:
        logger.info(
            "VALIDATION: sentence-transformers not found. Local embeddings will be disabled."
        )

    return checks


def check_env_strict():
    """
    Validate critical runtime dependencies and indicate whether startup can proceed.
    
    This treats a missing API key and any failed package check whose key starts with "pkg_" as critical. If any critical failures are detected an error is logged and the function signals failure.
    
    Returns:
        bool: True if no critical failures were found, False if one or more critical failures were detected.
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
