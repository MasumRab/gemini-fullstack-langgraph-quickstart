"""Centralized model name constants for Gemini API.

This module provides a single source of truth for all Gemini model names
used throughout the application. This prevents typos and ensures consistency.

Usage:
    from agent.models import GEMINI_FLASH, GEMINI_PRO
    
    llm = ChatGoogleGenerativeAI(model=GEMINI_FLASH)
"""

# ============================================================================
# Gemini 2.5 Models (Accessible via API - December 2024)
# ============================================================================

# Primary models for production use
GEMINI_FLASH = "gemini-2.5-flash"
"""Fast, efficient model for most tasks. 1M token context, 15 RPM free tier."""

GEMINI_FLASH_LITE = "gemini-2.5-flash-lite"
"""Lightweight variant of Flash. 1M token context, 15 RPM free tier."""

GEMINI_PRO = "gemini-2.5-pro"
"""High-capability model for complex tasks. 2M token context, 10 RPM free tier."""

GEMMA_2_27B_IT = "gemma-2-27b-it"
"""Open weights model (Gemma 2 27B IT). High daily limits, 8k context."""

GEMMA_3_27B_IT = "gemma-3-27b-it"
"""Gemma 3 27B IT. High daily limits, suitable for most tasks."""

# ============================================================================
# Default Model Assignments
# ============================================================================

# These are the recommended defaults for different tasks
DEFAULT_QUERY_MODEL = GEMMA_3_27B_IT
"""Default model for query generation - fast and efficient."""

DEFAULT_REFLECTION_MODEL = GEMMA_3_27B_IT
"""Default model for reflection/reasoning - balanced performance."""

DEFAULT_ANSWER_MODEL = GEMMA_3_27B_IT
"""Default model for final answer synthesis - high quality output."""

DEFAULT_VALIDATION_MODEL = GEMMA_3_27B_IT
"""Default model for validation tasks - quick verification."""

DEFAULT_COMPRESSION_MODEL = GEMMA_3_27B_IT
"""Default model for compression - lightweight and fast."""

DEFAULT_SCOPING_MODEL = GEMMA_3_27B_IT
"""Default model for scoping/planning - efficient analysis."""

# ============================================================================
# Model Aliases (for backward compatibility)
# ============================================================================

# Map common names to actual model identifiers
MODEL_ALIASES = {
    "flash": GEMINI_FLASH,
    "flash-lite": GEMINI_FLASH_LITE,
    "pro": GEMINI_PRO,
    "gemini-flash": GEMINI_FLASH,
    "gemini-pro": GEMINI_PRO,
    "gemma": GEMMA_3_27B_IT,
}

# ============================================================================
# Testing Constants
# ============================================================================

TEST_MODEL = GEMMA_3_27B_IT
"""Model to use in tests - points to a valid, accessible model."""

# ============================================================================
# Deprecated Models (DO NOT USE - kept for reference only)
# ============================================================================

# These models are not accessible via the current API
_DEPRECATED_MODELS = {
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-exp",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash-preview-04-17",
    "gemini-2.5-pro-preview-05-06",
}

# ============================================================================
# Validation Functions
# ============================================================================

def is_valid_model(model_name: str) -> bool:
    """Check if a model name is valid and accessible.
    
    Args:
        model_name: Model name to validate
        
    Returns:
        True if model is valid and accessible, False otherwise
    """
    # Check if it's a known valid model
    valid_models = {GEMINI_FLASH, GEMINI_FLASH_LITE, GEMINI_PRO, GEMMA_2_27B_IT, GEMMA_3_27B_IT}
    
    if model_name in valid_models:
        return True
    
    # Check if it's a valid alias
    if model_name in MODEL_ALIASES:
        return True
    
    return False


def is_deprecated_model(model_name: str) -> bool:
    """Check if a model name is deprecated.
    
    Args:
        model_name: Model name to check
        
    Returns:
        True if model is deprecated, False otherwise
    """
    return model_name in _DEPRECATED_MODELS


def get_model_or_default(model_name: str, default: str = GEMMA_3_27B_IT) -> str:
    """Get a valid model name, falling back to default if invalid.
    
    Args:
        model_name: Requested model name
        default: Default model to use if requested model is invalid
        
    Returns:
        Valid model name
    """
    # Check if it's an alias
    if model_name in MODEL_ALIASES:
        return MODEL_ALIASES[model_name]
    
    # Check if it's valid
    if is_valid_model(model_name):
        return model_name
    
    # Check if it's deprecated
    if is_deprecated_model(model_name):
        import logging
        logging.warning(
            f"Model '{model_name}' is deprecated and not accessible. "
            f"Using '{default}' instead."
        )
        return default
    
    # Unknown model - use default
    import logging
    logging.warning(
        f"Unknown model '{model_name}'. Using '{default}' instead."
    )
    return default


# ============================================================================
# All Valid Models (for iteration/validation)
# ============================================================================

ALL_VALID_MODELS = [GEMINI_FLASH, GEMINI_FLASH_LITE, GEMINI_PRO, GEMMA_2_27B_IT, GEMMA_3_27B_IT]
"""List of all valid, accessible Gemini models."""

def is_gemma_model(model_name: str) -> bool:
    """Check if the model is a Gemma model (requires custom tool handling)."""
    if not model_name:
        return False
    return "gemma" in model_name.lower()

def is_gemini_model(model_name: str) -> bool:
    """Check if the model is a Gemini model (supports native tool binding)."""
    if not model_name:
        return False
    name = model_name.lower()
    return "gemini" in name or "google" in name
