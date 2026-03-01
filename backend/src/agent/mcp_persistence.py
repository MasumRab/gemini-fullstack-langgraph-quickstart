import logging
from typing import Any, Dict, List

from mcp.server.fastmcp import FastMCP

from agent.persistence import load_plan, save_plan

# Setup logging
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("persistence")


@mcp.tool()
def load_thread_plan(thread_id: str) -> Dict[str, Any] | None:
    """
    Loads the saved plan and associated artifacts for the given thread.
    
    Parameters:
        thread_id (str): Unique identifier of the thread or conversation.
    
    Returns:
        Dict[str, Any] | None: The saved plan data (expected to include keys 'todo_list' and 'artifacts') if found, or `None` if no plan exists or an error occurred.
    """
    try:
        return load_plan(thread_id)
    except Exception as e:
        logger.exception(f"Error loading plan for thread {thread_id}: {e}")
        return None


@mcp.tool()
def save_thread_plan(
    thread_id: str, todo_list: List[Dict[str, Any]], artifacts: Dict[str, Any]
) -> str:
    """Saves the plan and artifacts for a specific thread to the local file system.

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
