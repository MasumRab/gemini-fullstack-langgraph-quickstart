import os
from dotenv import load_dotenv

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
    evaluate_research,
)

load_dotenv()

# Planning Graph: Includes Planning, Validation, Reflection.
# No KG Enrichment. No Compression.

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

# Skip Compression/KG, go straight to Reflection
builder.add_edge("validate_web_results", "reflection")

builder.add_conditional_edges(
    "reflection", evaluate_research, ["web_research", "finalize_answer"]
)
builder.add_edge("finalize_answer", END)

graph = builder.compile(name="pro-search-agent-planning")
