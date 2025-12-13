from typing import List, Dict, Any, Optional
import json
import logging
from backend.src.agent.llm_client import call_llm_robust

logger = logging.getLogger(__name__)

class MCPToolUser:
    """
    Enables agent to use MCP tools for planned operations.
    Implements tool selection and execution logic.
    """

    def __init__(self, mcp_servers: List):
        self.servers = {server.name: server for server in mcp_servers}
        self.tool_registry = self._build_tool_registry()

    def _build_tool_registry(self) -> Dict:
        """Build registry of all available tools"""
        registry = {}
        for server_name, server in self.servers.items():
            for tool in server.tools:
                # Key format: server.tool_name
                # Note: 'tool' here is the wrapper object from FilesystemMCPServer
                registry[f"{server_name}.{tool.name}"] = {
                    "server": server,
                    "tool": tool,
                    "description": tool.description
                }
        return registry

    async def execute_tool(self, tool_name: str, **kwargs) -> Dict:
        """Execute a tool by name"""
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
                logger.warning(f"Tool '{tool_name}' matched to '{matched_tool}'. Please use the full tool name in the future.")
                tool_name = matched_tool
            else:
                # Ambiguous match
                return {
                    "success": False,
                    "error": f"Ambiguous tool name '{tool_name}'. Candidates: {', '.join(candidates)}"
                }

        tool_info = self.tool_registry[tool_name]
        handler = tool_info["tool"].handler

        try:
            result = await handler(**kwargs)
            return {
                "success": result.success,
                "data": result.data,
                "error": result.error
            }
        except Exception as e:
            return {"success": False, "error": f"Execution exception: {str(e)}"}

    def plan_tool_sequence(
        self,
        task_description: str,
        llm_client
    ) -> List[Dict]:
        """
        Use LLM to plan sequence of tool calls for a task.
        This is the "planned tool use" capability.
        """
        # Build tool descriptions
        tool_descriptions = "\n".join([
            f"- {name}: {info['description']} (Params: {json.dumps(info['tool'].inputSchema)})"
            for name, info in self.tool_registry.items()
        ])

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
        """Execute a planned sequence of tool calls"""
        results = []

        for step in plan:
            tool_name = step.get("tool")
            params = step.get("params", {})

            logger.info(f"Executing: {tool_name} with {params}")
            result = await self.execute_tool(tool_name, **params)

            results.append({
                "tool": tool_name,
                "params": params,
                "result": result,
                "reason": step.get("reason", "")
            })

            # Stop on failure
            if not result.get("success", False):
                logger.error(f"Tool execution failed: {result.get('error')}")
                break

        return results
