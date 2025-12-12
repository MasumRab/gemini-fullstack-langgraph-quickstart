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
    """Get current date in a human-readable format.

    Returns:
        Formatted date string (e.g., 'Sun Dec 8, 2024')
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
    """Perform search using Tavily API for multiple queries.

    Args:
        search_queries: List of search queries to execute
        max_results: Maximum number of results per query
        topic: Topic filter for search results
        include_raw_content: Whether to include raw webpage content
        config: Runtime configuration for API key

    Returns:
        List of search result dictionaries
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
    """Execute multiple Tavily search queries asynchronously.

    Args:
        search_queries: List of search query strings to execute
        max_results: Maximum number of results per query
        topic: Topic category for filtering results
        include_raw_content: Whether to include full webpage content
        config: Runtime configuration for API key access

    Returns:
        List of search result dictionaries from Tavily API
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
    """Deduplicate search results by URL to avoid processing duplicate content.

    Args:
        search_results: List of search result dictionaries

    Returns:
        Dictionary mapping URLs to unique results
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
    """Process search results by summarizing content where available.

    Args:
        unique_results: Dictionary of unique search results
        summarization_model: Optional model for content summarization
        max_content_length: Maximum content length before truncation

    Returns:
        Dictionary of processed results with summaries
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
    """Format search results into a well-structured string output.

    Args:
        summarized_results: Dictionary of processed search results

    Returns:
        Formatted string of search results with clear source separation
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
    """Summarize webpage content using AI model.

    Args:
        model: The chat model configured for summarization
        webpage_content: Raw webpage content to be summarized
        timeout: Timeout in seconds for summarization

    Returns:
        Formatted summary with key excerpts, or original content if failed
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
    """Summarize webpage content using AI model asynchronously.

    Args:
        model: The chat model configured for summarization
        webpage_content: Raw webpage content to be summarized
        timeout: Timeout in seconds for the summarization task

    Returns:
        Formatted summary with key excerpts, or original content if failed
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
    """Fetch results from Tavily search API with content summarization.

    Args:
        query: A single search query to execute
        max_results: Maximum number of results to return
        topic: Topic to filter results by ('general', 'news', 'finance')

    Returns:
        Formatted string of search results with summaries
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
    """Refine draft report by synthesizing research findings.

    Args:
        research_brief: User's research request
        findings: Collected research findings for the user request
        draft_report: Draft report based on the findings and user request

    Returns:
        Refined draft report
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
    """Determine if an exception indicates a token/context limit was exceeded.

    Args:
        exception: The exception to analyze
        model_name: Optional model name to optimize provider detection

    Returns:
        True if the exception indicates a token limit was exceeded, False otherwise
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

    # Google/Gemini Models (Only 2.5 series accessible via API as of Dec 2024)
    # Deprecated: 1.5 and 2.0 series models
    "google:gemini-2.5-pro": 2097152,
    "google:gemini-2.5-flash": 1048576,
    "google:gemini-2.5-flash-lite": 1048576,
    "gemini-2.5-pro": 2097152,
    "gemini-2.5-flash": 1048576,
    "gemini-2.5-flash-lite": 1048576,
    # Legacy models (deprecated, kept for reference)
    "google:gemini-1.5-pro": 2097152,
    "google:gemini-1.5-flash": 1048576,
    "google:gemini-2.0-flash": 1048576,
    "gemini-1.5-pro": 2097152,
    "gemini-1.5-flash": 1048576,
    "gemini-2.0-flash-exp": 1048576,
}


def get_model_token_limit(model_name: str) -> int:
    """Get the token limit for a given model.

    Args:
        model_name: Name of the model

    Returns:
        Token limit, or default of 128000 if unknown
    """
    return MODEL_TOKEN_LIMITS.get(model_name, 128000)
