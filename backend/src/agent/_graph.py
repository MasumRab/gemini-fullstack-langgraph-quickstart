"""
Alternative/Experimental Graph Implementation.

This module provides a standalone, multi-provider LangGraph workflow that can be used
for experimentation or as a fallback. It maintains compatibility with the main graph.py
but offers a simpler structure for testing new features.

Key differences from graph.py:
- Simplified node structure (no planning confirmation loop)
- Direct RAG integration via conditional edges
- Uses LLMFactory for model instantiation
- Suitable for CLI/notebook usage
"""

import os
import time
import json
import re
import logging
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END

from agent.state import OverallState, ReflectionState
from agent.configuration import Configuration
from agent.prompts import (
    query_writer_instructions,
    reflection_instructions,
    answer_instructions,
    get_current_date,
)
from agent.utils import get_research_topic, LLMFactory
from agent import rag_nodes

# Optional imports with graceful fallback
try:
    from agent.research_tools import TAVILY_AVAILABLE, tavily_search_multiple
except ImportError:
    TAVILY_AVAILABLE = False
    tavily_search_multiple = None

try:
    from google import genai
    from google.genai import types
    genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
except ImportError:
    genai_client = None

load_dotenv()

logger = logging.getLogger(__name__)


# =============================================================================
# Node Implementations (Simplified versions for experimental graph)
# =============================================================================

def generate_query(state: OverallState, config: RunnableConfig) -> Dict[str, Any]:
    """Generate search queries based on the user's question."""
    configurable = Configuration.from_runnable_config(config)
    
    messages = state.get("messages", [])
    research_topic = get_research_topic(messages) if messages else "General research"
    
    initial_count = state.get("initial_search_query_count", configurable.number_of_initial_queries)
    
    formatted_prompt = query_writer_instructions.format(
        current_date=get_current_date(),
        research_topic=research_topic,
        number_of_queries=initial_count,
    )
    
    llm = LLMFactory.create_llm(
        model_name=configurable.query_generator_model,
        temperature=1.0,
        max_retries=2,
    )
    
    try:
        result = llm.invoke(formatted_prompt)
        content = getattr(result, "content", str(result))
        
        # Parse queries from response
        queries = []
        for line in content.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                # Remove numbering like "1." or "- "
                cleaned = re.sub(r"^[\d\.\-\*\s]+", "", line).strip()
                if cleaned:
                    queries.append(cleaned)
        
        if not queries:
            queries = [research_topic]
        
        return {"search_query": queries[:initial_count]}
    except Exception as e:
        logger.error(f"Query generation failed: {e}")
        return {"search_query": [research_topic]}


def web_research(state: OverallState, config: RunnableConfig) -> Dict[str, Any]:
    """Perform web research using available search providers."""
    configurable = Configuration.from_runnable_config(config)
    
    search_query = state.get("search_query", [])
    if isinstance(search_query, list):
        query = search_query[-1] if search_query else ""
    else:
        query = search_query
    
    if not query:
        return {"web_research_result": [], "sources_gathered": []}
    
    # Try Tavily first if available
    if TAVILY_AVAILABLE and tavily_search_multiple and os.getenv("TAVILY_API_KEY"):
        try:
            results = tavily_search_multiple([query])
            formatted_results = []
            sources = []
            
            for result_set in results:
                for item in result_set.get("results", []):
                    content = item.get("content", "")
                    title = item.get("title", "")
                    url = item.get("url", "")
                    formatted_results.append(f"{content} [{title}]({url})")
                    sources.append({"title": title, "url": url, "snippet": content[:200]})
            
            return {
                "web_research_result": formatted_results,
                "sources_gathered": sources,
            }
        except Exception as e:
            logger.warning(f"Tavily search failed, falling back to Google: {e}")
    
    # Fallback to Google GenAI grounding
    if genai_client:
        try:
            response = genai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0,
                ),
            )
            
            grounding_metadata = None
            if response.candidates:
                grounding_metadata = getattr(response.candidates[0], "grounding_metadata", None)
            
            sources = []
            if grounding_metadata:
                chunks = getattr(grounding_metadata, "grounding_chunks", []) or []
                for chunk in chunks:
                    web_info = getattr(chunk, "web", None)
                    if web_info:
                        sources.append({
                            "title": getattr(web_info, "title", ""),
                            "url": getattr(web_info, "uri", ""),
                            "snippet": "",
                        })
            
            return {
                "web_research_result": [response.text] if response.text else [],
                "sources_gathered": sources,
            }
        except Exception as e:
            logger.error(f"Google search failed: {e}")
    
    return {"web_research_result": [], "sources_gathered": []}


