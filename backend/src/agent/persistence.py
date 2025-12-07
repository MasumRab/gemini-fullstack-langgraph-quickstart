from typing import List, Dict, Any

def load_plan(thread_id: str) -> Dict[str, Any]:
    """Mock persistence load."""
    return {}

def save_plan(thread_id: str, plan: List[Dict], artifacts: Dict) -> None:
    """Mock persistence save."""
    pass
