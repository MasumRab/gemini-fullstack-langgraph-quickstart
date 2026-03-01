import logging
from typing import Any, Dict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from agent.configuration import Configuration
from agent.nodes import (
    evaluate_research,
    finalize_answer,
    generate_plan,
    load_context,
    planning_mode,
    planning_router,
    planning_wait,
    reflection,
    validate_web_results,
    web_research,
)
from agent.registry import graph_registry
from agent.state import OverallState
from agent.utils import get_cached_llm
from config.app_config import config as app_config

logger = logging.getLogger(__name__)


@graph_registry.describe(
    "compress_context",
    summary="Compresses search results into a concise knowledge graph/summary.",
    tags=["compression", "memory"],
    outputs=["web_research_result"],
)
def compress_context(state: OverallState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Produce a consolidated web research context by merging, deduplicating, and optionally compressing recent validated results.
    
    Merges the state's "validated_web_research_result" into the existing "web_research_result", preserving insertion order and removing duplicates. If compression is disabled, the merged list is returned unchanged. When compression is enabled in "tiered" mode, the merged results are compressed into a single summarized entry that preserves source citations and key factual claims; if compression fails, the merged list is returned instead.
    
    Returns:
        dict[str, Any]: A state fragment with the key "web_research_result". The value is either a list of deduplicated snippets (when compression is off or on failure) or a single-item list containing the compressed summary (when tiered compression succeeds).
    """
    # 1. Gather all results
    new_results = state.get("validated_web_research_result", [])
    current_results = state.get("web_research_result", [])

    # Combine and deduplicate (preserving order)
    combined = current_results + new_results
    unique_results = list(dict.fromkeys(combined))

    # 2. Check configuration
    if not app_config.compression_enabled:
        return {"web_research_result": unique_results}

    # 3. LLM Compression (if tiered/enabled)
    # We only compress if we have substantial content to justify the call
    # and if the mode is set to 'tiered' (or we just treat enabled as tiered for now)

    if app_config.compression_mode == "tiered":
        combined_text = "\n\n".join(unique_results)

        # Safety: avoid blowing context if it's massive
        max_chars = 50000
        if len(combined_text) > max_chars:
            combined_text = combined_text[:max_chars] + "\n[... truncated]"

        prompt = f"""
        You are an expert researcher.
        Compress the following research notes into a concise, dense summary.

        CRITICAL INSTRUCTIONS:
        1. YOU MUST PRESERVE all source citations in the [Title](url) format.
        2. Do not lose any key factual claims, numbers, or dates.
        3. Merge repetitive information.
        4. If the input is already concise, just return it as is.

        Research Notes:
        {combined_text}
        """

        try:
            # ⚡ Bolt Optimization: Use centralized cached factory
            llm = get_cached_llm(
                model=app_config.model_compression,
                temperature=0,
            )
            response = llm.invoke(prompt)
            compressed_content = response.content

            # We return the compressed summary as a single item list
            # to replace the long list of snippets.
            return {"web_research_result": [compressed_content]}

        except Exception as e:
            logger.warning(
                f"Compression failed in supervisor: {e}. Returning uncompressed history."
            )
            return {"web_research_result": unique_results}

    # Default fallback
    return {"web_research_result": unique_results}


builder = StateGraph(OverallState, config_schema=Configuration)
builder.add_node("load_context", load_context)
builder.add_node("generate_plan", generate_plan)
builder.add_node("planning_mode", planning_mode)
builder.add_node("planning_wait", planning_wait)
builder.add_node("web_research", web_research)
builder.add_node("validate_web_results", validate_web_results)
builder.add_node("compress_context", compress_context)  # The new node
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
builder.add_edge("validate_web_results", "compress_context")  # Inject compression
builder.add_edge("compress_context", "reflection")  # Reflect on compressed context
builder.add_conditional_edges(
    "reflection", evaluate_research, ["web_research", "finalize_answer"]
)
builder.add_edge("finalize_answer", END)

graph = builder.compile(name="pro-search-agent-supervisor")
