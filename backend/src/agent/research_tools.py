"""Research Tools and Search Utilities.

This module provides search, summarization, and reflection tools for the research agent.
Adapted from open_deep_research and thinkdepthai examples for the Gemini backend.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Annotated, Any, Dict, List, Literal, Optional

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool

# Try to import Tavily client, fall back to None if not available
try:
    from tavily import TavilyClient, AsyncTavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    TavilyClient = None
    AsyncTavilyClient = None

from agent.prompts import summarize_webpage_prompt


# =============================================================================
# Utility Functions
# =============================================================================

def get_today_str() -> str:
    """
    Return the current local date formatted like 'Sun Dec 8, 2024'.
    
    Returns:
        The current date as a string in the form "DayAbbrev MonthAbbrev DD, YYYY" (e.g., "Sun Dec 8, 2024").
    """
    return datetime.now().strftime("%a %b %d, %Y")


def get_tavily_api_key(config: Optional[RunnableConfig] = None) -> str:
    """Retrieve Tavily API key from config or environment.

    Args:
        config: Optional runtime configuration

    Returns:
        Tavily API key string

    Raises:
        ValueError: If no API key is found
    """
    # Try config first
    if config:
        configurable = config.get("configurable", {})
        if key := configurable.get("tavily_api_key"):
            return key

    # Fall back to environment variable
    key = os.getenv("TAVILY_API_KEY")
    if key:
        return key

    raise ValueError("Tavily API key not found in config or environment")


# =============================================================================
# Search Functions
# =============================================================================

def tavily_search_multiple(
    search_queries: List[str],
    max_results: int = 3,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = True,
    config: Optional[RunnableConfig] = None,
) -> List[dict]:
    """
    Perform Tavily searches for multiple queries and return their raw results.
    
    Performs a separate Tavily search for each string in `search_queries` and returns a list of result dictionaries in the same order. If the Tavily client is unavailable, an empty list is returned. If an individual query fails, its entry will include the original `query` and an empty `results` list.
    
    Parameters:
        search_queries (List[str]): Queries to execute.
        max_results (int): Maximum number of results to return per query.
        topic (Literal["general", "news", "finance"]): Topic filter applied to each search.
        include_raw_content (bool): If True, request raw webpage content in results when available.
        config (Optional[RunnableConfig]): Optional runtime configuration used to obtain the Tavily API key.
    
    Returns:
        List[dict]: A list of result dictionaries (one per query). Each dictionary typically contains the originating `query` and a `results` list (empty on per-query failure).
    """
    if not TAVILY_AVAILABLE:
        logging.warning("Tavily client not available, returning empty results")
        return []

    api_key = get_tavily_api_key(config)
    tavily_client = TavilyClient(api_key=api_key)

    search_docs = []
    for query in search_queries:
        try:
            result = tavily_client.search(
                query,
                max_results=max_results,
                include_raw_content=include_raw_content,
                topic=topic
            )
            search_docs.append(result)
        except Exception as e:
            logging.error(f"Search failed for query '{query}': {e}")
            search_docs.append({"query": query, "results": []})

    return search_docs


async def tavily_search_async(
    search_queries: List[str],
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = True,
    config: Optional[RunnableConfig] = None,
) -> List[dict]:
    """
    Perform multiple Tavily searches concurrently and return the results for each query.
    
    If the Tavily client is unavailable, returns an empty list. For individual query failures, the corresponding entry will be a dictionary of the form {"query": <original_query>, "results": []}.
    
    Parameters:
        search_queries (List[str]): Queries to execute.
        max_results (int): Maximum number of results to request per query.
        topic (Literal["general", "news", "finance"]): Topic category to filter results.
        include_raw_content (bool): If True, include full webpage content in each result when available.
        config (Optional[RunnableConfig]): Optional runtime configuration used to obtain the Tavily API key.
    
    Returns:
        List[dict]: A list of per-query result dictionaries returned by the Tavily API or placeholder dictionaries for failed queries.
    """
    if not TAVILY_AVAILABLE:
        logging.warning("Tavily async client not available, returning empty results")
        return []

    api_key = get_tavily_api_key(config)
    tavily_client = AsyncTavilyClient(api_key=api_key)

    search_tasks = [
        tavily_client.search(
            query,
            max_results=max_results,
            include_raw_content=include_raw_content,
            topic=topic
        )
        for query in search_queries
    ]

    search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

    # Filter out exceptions and log them
    valid_results = []
    for i, result in enumerate(search_results):
        if isinstance(result, Exception):
            logging.error(f"Async search failed for query '{search_queries[i]}': {result}")
            valid_results.append({"query": search_queries[i], "results": []})
        else:
            valid_results.append(result)

    return valid_results


# =============================================================================
# Deduplication and Processing
# =============================================================================

def deduplicate_search_results(search_results: List[dict]) -> Dict[str, dict]:
    """
    Deduplicates search result entries by URL.
    
    Parameters:
        search_results (List[dict]): List of search response dictionaries, each expected to have a "results" list of result dicts and an optional "query" field.
    
    Returns:
        Dict[str, dict]: Mapping from URL to a unique result dictionary. Each stored result is the original result dict augmented with a "query" key containing the originating search query.
    """
    unique_results = {}

    for response in search_results:
        for result in response.get("results", []):
            url = result.get("url", "")
            if url and url not in unique_results:
                unique_results[url] = {
                    **result,
                    "query": response.get("query", "")
                }

    return unique_results


def process_search_results(
    unique_results: Dict[str, dict],
    summarization_model: Optional[BaseChatModel] = None,
    max_content_length: int = 250000,
) -> Dict[str, dict]:
    """
    Process search results and produce a summary entry for each unique URL.
    
    For each input result, uses the provided summarization model to summarize the raw content up to max_content_length when both raw content and a model are available; if raw content is missing the function falls back to the short snippet, and if a model is not provided it truncates the raw content to max_content_length.
    
    Parameters:
        unique_results: Mapping from URL to the original search result dictionary. Each result may include 'raw_content', 'content' (short snippet), and 'title'.
        summarization_model: Optional chat model used to generate a concise summary of raw content when available.
        max_content_length: Maximum number of characters of raw content to consider for summarization or truncation.
    
    Returns:
        dict: Mapping from URL to a processed result dictionary with keys:
            - 'title': the result title (or "Untitled" if missing)
            - 'content': the summarized text, fallback snippet, or truncated raw content
    """
    summarized_results = {}

    for url, result in unique_results.items():
        raw_content = result.get("raw_content", "")

        if not raw_content:
            # No raw content, use the short snippet
            content = result.get("content", "")
        elif summarization_model:
            # Summarize raw content
            content = summarize_webpage_content(
                summarization_model,
                raw_content[:max_content_length]
            )
        else:
            # No model, just truncate
            content = raw_content[:max_content_length]

        summarized_results[url] = {
            "title": result.get("title", "Untitled"),
            "content": content
        }

    return summarized_results


def format_search_output(summarized_results: Dict[str, dict]) -> str:
    """
    Format processed search results into a readable multi-source text block.
    
    Parameters:
        summarized_results (Dict[str, dict]): Mapping from URL to a result dictionary that must contain the keys `"title"` and `"content"`, where `"title"` is the source title and `"content"` is the summary text.
    
    Returns:
        A single string containing numbered source sections; each section includes the source title, URL, and summary. If `summarized_results` is empty, returns a short message indicating that no valid results were found.
    """
    if not summarized_results:
        return "No valid search results found. Please try different search queries."

    formatted_output = "Search results:\n\n"

    for i, (url, result) in enumerate(summarized_results.items(), 1):
        formatted_output += f"\n--- SOURCE {i}: {result['title']} ---\n"
        formatted_output += f"URL: {url}\n\n"
        formatted_output += f"SUMMARY:\n{result['content']}\n\n"
        formatted_output += "-" * 80 + "\n"

    return formatted_output


# =============================================================================
# Summarization
# =============================================================================

def summarize_webpage_content(
    model: BaseChatModel,
    webpage_content: str,
    timeout: float = 60.0,
) -> str:
    """
    Produce a human-readable summary of webpage content, including key excerpts when available.
    
    Parameters:
        model (BaseChatModel): Chat model used to generate the summary.
        webpage_content (str): Raw HTML or text content of the webpage to summarize.
        timeout (float): Maximum allowed time for summarization (seconds). Note: not all models enforce this parameter.
    
    Returns:
        summary (str): If the model returns structured fields `summary` and `key_excerpts`, returns them formatted as
        "<summary>...</summary>\n\n<key_excerpts>...</key_excerpts>". Otherwise returns the model's plain-text response. If summarization fails, returns the original `webpage_content` truncated to 1000 characters with "..." appended when truncated.
    """
    try:
        prompt_content = summarize_webpage_prompt.format(
            webpage_content=webpage_content,
            date=get_today_str()
        )

        summary = model.invoke([HumanMessage(content=prompt_content)])

        # Handle structured output
        if hasattr(summary, "summary") and hasattr(summary, "key_excerpts"):
            formatted_summary = (
                f"<summary>\n{summary.summary}\n</summary>\n\n"
                f"<key_excerpts>\n{summary.key_excerpts}\n</key_excerpts>"
            )
        else:
            # Plain text response
            formatted_summary = str(summary.content if hasattr(summary, "content") else summary)

        return formatted_summary

    except Exception as e:
        logging.warning(f"Summarization failed: {e}")
        # Return truncated original content
        if len(webpage_content) > 1000:
            return webpage_content[:1000] + "..."
        return webpage_content


async def summarize_webpage_async(
    model: BaseChatModel,
    webpage_content: str,
    timeout: float = 60.0,
) -> str:
    """
    Produce a concise, formatted summary and key excerpts for the given webpage content.
    
    If the model returns structured fields `summary` and `key_excerpts`, the result is formatted with `<summary>` and `<key_excerpts>` blocks; otherwise the raw text response is returned. On timeout or other failure, returns the original content truncated to 1000 characters with an ellipsis when longer.
    
    Parameters:
        timeout (float): Maximum seconds to wait for the model response.
    
    Returns:
        str: Formatted summary or truncated original content on failure.
    """
    try:
        prompt_content = summarize_webpage_prompt.format(
            webpage_content=webpage_content,
            date=get_today_str()
        )

        summary = await asyncio.wait_for(
            model.ainvoke([HumanMessage(content=prompt_content)]),
            timeout=timeout
        )

        # Handle structured output
        if hasattr(summary, "summary") and hasattr(summary, "key_excerpts"):
            formatted_summary = (
                f"<summary>\n{summary.summary}\n</summary>\n\n"
                f"<key_excerpts>\n{summary.key_excerpts}\n</key_excerpts>"
            )
        else:
            formatted_summary = str(summary.content if hasattr(summary, "content") else summary)

        return formatted_summary

    except asyncio.TimeoutError:
        logging.warning(f"Summarization timed out after {timeout} seconds")
        return webpage_content[:1000] + "..." if len(webpage_content) > 1000 else webpage_content
    except Exception as e:
        logging.warning(f"Async summarization failed: {e}")
        return webpage_content[:1000] + "..." if len(webpage_content) > 1000 else webpage_content


# =============================================================================
# Tool Definitions
# =============================================================================

TAVILY_SEARCH_DESCRIPTION = (
    "A search engine optimized for comprehensive, accurate, and trusted results. "
    "Useful for answering questions about current events and gathering research data."
)


@tool(description=TAVILY_SEARCH_DESCRIPTION)
def tavily_search(
    query: str,
    max_results: Annotated[int, InjectedToolArg] = 3,
    topic: Annotated[Literal["general", "news", "finance"], InjectedToolArg] = "general",
) -> str:
    """
    Perform a Tavily search for a single query, deduplicate and process results, and return a formatted summary string.
    
    Parameters:
        query (str): The search query to execute.
        max_results (int): Maximum number of results to return.
        topic (Literal['general', 'news', 'finance']): Topic filter to apply to the search.
    
    Returns:
        str: Formatted text with headers for each source and their summaries, or a message indicating no valid results.
    """
    # Execute search for single query
    search_results = tavily_search_multiple(
        [query],
        max_results=max_results,
        topic=topic,
        include_raw_content=True,
    )

    # Deduplicate results by URL
    unique_results = deduplicate_search_results(search_results)

    # Process results (without summarization model for simplicity)
    summarized_results = process_search_results(unique_results)

    # Format output
    return format_search_output(summarized_results)


THINK_TOOL_DESCRIPTION = (
    "Strategic reflection tool for research planning. "
    "Use after each search to analyze results and plan next steps."
)


@tool(description=THINK_TOOL_DESCRIPTION)
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making.

    Use this tool after each search to analyze results and plan next steps systematically.
    This creates a deliberate pause in the research workflow for quality decision-making.

    When to use:
    - After receiving search results: What key information did I find?
    - Before deciding next steps: Do I have enough to answer comprehensively?
    - When assessing research gaps: What specific information am I still missing?
    - Before concluding research: Can I provide a complete answer now?

    Reflection should address:
    1. Analysis of current findings - What concrete information have I gathered?
    2. Gap assessment - What crucial information is still missing?
    3. Quality evaluation - Do I have sufficient evidence/examples for a good answer?
    4. Strategic decision - Should I continue searching or provide my answer?

    Args:
        reflection: Your detailed reflection on research progress, findings, gaps, and next steps

    Returns:
        Confirmation that reflection was recorded for decision-making
    """
    return f"Reflection recorded: {reflection}"


