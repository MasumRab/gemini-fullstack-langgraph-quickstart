from langchain_core.tools import tool

from agent.persistence import load_plan as persist_load
from agent.persistence import save_plan as persist_save


@tool
def save_plan_tool(thread_id: str, todo_list: list, artifacts: dict) -> str:
    """
    Save the current plan and associated artifacts to a local file for the given thread.
    
    Parameters:
        thread_id (str): Unique identifier of the conversation thread whose plan is being saved.
        todo_list (list): List of task items representing the plan.
        artifacts (dict): Mapping of artifact names to their data (e.g., documents, code).
    
    Returns:
        str: `"Plan saved successfully."` on success, or an error message beginning with
        `"Error saving plan: "` followed by the underlying exception message on failure.
    """
    try:
        persist_save(thread_id, todo_list, artifacts)
        return "Plan saved successfully."
    except Exception as e:
        return f"Error saving plan: {e}"


@tool
def load_plan_tool(thread_id: str) -> str:
    """
    Load a saved plan and its artifacts for the given conversation thread.
    
    Parameters:
        thread_id (str): The unique identifier of the conversation thread to load.
    
    Returns:
        str: `"Plan loaded: {data}"` if a saved plan and artifacts are found (`data` contains the loaded content),
        `"No plan found."` if nothing is stored for the thread, or
        `"Error loading plan: {e}"` if an error occurred while attempting to load.
    """
    try:
        data = persist_load(thread_id)
        if data:
            return f"Plan loaded: {data}"
        return "No plan found."
    except Exception as e:
        return f"Error loading plan: {e}"
