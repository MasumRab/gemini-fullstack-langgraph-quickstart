"""Dynamic Graph Builder for flexible agent composition.

Usage in notebooks:
    from agent.graph_builder import build_graph

    graph = build_graph(
        enable_planning=True,
        enable_reflection=True,
        enable_rag=False,
        enable_kg=False,
        enable_compression=True,
    )

    result = await graph.ainvoke(state, config)
"""

import os
from typing import Optional
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END

from agent.state import OverallState
from agent.configuration import Configuration
from agent.nodes import (
    load_context,
    generate_plan,
    continue_to_web_research,
    planning_mode,
    planning_wait,
    planning_router,
    web_research,
    validate_web_results,
    compression_node,
    reflection,
    finalize_answer,
    evaluate_research,
)

# Optional imports with graceful fallback
try:
    from agent.kg import kg_enrich
    KG_AVAILABLE = True
except ImportError:
    KG_AVAILABLE = False
    kg_enrich = None

try:
    from agent.rag_nodes import rag_retrieve, should_use_rag, rag_fallback_to_web
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    rag_retrieve = None

load_dotenv()


def build_graph(
    enable_planning: bool = False,
    enable_reflection: bool = True,
    enable_validation: bool = True,
    enable_compression: bool = False,
    enable_rag: bool = False,
    enable_kg: bool = False,
    parallel_search: bool = True,
    name: str = "custom-agent",
) -> StateGraph:
    """Build a customized agent graph based on feature flags.

    Args:
        enable_planning: Include planning mode for user review (default: False)
        enable_reflection: Include reflection loop for follow-up queries (default: True)
        enable_validation: Include web result validation (default: True)
        enable_compression: Include result compression (default: False)
        enable_rag: Include RAG retrieval node (default: False)
        enable_kg: Include Knowledge Graph enrichment (default: False)
        parallel_search: Use parallel Send for web research (default: True)
        name: Name for the compiled graph

    Returns:
        Compiled StateGraph ready for invocation

    Example:
        # Minimal graph (upstream-like)
        graph = build_graph(enable_planning=False, enable_reflection=False)

        # Standard planning graph
        graph = build_graph(enable_planning=True, enable_reflection=True)

        # Full enriched graph
        graph = build_graph(
            enable_planning=True,
            enable_reflection=True,
            enable_compression=True,
            enable_kg=True,
        )
    """
    builder = StateGraph(OverallState, config_schema=Configuration)

    # === Core Nodes (Always present) ===
    builder.add_node("load_context", load_context)
    builder.add_node("generate_plan", generate_plan)
    builder.add_node("web_research", web_research)
    builder.add_node("finalize_answer", finalize_answer)

    # === Optional Nodes ===
    if enable_planning:
        builder.add_node("planning_mode", planning_mode)
        builder.add_node("planning_wait", planning_wait)

    if enable_validation:
        builder.add_node("validate_web_results", validate_web_results)

    if enable_compression:
        builder.add_node("compression_node", compression_node)

    if enable_reflection:
        builder.add_node("reflection", reflection)

    if enable_rag and RAG_AVAILABLE and rag_retrieve:
        builder.add_node("rag_retrieve", rag_retrieve)

    if enable_kg and KG_AVAILABLE and kg_enrich:
        builder.add_node("kg_enrich", kg_enrich)

    # === Edges ===
    builder.add_edge(START, "load_context")
    builder.add_edge("load_context", "generate_plan")

    # After query generation: Planning or direct to search
    if enable_planning:
        builder.add_edge("generate_plan", "planning_mode")
        builder.add_conditional_edges(
            "planning_mode", planning_router, ["planning_wait", "web_research"]
        )
        builder.add_conditional_edges(
            "planning_wait", planning_router, ["planning_wait", "web_research"]
        )
    else:
        # No planning: fan out directly to web research
        if parallel_search:
            builder.add_conditional_edges(
                "generate_plan",
                continue_to_web_research,
                ["web_research"]
            )
        else:
            # Sequential: just connect
            builder.add_edge("generate_plan", "web_research")

    # === Post-Search Pipeline ===
    # Determine the chain: web_research -> [validation] -> [compression] -> [rag] -> [kg] -> [reflection] -> finalize

    current_node = "web_research"

    # Validation
    if enable_validation:
        builder.add_edge(current_node, "validate_web_results")
        current_node = "validate_web_results"

    # Compression (optional enrichment)
    if enable_compression:
        builder.add_edge(current_node, "compression_node")
        current_node = "compression_node"

    # RAG (optional enrichment)
    if enable_rag and RAG_AVAILABLE and rag_retrieve:
        builder.add_edge(current_node, "rag_retrieve")
        current_node = "rag_retrieve"

    # KG Enrichment (optional enrichment)
    if enable_kg and KG_AVAILABLE and kg_enrich:
        builder.add_edge(current_node, "kg_enrich")
        current_node = "kg_enrich"

    # Reflection or direct to finalize
    if enable_reflection:
        builder.add_edge(current_node, "reflection")
        builder.add_conditional_edges(
            "reflection", evaluate_research, ["web_research", "finalize_answer"]
        )
    else:
        builder.add_edge(current_node, "finalize_answer")

    builder.add_edge("finalize_answer", END)

    return builder.compile(name=name)


# === Preset Graphs ===

def upstream_graph():
    """Minimal graph: Query -> Search -> Answer."""
    return build_graph(
        enable_planning=False,
        enable_reflection=False,
        enable_validation=False,
        enable_compression=False,
        enable_rag=False,
        enable_kg=False,
        name="upstream-agent",
    )


def planning_graph():
    """Standard graph: + Planning + Reflection."""
    return build_graph(
        enable_planning=True,
        enable_reflection=True,
        enable_validation=True,
        enable_compression=False,
        enable_rag=False,
        enable_kg=False,
        name="planning-agent",
    )


def enriched_graph():
    """Full-featured graph: + KG + Compression."""
    return build_graph(
        enable_planning=True,
        enable_reflection=True,
        enable_validation=True,
        enable_compression=True,
        enable_rag=False,  # RAG is separate opt-in
        enable_kg=True,
        name="enriched-agent",
    )


def rag_graph():
    """RAG-enabled graph."""
    return build_graph(
        enable_planning=True,
        enable_reflection=True,
        enable_validation=True,
        enable_compression=False,
        enable_rag=True,
        enable_kg=False,
        name="rag-agent",
    )
