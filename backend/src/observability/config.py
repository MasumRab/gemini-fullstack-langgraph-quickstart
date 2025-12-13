import os
from typing import Optional

def is_enabled() -> bool:
    """
    Determine whether Langfuse observability is enabled based on environment configuration and required keys.
    
    Returns:
        bool: `True` if LANGFUSE_ENABLED is set to an enabled value and both LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are present, `False` otherwise.
    """
    # Check if explicitly enabled
    enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() in ("true", "1", "yes", "on")
    if not enabled:
        return False

    # Check for required keys
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    # Host is optional, defaults to cloud

    return bool(public_key and secret_key)

def is_audit_mode() -> bool:
    """
    Determine whether audit mode is enabled to collect richer metadata.
    
    Returns:
        bool: `True` if the `AUDIT_MODE` environment variable is set to one of "true", "1", "yes", or "on" (case-insensitive), `False` otherwise.
    """
    return os.getenv("AUDIT_MODE", "false").lower() in ("true", "1", "yes", "on")