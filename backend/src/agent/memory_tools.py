from langchain_core.tools import tool
from agent.persistence import save_plan as persist_save, load_plan as persist_load

@tool
def save_plan_tool(thread_id: str, todo_list: list, artifacts: dict) -> str:
    """Saves the current plan and artifacts to a local file.

    Args:
        thread_id: The unique ID of the conversation thread.
        todo_list: The list of tasks/todos.
        artifacts: A dictionary of artifacts (documents, code).
    """
    try:
        persist_save(thread_id, todo_list, artifacts)
        return "Plan saved successfully."
    except Exception as e:
        return f"Error saving plan: {e}"

@tool
def load_plan_tool(thread_id: str) -> str:
    """Loads the plan and artifacts from a local file.

    Args:
        thread_id: The unique ID of the conversation thread.
    """
    try:
        data = persist_load(thread_id)
        if data:
            return f"Plan loaded: {data}"
        return "No plan found."
    except Exception as e:
        return f"Error loading plan: {e}"