def reflection(state: OverallState, config: RunnableConfig) -> Dict[str, Any]:
    """Identify knowledge gaps and propose follow-up queries."""
    configurable = Configuration.from_runnable_config(config)
    
    state["research_loop_count"] = state.get("research_loop_count", 0) + 1
    reasoning_model = state.get("reasoning_model", configurable.reflection_model)
    
    web_research_result = state.get("web_research_result", [])
    summaries_text = "\n\n---\n\n".join(web_research_result) if web_research_result else "No research content available."
    
    messages = state.get("messages", [])
    research_topic = get_research_topic(messages) if messages else "General research"
    
    formatted_prompt = reflection_instructions.format(
        current_date=get_current_date(),
        research_topic=research_topic,
        summaries=summaries_text,
    )
    
    llm = LLMFactory.create_llm(
        model_name=reasoning_model or configurable.reflection_model,
        temperature=1.0,
        max_retries=2,
    )
    
    result = llm.invoke(formatted_prompt)
    content = getattr(result, "content", str(result))
    
    # Parse reflection response
    is_sufficient = False
    knowledge_gap = ""
    follow_up_queries: List[str] = []
    
    try:
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        json_content = json_match.group(1) if json_match else content
        parsed = json.loads(json_content)
        is_sufficient = bool(parsed.get("is_sufficient", False))
        knowledge_gap = parsed.get("knowledge_gap", "")
        follow_up_raw = parsed.get("follow_up_queries", [])
        if isinstance(follow_up_raw, str):
            follow_up_queries = [follow_up_raw]
        elif isinstance(follow_up_raw, list):
            follow_up_queries = [str(q) for q in follow_up_raw if q]
    except (json.JSONDecodeError, KeyError, AttributeError):
        # Fallback parsing
        for line in content.strip().split("\n"):
            upper = line.upper().strip()
            if upper.startswith("SUFFICIENT"):
                is_sufficient = "YES" in upper or "TRUE" in upper
            elif upper.startswith("KNOWLEDGE_GAP"):
                knowledge_gap = line.split(":", 1)[-1].strip()
            elif upper.startswith("FOLLOW_UP"):
                rest = line.split(":", 1)[-1]
                follow_up_queries = [s.strip() for s in rest.split(",") if s.strip()]
    
    query_count = len(state.get("search_query", []) or [])
    
    return {
        "is_sufficient": is_sufficient,
        "knowledge_gap": knowledge_gap,
        "follow_up_queries": follow_up_queries,
        "research_loop_count": state["research_loop_count"],
        "number_of_ran_queries": query_count,
    }


def evaluate_research(state: ReflectionState, config: RunnableConfig) -> str:
    """Decide whether to continue researching or finalize the answer."""
    configurable = Configuration.from_runnable_config(config)
    max_loops = state.get("max_research_loops", configurable.max_research_loops)
    loop_count = state.get("research_loop_count", 0)
    
    if state.get("is_sufficient") or loop_count >= max_loops:
        return "finalize_answer"
    return "continue_research"


def continue_research(state: OverallState) -> Dict[str, Any]:
    """Route follow-up queries back into the research loop."""
    follow_up_queries = state.get("follow_up_queries", [])
    if not follow_up_queries:
        return {}
    
    next_query = follow_up_queries[0]
    return {
        "search_query": [next_query],
        "follow_up_queries": follow_up_queries[1:],
    }


