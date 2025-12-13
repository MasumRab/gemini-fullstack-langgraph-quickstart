from typing import Dict, Any
from agent.state import OverallState

def handle_end_plan(state: OverallState) -> Dict[str, Any]:
    """
    Constructs a planning result that marks planning as automatically approved and disables further planning.
    
    Parameters:
        state (OverallState): Accepted for API compatibility; not used by this handler.
    
    Returns:
        dict: A planning result containing:
            - planning_status (str): "auto_approved".
            - planning_steps (list): An empty list.
            - planning_feedback (list): A list with the message "Planning disabled via /end_plan.".
    """
    return {
        "planning_status": "auto_approved",
        "planning_steps": [],
        "planning_feedback": ["Planning disabled via /end_plan."],
    }

def handle_confirm_plan(state: OverallState) -> Dict[str, Any]:
    """
    Return a planning result that marks the current plan as confirmed.
    
    Returns:
        result (Dict[str, Any]): A dictionary with:
            - "planning_status": "confirmed"
            - "planning_feedback": a list containing "Plan confirmed. Proceeding to research."
    """
    return {
        "planning_status": "confirmed",
        "planning_feedback": ["Plan confirmed. Proceeding to research."]
    }

def handle_start_plan(state: OverallState) -> Dict[str, Any]:
    """
    Enter planning mode and mark the plan as awaiting confirmation.
    
    Returns:
        result (Dict[str, Any]): A planning result dictionary containing:
            - `planning_status`: the string "awaiting_confirmation".
            - `planning_feedback`: a list with the message "Planning mode started. Please review the plan."
    """
    return {
        "planning_status": "awaiting_confirmation",
        "planning_feedback": ["Planning mode started. Please review the plan."]
    }

def planning_router_logic(user_input: str, state: OverallState) -> str:
    """
    Route user input to the next planning node based on normalized command text.
    
    Parameters:
        user_input (str): The user's input; leading/trailing whitespace is ignored and comparison is case-insensitive.
        state (OverallState): Current agent state (not used by this router).
    
    Returns:
        str: The next node name — "planning_command_handler" when the input starts with "/end_plan", "/confirm_plan", or "/plan"; "continue" for any other input.
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