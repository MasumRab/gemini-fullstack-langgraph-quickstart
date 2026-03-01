import json
import logging
from typing import Dict, List

from agent.llm_client import call_llm_robust

logger = logging.getLogger(__name__)


class MCPToolUser:
    """Enables agent to use MCP tools for planned operations.
    Implements tool selection and execution logic.
    """

    def __init__(self, mcp_servers: List):
        self.servers = {server.name: server for server in mcp_servers}
        self.tool_registry = self._build_tool_registry()

    def _build_tool_registry(self) -> Dict:
        """
        Create a registry mapping fully-qualified tool names to their metadata.
        
        Each key is formatted as "server_name.tool_name". Each value is a dict containing:
        - "server": the server object,
        - "tool": the tool wrapper object,
        - "description": the tool's description.
        
        Returns:
            registry (Dict[str, Dict]): Mapping from fully-qualified tool name to its metadata dictionary.
        """
        registry = {}
        for server_name, server in self.servers.items():
            for tool in server.tools:
                # Key format: server.tool_name
                # Note: 'tool' here is the wrapper object from FilesystemMCPServer
                registry[f"{server_name}.{tool.name}"] = {
                    "server": server,
                    "tool": tool,
                    "description": tool.description,
                }
        return registry

    async def execute_tool(self, tool_name: str, **kwargs) -> Dict:
        """
        Execute a registered tool by name, accepting either a fully-qualified name (e.g., "server.tool") or a bare tool name.
        
        Parameters:
            tool_name (str): Fully-qualified tool name or bare tool name. If a bare name matches exactly one registered tool, that tool is used; if it matches multiple tools the call fails with an ambiguity error.
        
        Returns:
            dict: A dictionary with the following keys:
                - "success" (bool): `true` if the tool executed successfully, `false` otherwise.
                - "data": The tool's returned data on success (may be None or omitted by the tool).
                - "error" (str): An error message when "success" is `false`, describing not-found, ambiguity, execution failure, or exception details.
        """
        # Handle cases where tool_name might be just "read_file" or "filesystem.read_file"
        if tool_name not in self.tool_registry:
            # Try finding it without server prefix
            candidates = []
            for key in self.tool_registry:
                # We check for suffix match, assuming the registry key format is server.tool_name
                # The check ensures that we match a full tool name component (preceded by dot)
                if key.endswith(f".{tool_name}"):
                    candidates.append(key)

            if len(candidates) == 0:
                return {"success": False, "error": f"Tool {tool_name} not found"}
            elif len(candidates) == 1:
                # Unambiguous match
                matched_tool = candidates[0]
                logger.warning(
                    f"Tool '{tool_name}' matched to '{matched_tool}'. Please use the full tool name in the future."
                )
                tool_name = matched_tool
            else:
                # Ambiguous match
                return {
                    "success": False,
                    "error": f"Ambiguous tool name '{tool_name}'. Candidates: {', '.join(candidates)}",
                }

        tool_info = self.tool_registry[tool_name]
        handler = tool_info["tool"].handler

        try:
            result = await handler(**kwargs)
            return {
                "success": result.success,
                "data": result.data,
                "error": result.error,
            }
        except Exception as e:
            return {"success": False, "error": f"Execution exception: {str(e)}"}

    def plan_tool_sequence(self, task_description: str, llm_client) -> List[Dict]:
        """
        Plan a sequence of fully-qualified tool calls for a task using an LLM.
        
        Builds a prompt describing available tools and asks the LLM to return a JSON plan. The function extracts JSON from the LLM response (supports fenced code blocks with or without a "json" fence), parses it, and returns the plan as a list of dictionaries. If the parsed JSON is a dict with a "plan" key, that value is returned. On parse error, unexpected format, or any exception, an empty list is returned and an error is logged.
        
        Parameters:
        	task_description (str): Natural-language description of the task to plan.
        	llm_client: LLM client or object passed through to the robust LLM caller.
        
        Returns:
        	plan (List[Dict]): A list of planned tool call objects (e.g., {"tool": "namespace.tool", "params": {...}, "reason": "..."}) or an empty list on error.
        """
        # Build tool descriptions
        tool_descriptions = "\n".join(
            [
                f"- {name}: {info['description']} (Params: {json.dumps(info['tool'].inputSchema)})"
                for name, info in self.tool_registry.items()
            ]
        )

        planning_prompt = f"""
Given this task, plan a sequence of tool calls to complete it.

Available Tools:
{tool_descriptions}

Task: {task_description}

Return a JSON list of tool calls.
Format:
[
  {{"tool": "filesystem.tool_name", "params": {{"param1": "value1"}}, "reason": "why this tool"}},
  ...
]

ENSURE to use the full tool name (e.g. filesystem.write_file).
"""

        try:
            # Adapt to llm_client interface using robust caller
            response_text = call_llm_robust(llm_client, planning_prompt)

            # Clean markdown
            response_text = response_text.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            plan = json.loads(response_text)
            if isinstance(plan, list):
                return plan
            elif isinstance(plan, dict) and "plan" in plan:
                return plan["plan"]
            else:
                logger.error(f"Unexpected plan format: {plan}")
                return []

        except Exception as e:
            logger.error(f"Planning error: {e}")
            return []

    async def execute_plan(self, plan: List[Dict]) -> List[Dict]:
        """
        Execute a planned sequence of tool calls.
        
        Parameters:
            plan (List[Dict]): A list of steps where each step is a dict containing:
                - "tool" (str): Full tool identifier (e.g., "server.tool").
                - "params" (dict, optional): Keyword arguments to pass to the tool handler.
                - "reason" (str, optional): Human-readable reason for the step.
        
        Returns:
            List[Dict]: A list of result entries in execution order. Each entry contains:
                - "tool" (str): The tool name executed.
                - "params" (dict): The parameters used for the call.
                - "result" (dict): The tool execution result (contains "success", "data", and/or "error" as provided by execute_tool).
                - "reason" (str): The step's reason, or empty string if not provided.
        
        Notes:
            Execution stops at the first step whose result has "success" equal to `False`.
        """
        results = []

        for step in plan:
            tool_name = step.get("tool")
            params = step.get("params", {})

            logger.info(f"Executing: {tool_name} with {params}")
            result = await self.execute_tool(tool_name, **params)

            results.append(
                {
                    "tool": tool_name,
                    "params": params,
                    "result": result,
                    "reason": step.get("reason", ""),
                }
            )

            # Stop on failure
            if not result.get("success", False):
                logger.error(f"Tool execution failed: {result.get('error')}")
                break

        return results
