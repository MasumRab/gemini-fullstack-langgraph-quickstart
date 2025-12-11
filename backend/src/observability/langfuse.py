import logging
import contextlib
from typing import Optional, Any, Dict

from observability.config import is_enabled, is_audit_mode

logger = logging.getLogger(__name__)

# Try to import Langfuse
try:
    from langfuse import observe
    _LANGFUSE_AVAILABLE = True
except ImportError:
    _LANGFUSE_AVAILABLE = False
    observe = None

def get_langfuse_handler(metadata: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    """
    Return a Langfuse CallbackHandler instance when Langfuse is enabled and available.
    
    Attempts to locate and instantiate a compatible Langfuse CallbackHandler. If observability is disabled, Langfuse is not installed, the handler class cannot be found, or initialization fails, the function returns `None`.
    
    Parameters:
        metadata (Optional[Dict[str, Any]]): Optional metadata intended for handler/trace association. Depending on the installed Langfuse version, the constructor may not accept metadata, so this argument may be unused.
    
    Returns:
        A Langfuse CallbackHandler instance if available, `None` otherwise.
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
                from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler
            except ImportError:
                pass

        # 3. Callback module (Older V2)
        if LangfuseCallbackHandler is None:
             try:
                 from langfuse.callback import CallbackHandler as LangfuseCallbackHandler
             except ImportError:
                 pass

        if LangfuseCallbackHandler is None:
            logger.warning("Langfuse enabled but CallbackHandler could not be imported.")
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
def observe_span(name: str, config: Optional[Dict] = None, **kwargs):
    """
    Create a Langfuse observation span and yield it for use within a context.
    
    Yields the Langfuse span object when Langfuse is enabled and available; otherwise yields None. If audit mode is enabled and the yielded span exposes an `update` method, the span's metadata will be updated with an `audit` flag and a `config_keys` list derived from `config`.
    
    Parameters:
        name (str): Name of the span.
        config (Optional[Dict]): Optional configuration whose keys are added to span metadata when in audit mode.
        **kwargs: Additional metadata/attributes forwarded to the Langfuse `observe` call.
    
    Yields:
        The Langfuse span object if available, `None` otherwise.
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
                 if hasattr(span, 'update'):
                     # Note: update() signature depends on SDK version, usually takes kwargs
                     span.update(metadata={"audit": True, "config_keys": list(config.keys()) if config else []})

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