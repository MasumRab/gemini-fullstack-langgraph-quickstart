import logging
from typing import Any, Union, List, Optional
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


class GemmaAdapter:
    """
    Adapter for Gemma models to provide a LangChain-like 'invoke' interface
    with tool-calling support via manual prompting and parsing.
    """
    def __init__(self, client: Any, tools: Optional[List[Any]] = None):
        self.client = client
        self.tools = tools or []
        from agent.tool_adapter import GEMMA_TOOL_INSTRUCTION, format_tools_to_json_schema
        self.instruction_template = GEMMA_TOOL_INSTRUCTION
        self.tools_schema = format_tools_to_json_schema(self.tools) if self.tools else ""

    def invoke(self, input_data: Union[str, Any], **kwargs) -> Any:
        # Extract prompt from input (could be string or list of messages)
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
            full_prompt = self.instruction_template.format(
                tool_schemas=self.tools_schema
            ) + f"\n\nUser Request: {prompt}"
        else:
            full_prompt = prompt

        # Call the underlying client
        response_text = call_llm_robust(self.client, full_prompt, **kwargs)

        # If tools are present, parse for tool calls
        if self.tools:
            from agent.tool_adapter import parse_tool_calls
            from langchain_core.messages import AIMessage
            
            tool_names = [t.name for t in self.tools]
            tool_calls = parse_tool_calls(response_text, allowed_tools=tool_names)
            
            if tool_calls:
                return AIMessage(content=response_text, tool_calls=tool_calls)
        
        from langchain_core.messages import AIMessage
        return AIMessage(content=response_text)
