import json
import os
from typing import List, Dict, Any, Optional

PLAN_DIR = "plans"

def _get_plan_path(thread_id: str) -> str:
    """Gets the file path for a specific thread's plan."""
    # Ensure the plans directory exists
    os.makedirs(PLAN_DIR, exist_ok=True)
    # Sanitize thread_id to be safe for filenames
    safe_id = "".join(c for c in thread_id if c.isalnum() or c in ('-', '_'))
    return os.path.join(PLAN_DIR, f"{safe_id}.json")

def save_plan(thread_id: str, todo_list: List[Dict[str, Any]], artifacts: Dict[str, str]) -> None:
    """Saves the current plan and artifacts to a JSON file."""
    if not thread_id:
        return
        
    path = _get_plan_path(thread_id)
    data = {
        "todo_list": todo_list,
        "artifacts": artifacts,
        "updated_at": os.path.getmtime(path) if os.path.exists(path) else None
    }
    
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving plan for thread {thread_id}: {e}")

def load_plan(thread_id: str) -> Optional[Dict[str, Any]]:
    """Loads the plan and artifacts from a JSON file."""
    if not thread_id:
        return None
        
    path = _get_plan_path(thread_id)
    if not os.path.exists(path):
        return None
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading plan for thread {thread_id}: {e}")
        return None
