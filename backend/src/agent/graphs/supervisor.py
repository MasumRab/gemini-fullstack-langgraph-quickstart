from typing import Dict, Any, List
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from agent.state import OverallState
from agent.configuration import Configuration
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from config.app_config import config as app_config
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
    new_results = state.get("validated_web_research_result", [])
    current_results = state.get("web_research_result", [])

    # Combine all results
    all_results = current_results + new_results

    # If disabled, return full list
    if not app_config.compression_enabled:
        return {"web_research_result": all_results}

    # Deduplicate while preserving order
    unique_results = list(dict.fromkeys(all_results))

    combined_text = "\n\n".join(unique_results)

    # Truncate if too long
    max_chars = 30000
    if len(combined_text) > max_chars:
        combined_text = combined_text[:max_chars] + "\n[... truncated]"

    prompt = f"""
    Compress the following research notes into a concise running summary.
    CRITICAL: You MUST preserve all source citations in [Title](url) format.
    Do not lose any factual claims. Merge similar information.

    Notes:
    {combined_text}
    """

    try:
        llm = ChatGoogleGenerativeAI(
            model=app_config.model_compression,
            temperature=0,
            api_key=os.getenv("GEMINI_API_KEY"),
        )
        response = llm.invoke(prompt)
        compressed = response.content
        return {"web_research_result": [compressed]}
    except Exception as e:
        # Fallback
        return {"web_research_result": unique_results}

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