@tool(description="Refine and improve a draft research report")
def refine_draft_report(
    research_brief: Annotated[str, InjectedToolArg],
    findings: Annotated[str, InjectedToolArg],
    draft_report: Annotated[str, InjectedToolArg],
) -> str:
    """
    Refine a draft research report by synthesizing findings and producing an improved report.
    
    Incorporates key findings, improves clarity and structure, adds relevant citations drawn from the findings, and fixes factual inconsistencies.
    
    Returns:
        Refined report text incorporating the findings and revisions.
    """
    # Use default model for refinement
    writer_model = init_chat_model(model="gemini-2.5-flash", max_tokens=16000)

    prompt = f"""You are refining a research report based on the following:

## Research Brief
{research_brief}

## Findings
{findings}

## Current Draft
{draft_report}

## Instructions
Please improve this draft by:
1. Ensuring all key findings are incorporated
2. Improving clarity and structure
3. Adding relevant citations from the findings
4. Fixing any factual inconsistencies
5. Making the report more comprehensive

Today's date: {get_today_str()}

Provide the refined report:
"""

    response = writer_model.invoke([HumanMessage(content=prompt)])
    return response.content


# =============================================================================
# Token Limit Detection
# =============================================================================

def is_token_limit_exceeded(exception: Exception, model_name: str = None) -> bool:
    """
    Detect whether an exception indicates that a model's token or context length limit was exceeded.
    
    Parameters:
        exception (Exception): The exception to analyze.
        model_name (str, optional): Model identifier to help recognize provider-specific error messages.
    
    Returns:
        `true` if the exception text suggests a token or context-limit error, `false` otherwise.
    """
    error_str = str(exception).lower()

    # Common token limit error patterns
    token_keywords = [
        "token limit",
        "context length",
        "maximum context",
        "too long",
        "reduce the length",
        "exceeds the maximum",
        "prompt is too long",
        "resource exhausted",
    ]

    return any(keyword in error_str for keyword in token_keywords)


