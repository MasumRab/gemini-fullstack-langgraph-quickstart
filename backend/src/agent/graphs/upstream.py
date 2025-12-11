import os
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END

from agent.state import OverallState
from agent.configuration import Configuration
from agent.registry import graph_registry
from agent.nodes import (
    load_context,
    generate_query,
    planning_mode,
    planning_wait,
    planning_router,
    web_research,
    validate_web_results,
    reflection,
    finalize_answer,
    evaluate_research,
)

# Load env but don't crash on missing keys here
load_dotenv()

# Create upstream builder
builder = StateGraph(OverallState, config_schema=Configuration)

builder.add_node("load_context", load_context)
builder.add_node("generate_query", generate_query)
builder.add_node("planning_mode", planning_mode)
builder.add_node("planning_wait", planning_wait)
builder.add_node("web_research", web_research)
builder.add_node("validate_web_results", validate_web_results)
builder.add_node("reflection", reflection)
builder.add_node("finalize_answer", finalize_answer)

builder.add_edge(START, "load_context")
builder.add_edge("load_context", "generate_query")
builder.add_edge("generate_query", "planning_mode")
builder.add_conditional_edges(
    "planning_mode", planning_router, ["planning_wait", "web_research"]
)
builder.add_conditional_edges(
    "planning_wait", planning_router, ["planning_wait", "web_research"]
)
builder.add_edge("web_research", "validate_web_results")

# Upstream Simpler Flow: Skip Compression and KG Enrichment
builder.add_edge("validate_web_results", "reflection")

builder.add_conditional_edges(
    "reflection", evaluate_research, ["web_research", "finalize_answer"]
)
builder.add_edge("finalize_answer", END)

# Compile
graph = builder.compile(name="pro-search-agent-upstream")
