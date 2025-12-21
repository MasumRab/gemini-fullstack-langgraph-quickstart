"""Adapter for handling tool calling with models that do not support native API tool binding (e.g. Gemma)."""

import json
import re
from typing import Any, Dict, List, Optional, Union

from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool

# Prompt template for instructing the model
GEMMA_TOOL_INSTRUCTION = """
You have access to the following tools.
If the user's request requires using a tool, you MUST output a JSON object strictly following this schema inside a markdown code block.

Available Tools:
{tool_schemas}

**Output Format:**
To call a tool, output a JSON object like this:
```json
{{
  "tool_calls": [
    {{
      "name": "tool_name",
      "arguments": {{
        "arg1": "value1",
        "arg2": "value2"
      }}
    }}
  ]
}}
```

If no tool is needed, respond normally with text.
"""

def format_tools_to_json_schema(tools: List[BaseTool]) -> str:
    """
    Converts a list of LangChain tools into a readable JSON schema string for the prompt.
    """
    tool_schemas = []
    for tool in tools:
        # Pydantic v1 uses .args, v2 uses .args_schema or model_json_schema()
        # BaseTool.args usually returns just the properties, not the full JSON schema with "type": "object" wrapper
        # We want the full schema usually
        if hasattr(tool, "get_input_schema"):
             input_schema = tool.get_input_schema()
             if hasattr(input_schema, "model_json_schema"):
                 parameters = input_schema.model_json_schema()
             elif hasattr(input_schema, "schema"):
                 parameters = input_schema.schema()
             else:
                 parameters = tool.args
        else:
             parameters = tool.args

        schema = {
            "name": tool.name,
            "description": tool.description,
            "parameters": parameters
        }
        tool_schemas.append(schema)

    return json.dumps(tool_schemas, indent=2)


def parse_tool_calls(content: str, allowed_tools: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Parses the LLM output for JSON tool calls.
    Expects format:
    ```json
    {
        "tool_calls": [
            { "name": "...", "arguments": { ... } }
        ]
    }
    ```
    or just the raw JSON object.

    Args:
        content: The text output from the LLM.
        allowed_tools: Optional list of allowed tool names to validate against.

    Returns:
        List of tool call dicts compatible with LangChain's tool_calls structure:
        [{'name': str, 'args': dict, 'id': str, 'type': 'tool_call'}]
    """
    tool_calls = []

    # 1. Try to find JSON block
    json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Fallback: Try to find the first '{' and last '}'
        # This is risky but helps if the model forgets the markdown block
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            json_str = content[start:end+1]
        else:
            return []

    try:
        data = json.loads(json_str)

        # Handle list of tool calls (some models might output a list directly)
        if isinstance(data, list):
             calls = data
        # Handle standard wrapper
        elif isinstance(data, dict):
            if "tool_calls" in data:
                calls = data["tool_calls"]
            elif "name" in data and ("arguments" in data or "args" in data):
                # Single tool call object
                calls = [data]
            else:
                # Not a recognizable tool call structure
                return []
        else:
            return []

        for call in calls:
            name = call.get("name")
            if not name:
                continue

            # Validate allowed tools
            if allowed_tools and name not in allowed_tools:
                continue

            arguments = call.get("arguments") or call.get("args") or {}

            # Generate a dummy ID since Gemma doesn't provide one
            # Using a deterministic hash or random string
            import uuid
            call_id = f"call_{uuid.uuid4().hex[:8]}"

            tool_calls.append({
                "name": name,
                "args": arguments,
                "id": call_id,
                "type": "tool_call" # Standard LangChain field
            })

    except json.JSONDecodeError:
        # Log warning or handle silently?
        # For now, return empty if parsing fails
        pass

    return tool_calls
