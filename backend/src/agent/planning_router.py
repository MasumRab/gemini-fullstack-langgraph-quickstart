from typing import Any, Dict

from agent.state import OverallState


def handle_end_plan(state: OverallState) -> Dict[str, Any]:
    """
    Builds the response payload for ending planning mode.
    
    Parameters:
        state (OverallState): Current overall state; this function does not modify it.
    
    Returns:
        result (Dict[str, Any]): Dictionary with:
            - `planning_status`: `"auto_approved"`.
            - `planning_steps`: empty list.
            - `planning_feedback`: list containing the message `"Planning disabled via /end_plan."`.
    """
    return {
        "planning_status": "auto_approved",
        "planning_steps": [],
        "planning_feedback": ["Planning disabled via /end_plan."],
    }


def handle_confirm_plan(state: OverallState) -> Dict[str, Any]:
    """
    Builds the response dictionary for confirming a plan without mutating the provided state.
    
    Parameters:
        state (OverallState): Current agent state (not modified).
    
    Returns:
        Dict[str, Any]: Response containing:
            - `planning_status`: "confirmed"
            - `planning_feedback`: list with a single confirmation message
    """
    return {
        "planning_status": "confirmed",
        "planning_feedback": ["Plan confirmed. Proceeding to research."],
    }


def handle_start_plan(state: OverallState) -> Dict[str, Any]:
    """
    Enter planning mode and await user confirmation.
    
    Returns:
        dict: Contains `planning_status` set to `"awaiting_confirmation"` and `planning_feedback` with a single message prompting the user to review the plan.
    """
    return {
        "planning_status": "awaiting_confirmation",
        "planning_feedback": ["Planning mode started. Please review the plan."],
    }


def planning_router_logic(user_input: str, state: OverallState) -> str:
    """
    Determine the next node name for planning-related user input.
    
    Parameters:
        user_input (str): Raw user input to examine; leading/trailing whitespace is ignored and matching is case-insensitive.
        state (OverallState): Current overall state (inspected but not mutated by this function).
    
    Returns:
        str: `'planning_command_handler'` if the input starts with `/end_plan`, `/confirm_plan`, or `/plan`; `'continue'` otherwise.
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
