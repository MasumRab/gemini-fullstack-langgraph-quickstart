from typing import Dict, Any
from agent.state import OverallState

def handle_end_plan(state: OverallState) -> Dict[str, Any]:
    return {
        "planning_status": "auto_approved",
        "planning_steps": [],
        "planning_feedback": ["Planning disabled via /end_plan."],
    }

def handle_confirm_plan(state: OverallState) -> Dict[str, Any]:
    return {
        "planning_status": "confirmed",
        "planning_feedback": ["Plan confirmed. Proceeding to research."]
    }

def handle_start_plan(state: OverallState) -> Dict[str, Any]:
    return {
        "planning_status": "awaiting_confirmation",
        "planning_feedback": ["Planning mode started. Please review the plan."]
    }

def planning_router_logic(user_input: str, state: OverallState) -> str:
    """
    Routes planning-related commands to appropriate handlers.
    Returns the name of the next node.
    """
    user_input = user_input.strip().lower()

    if user_input.startswith("/end_plan"):
        # We need to perform the state update associated with this command
        # In LangGraph, we typically do this in a node.
        # But since we are in a router, we return the node that will handle the transition
        # OR we rely on the fact that the 'planning_mode' or 'web_research' will handle it.
        # Given the previous design where router did state updates (side effect),
        # we will formalize this by returning a node that processes the command if we were refactoring completely.
        # However, for compatibility, we will stick to the existing flow but CLEANER.
        return "planning_command_handler"

    elif user_input.startswith("/confirm_plan"):
        return "planning_command_handler"

    elif user_input.startswith("/plan"):
        return "planning_command_handler"

    return "continue"

# NOTE: The above 'planning_router_logic' is a helper.
# The actual router in LangGraph needs to return the Node Name.
