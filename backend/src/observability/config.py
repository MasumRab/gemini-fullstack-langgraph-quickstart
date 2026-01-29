import os


def is_enabled() -> bool:
    """Check if Langfuse observability is enabled via environment variables."""
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
    """Check if audit mode is enabled for richer metadata."""
    return os.getenv("AUDIT_MODE", "false").lower() in ("true", "1", "yes", "on")
