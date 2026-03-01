import json
import os
from typing import Any, Dict, List

PLAN_DIR = "plans"


def _get_plan_path(thread_id: str) -> str:
    """
    Return the filesystem path for a thread's plan file.
    
    Ensures the plans directory exists and sanitizes `thread_id` to a safe filename by keeping only
    alphanumeric characters, hyphens, and underscores. The resulting filename is `<safe_id>.json`
    located inside the plans directory.
    
    Parameters:
        thread_id (str): Identifier for the thread; may contain characters that will be removed
            during sanitization.
    
    Returns:
        str: Path to the plan file within the plans directory.
    """
    # Ensure the plans directory exists
    os.makedirs(PLAN_DIR, exist_ok=True)
    # Sanitize thread_id to be safe for filenames
    safe_id = "".join(c for c in thread_id if c.isalnum() or c in ("-", "_"))
    return os.path.join(PLAN_DIR, f"{safe_id}.json")


def save_plan(
    thread_id: str, todo_list: List[Dict[str, Any]], artifacts: Dict[str, Any]
) -> None:
    """Saves the current plan and artifacts to a JSON file."""
    if not thread_id:
        return

    path = _get_plan_path(thread_id)
    data = {
        "todo_list": todo_list,
        "artifacts": artifacts,
        "updated_at": os.path.getmtime(path) if os.path.exists(path) else None,
    }

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving plan for thread {thread_id}: {e}")


def load_plan(thread_id: str) -> Dict[str, Any] | None:
    """
    Load a saved plan and its artifacts for the given thread.
    
    Parameters:
        thread_id (str): Identifier used to locate the plan file.
    
    Returns:
        dict | None: The loaded JSON object with keys `"todo_list"`, `"artifacts"`, and `"updated_at"` if the file exists and is valid; `None` if `thread_id` is falsy, the file does not exist, or an error occurs while reading/parsing.
    """
    if not thread_id:
        return None

    path = _get_plan_path(thread_id)
    if not os.path.exists(path):
        return None

    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading plan for thread {thread_id}: {e}")
        return None