# =============================================================================
# Model Token Limits Reference
# =============================================================================

MODEL_TOKEN_LIMITS = {
    # OpenAI Models
    "openai:gpt-4o": 128000,
    "openai:gpt-4o-mini": 128000,
    "openai:gpt-4-turbo": 128000,
    "openai:o1": 200000,
    "openai:o1-mini": 128000,

    # Anthropic Models
    "anthropic:claude-3-5-sonnet": 200000,
    "anthropic:claude-3-opus": 200000,
    "anthropic:claude-3-haiku": 200000,

    # Google/Gemini Models
    # Gemini 1.5 series (legacy, retiring April 2025)
    "google:gemini-1.5-pro": 2097152,
    "google:gemini-1.5-flash": 1048576,
    "gemini-1.5-pro": 2097152,
    "gemini-1.5-flash": 1048576,
    # Gemini 2.0 series
    "google:gemini-2.0-flash": 1048576,
    "gemini-2.0-flash": 1048576,
    "gemini-2.0-flash-exp": 1048576,
    "gemini-2.0-pro": 2097152,
    # Gemini 2.5 series (current stable)
    "google:gemini-2.5-flash": 1048576,
    "gemini-2.5-flash": 1048576,
    "gemini-2.5-flash-lite": 1048576,
    "google:gemini-2.5-pro": 2097152,
    "gemini-2.5-pro": 2097152,
}


def get_model_token_limit(model_name: str) -> int:
    """
    Look up the token limit for a model identifier.
    
    Parameters:
        model_name (str): Model identifier to query (e.g., 'gpt-4', 'gemini-2.5-flash').
    
    Returns:
        int: The token limit for the specified model; defaults to 128000 if the model is not found.
    """
    return MODEL_TOKEN_LIMITS.get(model_name, 128000)