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
    compression_node,  # New Node
    reflection,
    finalize_answer,
    evaluate_research,
)
from agent.kg import kg_enrich # New Node

# Ensure config is loaded
from backend.src.config.app_config import config

load_dotenv()

if os.getenv("GEMINI_API_KEY") is None:
    raise ValueError("GEMINI_API_KEY is not set")

# Create our Agent Graph using the standard builder wiring
builder = StateGraph(OverallState, config_schema=Configuration)
builder.add_node("load_context", load_context)
builder.add_node("generate_query", generate_query)
builder.add_node("planning_mode", planning_mode)
builder.add_node("planning_wait", planning_wait)
builder.add_node("web_research", web_research)
builder.add_node("validate_web_results", validate_web_results)
builder.add_node("compression_node", compression_node) # Add Compression
builder.add_node("kg_enrich", kg_enrich) # Add KG Pilot
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

# Pipeline: Validate -> Compression -> KG Enrich -> Reflection
builder.add_edge("validate_web_results", "compression_node")
builder.add_edge("compression_node", "kg_enrich")
builder.add_edge("kg_enrich", "reflection")

builder.add_conditional_edges(
    "reflection", evaluate_research, ["web_research", "finalize_answer"]
)
builder.add_edge("finalize_answer", END)

# Document edges for registry/tooling
graph_registry.document_edge(
    "generate_query",
    "planning_mode",
    description="Initial queries are summarized into a plan for user review.",
)
graph_registry.document_edge(
    "planning_mode",
    "web_research",
    description="Once approved (or auto-approved), plan steps dispatch to web research.",
)
graph_registry.document_edge(
    "planning_mode",
    "planning_wait",
    description="If confirmation is required, execution pauses for user feedback.",
)
graph_registry.document_edge(
    "web_research",
    "validate_web_results",
    description="Heuristic validation guards against irrelevant summaries.",
)
graph_registry.document_edge(
    "validate_web_results",
    "compression_node",
    description="Validated results are compressed/summarized.",
)
graph_registry.document_edge(
    "compression_node",
    "kg_enrich",
    description="Compressed results are optionally enriched into KG.",
)
graph_registry.document_edge(
    "kg_enrich",
    "reflection",
    description="Enriched/Compressed results reach the reasoning loop.",
)
graph_registry.document_edge(
    "reflection",
    "web_research",
    description="Follow-up queries trigger additional web searches until sufficient.",
)
graph_registry.document_edge(
    "reflection",
    "finalize_answer",
    description="Once sufficient or max loops reached, finalize the response.",
)
graph_registry.document_edge(
    "finalize_answer",
    END,
    description="Graph terminates after final answer is produced.",
)

graph = builder.compile(name="pro-search-agent")
