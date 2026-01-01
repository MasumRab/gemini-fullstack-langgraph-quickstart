from typing import Any, Dict, List, Optional
import logging
from mcp.server.fastmcp import FastMCP
from agent.persistence import load_plan, save_plan

# Setup logging
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("persistence")

@mcp.tool()
def load_thread_plan(thread_id: str) -> Optional[Dict[str, Any]]:
    """
    Loads the plan and artifacts for a specific thread from the local file system.

    Args:
        thread_id: The unique identifier for the thread/conversation.

    Returns:
        The plan data (todo_list, artifacts) or None if not found.
    """
    try:
        return load_plan(thread_id)
    except Exception as e:
        logger.exception(f"Error loading plan for thread {thread_id}: {e}")
        return None

@mcp.tool()
def save_thread_plan(thread_id: str, todo_list: List[Dict[str, Any]], artifacts: Dict[str, Any]) -> str:
    """
    Saves the plan and artifacts for a specific thread to the local file system.

    Args:
        thread_id: The unique identifier for the thread/conversation.
        todo_list: The list of tasks/todos.
        artifacts: A dictionary of artifacts (documents, code, etc.).

    Returns:
        A success message.
    """
    try:
        save_plan(thread_id, todo_list, artifacts)
        return f"Plan saved successfully for thread {thread_id}"
    except Exception:
        logger.exception(f"Error saving plan for thread {thread_id}")
        return "Error saving plan"
