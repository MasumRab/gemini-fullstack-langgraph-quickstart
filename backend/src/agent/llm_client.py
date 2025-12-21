import logging
from typing import Any, Union
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

# Define a retry strategy: wait 1s, 2s, 4s, etc., up to 3 times
# You can customize this or make it configurable via kwargs if needed,
# but using a decorator is cleaner for the core logic.
# We'll retry on any Exception for now, but ideally this should be more specific (e.g., NetworkError).
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def call_llm_robust(llm_client: Any, prompt: str, **kwargs) -> str:
    """
    Robustly calls an LLM client, handling different interfaces (invoke vs generate)
    and applying retries.

    Args:
        llm_client: The LLM client object (LangChain, Gemini SDK, etc.).
        prompt: The prompt string.
        **kwargs: Additional arguments to pass to the client.

    Returns:
        str: The generated text content.
    """
    try:
        # 1. Try LangChain 'invoke' interface
        if hasattr(llm_client, "invoke"):
            response = llm_client.invoke(prompt, **kwargs)
            if hasattr(response, "content"):
                return str(response.content)
            return str(response)

        # 2. Try Gemini/GenerativeAI 'generate' interface
        elif hasattr(llm_client, "generate"):
            # Some SDKs might expect 'generate_content' or just 'generate'
            # The existing code checked 'generate', so we stick to that first.
            response = llm_client.generate(prompt, **kwargs)
            # Response handling might vary
            if hasattr(response, "text"):
                 return response.text
            return str(response)

        # 3. Fallback to callable (some custom wrappers)
        else:
            response = llm_client(prompt, **kwargs)
            if hasattr(response, "content"):
                return str(response.content)
            return str(response)

    except Exception as e:
        logger.warning(f"LLM call failed (attempting retry): {e}")
        raise e
