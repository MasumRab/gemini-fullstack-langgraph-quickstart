import contextlib
import logging
from typing import Any, Dict

from observability.config import is_audit_mode, is_enabled

logger = logging.getLogger(__name__)

# Try to import Langfuse
try:
    from langfuse import observe

    _LANGFUSE_AVAILABLE = True
except ImportError:
    _LANGFUSE_AVAILABLE = False
    observe = None


def get_langfuse_handler(metadata: Dict[str, Any] | None = None) -> Any | None:
    """Factory to create a Langfuse CallbackHandler if enabled and available.

    Args:
        metadata: Optional dictionary of metadata to attach to the trace.

    Returns:
        A Langfuse CallbackHandler instance or None.
    """
    if not is_enabled() or not _LANGFUSE_AVAILABLE:
        return None

    try:
        # Shim for different import paths in v2 vs v3
        LangfuseCallbackHandler = None

        # Try finding the handler in known locations
        # 1. Integration package (newer V3 structure)
        if LangfuseCallbackHandler is None:
            try:
                from langfuse.integrations.langchain import LangfuseCallbackHandler
            except ImportError:
                pass

        # 2. Native package (V2/V3) - Verified working path for 3.10.5
        if LangfuseCallbackHandler is None:
            try:
                from langfuse.langchain import (
                    CallbackHandler as LangfuseCallbackHandler,
                )
            except ImportError:
                pass

        # 3. Callback module (Older V2)
        if LangfuseCallbackHandler is None:
            try:
                from langfuse.callback import CallbackHandler as LangfuseCallbackHandler
            except ImportError:
                pass

        if LangfuseCallbackHandler is None:
            logger.warning(
                "Langfuse enabled but CallbackHandler could not be imported."
            )
            return None

        # We can pass tags or session info via kwargs if needed
        # Note: Constructor might not accept metadata in all versions,
        # so we rely on env vars for auth.
        handler = LangfuseCallbackHandler()

        return handler
    except Exception as e:
        logger.error(f"Failed to initialize Langfuse handler: {e}")
        return None


@contextlib.contextmanager
def observe_span(name: str, config: Dict | None = None, **kwargs):
    """Context manager to create a Langfuse span manually.

    This is useful for non-LangChain code blocks or when we want explicit control.

    Args:
        name: Name of the span.
        config: RunnableConfig object (optional) to extract existing trace context.
        **kwargs: Additional metadata/attributes.
    """
    if not is_enabled() or not _LANGFUSE_AVAILABLE or not observe:
        yield
        return

    # In v3, `observe` is a decorator/context manager that handles nesting automatically.
    # We use it directly.

    # We move the try-except block to wrap the observation creation,
    # but we MUST allow exceptions from the yielded block to bubble up.

    span = None
    try:
        # NOTE: observe() takes `as_type` argument. Default is 'span' if nested.
        # We enter the context manually to ensure we can handle exceptions from the span creation itself
        # separately from the user code.
        # Actually, standard usage `with observe(...)` handles exceptions in the body by recording them
        # on the span and re-raising. We just need to not swallow them.

        with observe(name=name, **kwargs) as span_obj:
            span = span_obj
            # Check audit mode for extra logging
            if is_audit_mode():
                # We can update the span metadata if we have access to the span object
                if hasattr(span, "update"):
                    # Note: update() signature depends on SDK version, usually takes kwargs
                    span.update(
                        metadata={
                            "audit": True,
                            "config_keys": list(config.keys()) if config else [],
                        }
                    )

            yield span

    except Exception as e:
        # If the exception came from observe() itself (unlikely) or the yield, it bubbles here.
        # Langfuse's observe() re-raises exceptions from the body.
        # We just need to make sure we don't suppress it.
        # The previous code had `yield` inside `try` and suppressed `Exception`.
        # By removing the suppression, we are good.
        # But wait, we still want to log if it was an observability error vs app error?
        # No, simpler is better. Just let it bubble.
        raise e
