from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP
from agent.persistence import load_plan, save_plan

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
    return load_plan(thread_id)

@mcp.tool()
def save_thread_plan(thread_id: str, todo_list: List[Dict[str, Any]], artifacts: Dict[str, str]) -> str:
    """
    Save the plan and artifacts for a thread to local storage.
    
    Parameters:
        thread_id (str): Thread/conversation identifier.
        todo_list (List[Dict[str, Any]]): List of task dictionaries to persist.
        artifacts (Dict[str, str]): Mapping of artifact names to their contents.
    
    Returns:
        str: Success message "Plan saved successfully for thread {thread_id}" on success, or an error message containing the exception text on failure.
    """
    try:
        save_plan(thread_id, todo_list, artifacts)
        return f"Plan saved successfully for thread {thread_id}"
    except Exception as e:
        return f"Error saving plan: {str(e)}"