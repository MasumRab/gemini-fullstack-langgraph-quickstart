import logging
from typing import Any, List, Union

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


# Define a retry strategy: wait 1s, 2s, 4s, etc., up to 3 times
# You can customize this or make it configurable via kwargs if needed,
# but using a decorator is cleaner for the core logic.
# We'll retry on any Exception for now, but ideally this should be more specific (e.g., NetworkError).
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def call_llm_robust(llm_client: Any, prompt: str, **kwargs) -> str:
    """
    Call an LLM client and return its textual response, handling several client interfaces and triggering retry behavior on failure.
    
    Parameters:
        llm_client (Any): LLM client instance or callable. Supports objects with `invoke(...)`, objects with `generate(...)`, or a callable that accepts (prompt, **kwargs).
        prompt (str): The prompt or input text to send to the LLM.
        **kwargs: Additional client-specific keyword arguments forwarded to the underlying call.
    
    Returns:
        str: The response text produced by the LLM. If the response object exposes a `content` or `text` attribute, that value is returned as a string; otherwise the stringified response is returned.
    
    Raises:
        Exception: Re-raises any exception from the underlying client call (a warning is logged before re-raising to allow external retry logic to run).
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


class GemmaAdapter:
    """Adapter for Gemma models to provide a LangChain-like 'invoke' interface
    with tool-calling support via manual prompting and parsing.
    """

    def __init__(
        self, client: Any, tools: List[Any] | None = None, temperature: float = 0.7
    ):
        """
        Initialize the GemmaAdapter with an LLM client, optional tool definitions, and a default temperature.
        
        Parameters:
            client (Any): The underlying LLM client or callable used to generate responses.
            tools (List[Any] | None): Optional list of tool descriptors; when provided, they are formatted into a JSON schema and stored on the adapter. Defaults to no tools.
            temperature (float): Sampling temperature to use for generation when not overridden in calls; defaults to 0.7.
        """
        self.client = client
        self.tools = tools or []
        self.temperature = temperature
        from agent.tool_adapter import (
            GEMMA_TOOL_INSTRUCTION,
            format_tools_to_json_schema,
        )

        self.instruction_template = GEMMA_TOOL_INSTRUCTION
        self.tools_schema = (
            format_tools_to_json_schema(self.tools) if self.tools else ""
        )

    def invoke(self, input_data: Union[str, Any], **kwargs) -> Any:
        # Extract prompt from input (could be string or list of messages)
        """
        Invoke the adapter with user input and return an AIMessage containing the model response and any parsed tool calls.
        
        Parameters:
            input_data (str | Any): The user prompt or message(s). May be a raw string, an object with a `content` attribute, or a sequence of message-like objects (the last message will be used).
            **kwargs: Additional keyword arguments forwarded to the underlying LLM client (e.g., `temperature`); if `temperature` is not provided it defaults to the adapter's temperature.
        
        Returns:
            AIMessage: An AIMessage whose `content` is the model's text. If tool calling is enabled and tool calls are detected in the response, the AIMessage will include a `tool_calls` field describing those calls.
        """
        if isinstance(input_data, str):
            prompt = input_data
        elif hasattr(input_data, "content"):
            prompt = input_data.content
        elif isinstance(input_data, list) and input_data:
            # Simple heuristic: last message content
            last_msg = input_data[-1]
            prompt = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        else:
            prompt = str(input_data)

        # Inject tool instructions if tools are present
        if self.tools:
            full_prompt = (
                self.instruction_template.format(tool_schemas=self.tools_schema)
                + f"\n\nUser Request: {prompt}"
            )
        else:
            full_prompt = prompt

        # Pass temperature to the underlying client if it supports it
        if "temperature" not in kwargs:
            kwargs["temperature"] = self.temperature

        # Call the underlying client
        response_text = call_llm_robust(self.client, full_prompt, **kwargs)

        # Import AIMessage once at the top level
        from langchain_core.messages import AIMessage

        # If tools are present, parse for tool calls
        if self.tools:
            from agent.tool_adapter import parse_tool_calls

            # Defensive extraction of tool names
            tool_names = [
                name for t in self.tools if (name := getattr(t, "name", None))
            ]
            if len(tool_names) != len(self.tools):
                logger.warning("Some tools lack a 'name' attribute and were skipped")

            tool_calls = parse_tool_calls(response_text, allowed_tools=tool_names)

            if tool_calls:
                return AIMessage(content=response_text, tool_calls=tool_calls)

        return AIMessage(content=response_text)
