import os


def is_enabled() -> bool:
    """
    Determine whether Langfuse observability is enabled based on environment variables.
    
    Checks the LANGFUSE_ENABLED environment variable (case-insensitive; accepts "true", "1", "yes", "on" as true). If enabled, requires both LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to be present.
    
    Returns:
        True if LANGFUSE_ENABLED is set to a true value and both public and secret keys are present, False otherwise.
    """
    # Check if explicitly enabled
    enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() in (
        "true",
        "1",
        "yes",
        "on",
    )
    if not enabled:
        return False

    # Check for required keys
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    # Host is optional, defaults to cloud

    return bool(public_key and secret_key)


def is_audit_mode() -> bool:
    """
    Determine whether audit mode is enabled to include richer metadata.
    
    Returns:
        True if the `AUDIT_MODE` environment variable (case-insensitive) is set to `true`, `1`, `yes`, or `on`, False otherwise.
    """
    return os.getenv("AUDIT_MODE", "false").lower() in ("true", "1", "yes", "on")
