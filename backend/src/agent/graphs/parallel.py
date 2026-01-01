from langgraph.graph import StateGraph, START, END
from agent.state import OverallState
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
    finalize_answer,
    evaluate_research
)
from agent.registry import graph_registry

# Create our Agent Graph using the standard builder wiring
builder = StateGraph(OverallState, config_schema=Configuration)
builder.add_node("load_context", load_context)
builder.add_node("generate_plan", generate_plan)
builder.add_node("planning_mode", planning_mode)
builder.add_node("planning_wait", planning_wait)
builder.add_node("web_research", web_research)
builder.add_node("validate_web_results", validate_web_results)
builder.add_node("reflection", reflection)
builder.add_node("finalize_answer", finalize_answer)

builder.add_edge(START, "load_context")
builder.add_edge("load_context", "generate_plan")
builder.add_edge("generate_plan", "planning_mode")
builder.add_conditional_edges(
    "planning_mode", planning_router, ["planning_wait", "web_research"]
)
builder.add_conditional_edges(
    "planning_wait", planning_router, ["planning_wait", "web_research"]
)
builder.add_edge("web_research", "validate_web_results")
builder.add_edge("validate_web_results", "reflection")
builder.add_conditional_edges(
    "reflection", evaluate_research, ["web_research", "finalize_answer"]
)
builder.add_edge("finalize_answer", END)

# Document edges (metadata only)
graph_registry.document_edge("generate_plan", "planning_mode", description="Initial plan is prepared for user review.")
graph_registry.document_edge("planning_mode", "web_research", description="Once approved (or auto-approved), plan steps dispatch to web research.")
graph_registry.document_edge("planning_mode", "planning_wait", description="If confirmation is required, execution pauses for user feedback.")
graph_registry.document_edge("web_research", "validate_web_results", description="Heuristic validation guards against irrelevant summaries.")
graph_registry.document_edge("validate_web_results", "reflection", description="Only validated summaries reach the reasoning loop.")
graph_registry.document_edge("reflection", "web_research", description="Follow-up queries trigger additional web searches until sufficient.")
graph_registry.document_edge("reflection", "finalize_answer", description="Once sufficient or max loops reached, finalize the response.")
graph_registry.document_edge("finalize_answer", END, description="Graph terminates after final answer is produced.")

graph = builder.compile(name="pro-search-agent-parallel")