def finalize_answer(state: OverallState, config: RunnableConfig) -> Dict[str, Any]:
    """Combine RAG documents and web research into the final answer."""
    configurable = Configuration.from_runnable_config(config)
    reasoning_model = state.get("reasoning_model") or configurable.answer_model
    
    all_summaries: List[str] = []
    
    # Include RAG documents if available
    rag_documents = state.get("rag_documents", [])
    for idx, doc in enumerate(rag_documents or []):
        labeled_doc = f"=== KNOWLEDGE BASE SOURCE {idx + 1} ===\n{doc}\n=== END KNOWLEDGE BASE SOURCE {idx + 1} ==="
        all_summaries.append(labeled_doc)
    
    # Include web research results
    web_research_result = state.get("web_research_result", [])
    for idx, result in enumerate(web_research_result or []):
        labeled_result = f"=== WEB RESEARCH SOURCE {idx + 1} ===\n{result}\n=== END WEB RESEARCH SOURCE {idx + 1} ==="
        all_summaries.append(labeled_result)
    
    summaries_text = "\n\n".join(all_summaries) if all_summaries else "No research content available."
    
    messages = state.get("messages", [])
    research_topic = get_research_topic(messages) if messages else "General research"
    
    formatted_prompt = answer_instructions.format(
        current_date=get_current_date(),
        research_topic=research_topic,
        summaries=summaries_text,
    )
    
    llm = LLMFactory.create_llm(
        model_name=reasoning_model or configurable.answer_model,
        temperature=0,
        max_retries=2,
    )
    
    result = llm.invoke(formatted_prompt)
    final_answer = getattr(result, "content", str(result))
    
    # Handle truncated responses
    response_metadata = getattr(result, "response_metadata", {})
    finish_reason = response_metadata.get("finish_reason")
    while finish_reason == "length":
        continuation = llm.invoke("Please continue from where you left off:\n" + final_answer[-500:])
        final_answer += "\n" + getattr(continuation, "content", str(continuation))
        response_metadata = getattr(continuation, "response_metadata", {})
        finish_reason = response_metadata.get("finish_reason")
        time.sleep(2)
    
    return {"messages": [AIMessage(content=final_answer)]}


# =============================================================================
# Graph Builder
# =============================================================================

def build_graph() -> StateGraph:
    """Build the experimental multi-provider LangGraph workflow."""
    workflow = StateGraph(OverallState, config_schema=Configuration)
    
    # Add nodes
    workflow.add_node("generate_query", generate_query)
    workflow.add_node("web_research", web_research)
    workflow.add_node("reflection", reflection)
    workflow.add_node("continue_research", continue_research)
    workflow.add_node("finalize_answer", finalize_answer)
    workflow.add_node("rag_retrieve", rag_nodes.rag_retrieve)
    
    # Define edges
    workflow.add_edge(START, "generate_query")
    
    # RAG routing: check if RAG should be used
    workflow.add_conditional_edges(
        "generate_query",
        rag_nodes.should_use_rag,
        {
            "rag_retrieve": "rag_retrieve",
            "web_research": "web_research",
        },
    )
    
    # After RAG, decide whether to also do web search
    workflow.add_conditional_edges(
        "rag_retrieve",
        rag_nodes.rag_fallback_to_web,
        {
            "web_research": "web_research",
            "reflection": "reflection",
        },
    )
    
    workflow.add_edge("web_research", "reflection")
    
    # Reflection routing
    workflow.add_conditional_edges(
        "reflection",
        evaluate_research,
        {
            "finalize_answer": "finalize_answer",
            "continue_research": "continue_research",
        },
    )
    
    # Continue research loops back via RAG check
    workflow.add_conditional_edges(
        "continue_research",
        rag_nodes.should_use_rag,
        {
            "rag_retrieve": "rag_retrieve",
            "web_research": "web_research",
        },
    )
    
    workflow.add_edge("finalize_answer", END)
    
    return workflow.compile(name="experimental-research-graph")


# Compile the graph at module level for easy import
research_graph = build_graph()

__all__ = ["research_graph", "build_graph"]
