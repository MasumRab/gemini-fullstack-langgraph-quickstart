from typing import Dict, Any, List
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from agent.state import OverallState
from agent.configuration import Configuration
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
    evaluate_research
)
from agent.registry import graph_registry

@graph_registry.describe(
    "compress_context",
    summary="Compresses search results into a concise knowledge graph/summary.",
    tags=["compression", "memory"],
    outputs=["web_research_result"],
)
def compress_context(state: OverallState, config: RunnableConfig) -> Dict[str, Any]:
    """Summarizes the current batch of web research results to prevent context bloat.

    Instead of appending to an ever-growing list, this node:
    1. Takes the new 'validated_web_research_result'.
    2. Merges it with existing 'web_research_result' (history).
    3. Uses an LLM to summarize/deduplicate into a 'Running Summary'.
    """
    # For Phase 2 Prototype: Simple concatenation/truncation or lightweight summary.
    # In a full implementation, this would call an LLM.

    new_results = state.get("validated_web_research_result", [])
    current_results = state.get("web_research_result", [])

    # Simple compression: Keep unique items, maybe limit total count
    all_results = current_results + new_results

    # TODO: Add actual LLM summarization here.
    # For now, we tag them as 'Compressed' to prove the architecture flow.
    compressed = [f"[Compressed] {r[:100]}..." for r in new_results]

    # We replace the raw results with the compressed version + full history if needed,
    # or just keep the 'Running Summary' as the main context.
    # Here we append to keep history but formatted differently.

    return {
        "web_research_result": all_results # Placeholder for actual compression logic
    }

builder = StateGraph(OverallState, config_schema=Configuration)
builder.add_node("load_context", load_context)
builder.add_node("generate_query", generate_query)
builder.add_node("planning_mode", planning_mode)
builder.add_node("planning_wait", planning_wait)
builder.add_node("web_research", web_research)
builder.add_node("validate_web_results", validate_web_results)
builder.add_node("compress_context", compress_context) # The new node
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
builder.add_edge("validate_web_results", "compress_context") # Inject compression
builder.add_edge("compress_context", "reflection") # Reflect on compressed context
builder.add_conditional_edges(
    "reflection", evaluate_research, ["web_research", "finalize_answer"]
)
builder.add_edge("finalize_answer", END)

graph = builder.compile(name="pro-search-agent-supervisor")
