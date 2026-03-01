"""Adapter for handling tool calling with models that do not support native API tool binding (e.g. Gemma)."""

import json
import re
import logging
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

# Updated Prompt template with Thought-Action pattern for better reliability
GEMMA_TOOL_INSTRUCTION = """
You are an expert agent with access to the following tools:

{tool_schemas}

**Goal:** Fulfill the user's request by selecting the appropriate tool.

**Instructions:**
1.  **Thought**: First, reason about the user's request and which tool (if any) is best suited. Write this down.
2.  **Action**: If a tool is needed, output a JSON object strictly following this schema inside a markdown block.

**Tool Call Schema:**
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

If no tool is needed, just respond with the text answer.
"""

def format_tools_to_json_schema(tools: List[BaseTool]) -> str:
    """
    Converts a list of LangChain tools into a readable JSON schema string for the prompt.
    """
    tool_schemas = []
    for tool in tools:
        # Pydantic v1 uses .args, v2 uses .args_schema or model_json_schema()
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
    Robustly handles markdown blocks and fallback JSON extraction.
    """
    # Debug logging to see what the model actually output
    logger.debug(f"Raw LLM Output for Tool Parsing:\n{content}\n" + "-"*20)

    tool_calls = []

    # 1. Try to find the standard ```json ... ``` block
    json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)

    json_str = ""
    if json_match:
        json_str = json_match.group(1)
    else:
        # 2. Fallback: Try to find a raw JSON object (first { to last })
        try:
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                candidate = content[start:end+1]
                json.loads(candidate)
                json_str = candidate
        except Exception:
            pass

    if not json_str:
        logger.warning("No JSON block found in LLM output.")
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
            elif "function" in data:
                 calls = [data["function"]]
            else:
                # Fallback: Implicit Arguments Object
                # If the dict keys look like arguments for a known tool
                # Specific check for 'Plan' tool which uses 'plan' key
                if "plan" in data and (allowed_tools is None or "Plan" in allowed_tools):
                     calls = [{"name": "Plan", "args": data}]
                elif "name" in data: # Malformed tool call object without args wrapper?
                    calls = [data]
                else:
                    # Risky fallback: if only one tool is allowed, assume it's that one
                    if allowed_tools and len(allowed_tools) == 1:
                        calls = [{"name": allowed_tools[0], "args": data}]
                    else:
                        # Cannot determine which tool
                        return []
        else:
            return []

        for call in calls:
            name = call.get("name")
            if not name:
                continue

            # Validate allowed tools
            if allowed_tools and name not in allowed_tools:
                # Case-insensitive match attempt?
                found = False
                for allowed in allowed_tools:
                    if allowed.lower() == name.lower():
                        name = allowed
                        found = True
                        break
                if not found:
                    continue

            arguments = call.get("arguments") or call.get("args") or {}

            # Ensure arguments is a dict
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except Exception:
                    pass

            import uuid
            call_id = f"call_{uuid.uuid4().hex[:8]}"

            tool_calls.append({
                "name": name,
                "args": arguments,
                "id": call_id,
                "type": "tool_call"
            })

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode failed: {e}")
        pass

    return tool_calls
