from typing import Dict, Any, List
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from agent.state import OverallState, ReflectionState
from agent.configuration import Configuration
from agent.nodes import (
    load_context,
    generate_plan,
    planning_mode,
    planning_wait,
    planning_router,
    web_research,
    validate_web_results,
    reflection,
    finalize_answer
)
from agent.registry import graph_registry

# Override evaluate_research to avoid Send (parallelism)
@graph_registry.describe(
    "evaluate_research_linear",
    summary="Routing policy for linear execution (no parallel Send).",
    tags=["routing", "policy"],
)
def evaluate_research_linear(state: ReflectionState, config: RunnableConfig) -> str:
    """Decides next step: 'web_research' (loop) or 'finalize_answer'."""
    configurable = Configuration.from_runnable_config(config)
    max_loops = state.get("max_research_loops") or configurable.max_research_loops

    if state["is_sufficient"] or state["research_loop_count"] >= max_loops:
        return "finalize_answer"

    # In linear mode, we just loop back to web_research.
    # The 'web_research' node needs to be smart enough to pick the *next* query
    # from the list if there are multiple, or just use the follow-up queries.
    return "web_research"

# Helper to process queries one by one
@graph_registry.describe(
    "queue_manager",
    summary="Manages the queue of queries for strict linear execution.",
    tags=["queue", "linear"],
)
def queue_manager(state: OverallState) -> Dict[str, Any]:
    """Prepares the next query for the single-threaded web_research node.

    In parallel mode, 'Send' distributes all queries.
    In linear mode, we need to pick one.
    """
    # Logic:
    # 1. If we have 'follow_up_queries' from reflection, use the first one.
    # 2. Else if we have initial 'search_query' list, use the next pending one.
    # For simplicity in this 'Strict Linear' variant, we assumes 'search_query'
    # in state is the *current* single query being worked on.

    # If we are coming from Reflection with follow-ups:
    follow_ups = state.get("follow_up_queries", [])
    if follow_ups:
        next_q = follow_ups[0]
        # Push remaining to a queue if we wanted advanced queueing,
        # but for now we just take the first follow-up.
        return {"search_query": next_q, "follow_up_queries": follow_ups[1:]}

    # If we are coming from Generate Query (list of queries),
    # the 'generate_plan' node outputs a list.
    # We might need a 'dispatcher' node if we want to process the *initial* list linearly.
    # However, 'web_research' expects 'search_query' to be a single string or list.

    # To strictly linearize the *initial* batch (which 'continue_to_web_research' usually fans out),
    # we would need a loop structure.
    # For Phase 1, we will simplify: Linear mode treats the *entire* initial list
    # as a single context or just takes the first one.
    # Or better: We assume 'search_query' is updated to be the single query to run.

    return {}

builder = StateGraph(OverallState, config_schema=Configuration)
builder.add_node("load_context", load_context)
builder.add_node("generate_plan", generate_plan)
builder.add_node("planning_mode", planning_mode)
builder.add_node("planning_wait", planning_wait)

# In linear mode, we might need a specific 'dispatcher' to handle the list -> item conversion
# But for now, we wire similarly, assuming 'web_research' can handle the state.
builder.add_node("web_research", web_research)
builder.add_node("validate_web_results", validate_web_results)
builder.add_node("reflection", reflection)
builder.add_node("finalize_answer", finalize_answer)

builder.add_edge(START, "load_context")
builder.add_edge("load_context", "generate_plan")
builder.add_edge("generate_plan", "planning_mode")

# Modified routing for planning
builder.add_conditional_edges(
    "planning_mode",
    planning_router,
    ["planning_wait", "web_research"]
)
builder.add_conditional_edges(
    "planning_wait",
    planning_router,
    ["planning_wait", "web_research"]
)

builder.add_edge("web_research", "validate_web_results")
builder.add_edge("validate_web_results", "reflection")

# Use linear evaluation (returns string "web_research" or "finalize_answer")
builder.add_conditional_edges(
    "reflection",
    evaluate_research_linear,
    ["web_research", "finalize_answer"]
)

builder.add_edge("finalize_answer", END)

graph = builder.compile(name="pro-search-agent-linear")
