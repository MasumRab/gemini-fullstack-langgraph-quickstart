from langchain_core.tools import tool
from agent.persistence import save_plan as persist_save, load_plan as persist_load

@tool
def save_plan_tool(thread_id: str, todo_list: list, artifacts: dict) -> str:
    """
    Save a plan and its associated artifacts to persistent storage for a conversation thread.
    
    Parameters:
        thread_id (str): Unique identifier for the conversation thread.
        todo_list (list): List of tasks or todo items representing the plan.
        artifacts (dict): Mapping of artifact names to their data (e.g., documents, code).
    
    Returns:
        str: A status message: "Plan saved successfully." on success or "Error saving plan: {error message}." on failure.
    """
    try:
        persist_save(thread_id, todo_list, artifacts)
        return "Plan saved successfully."
    except Exception as e:
        return f"Error saving plan: {e}"

@tool
def load_plan_tool(thread_id: str) -> str:
    """
    Load the saved plan and artifacts for a conversation thread.
    
    Parameters:
        thread_id (str): Unique identifier for the conversation thread to load.
    
    Returns:
        str: A message indicating the result:
            - "Plan loaded: {data}" when saved plan and artifacts are found (with {data} containing the loaded content).
            - "No plan found." when no saved data exists for the given thread_id.
            - "Error loading plan: {error message}" if an exception occurred during load.
    """
    try:
        data = persist_load(thread_id)
        if data:
            return f"Plan loaded: {data}"
        return "No plan found."
    except Exception as e:
        return f"Error loading plan: {e}"