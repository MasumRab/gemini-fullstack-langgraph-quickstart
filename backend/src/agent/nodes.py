# TODO: See docs/tasks/upstream_compatibility.md for future splitting of this file into _nodes.py (upstream) and nodes.py (evolved).
import os
import re
import difflib
from typing import List, Dict, Any, Optional
import logging

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.types import Send
from google.genai import Client

from agent.state import (
    OverallState,
    QueryGenerationState,
    ReflectionState,
    WebSearchState,
)
from agent.configuration import Configuration
from agent.prompts import (
    get_current_date,
    query_writer_instructions,
    web_searcher_instructions,
    reflection_instructions,
    answer_instructions,
)
from agent.tools_and_schemas import SearchQueryList, Reflection
from agent.utils import (
    get_citations,
    get_research_topic,
    insert_citation_markers,
    resolve_urls,
)
from agent.registry import graph_registry
from agent.persistence import load_plan, save_plan
from agent.research_tools import TAVILY_AVAILABLE, tavily_search_multiple

# Optional observability import
try:
    from observability.langfuse import observe_span
except ImportError:
    from contextlib import contextmanager

    @contextmanager
    def observe_span(name: str, config: Any = None):
        """No-op observability span when langfuse is not available."""
        yield

# Optional config import with sensible defaults for standalone usage
try:
    from config.app_config import config as app_config
except ImportError:
    from dataclasses import dataclass

    @dataclass
    class _DefaultAppConfig:
        """Default configuration for standalone agent usage."""
        validation_mode: str = "heuristic"
        require_citations: bool = False
        compression_enabled: bool = False
        compression_mode: str = "extractive"
        model_validation: str = "gemini-2.5-flash-preview-05-20"
        model_compression: str = "gemini-2.5-flash-preview-05-20"
        search_provider: str = "google"
        search_fallback: str = "duckduckgo"

    app_config = _DefaultAppConfig()

# Optional search router import with fallback implementation
try:
    from search.router import search_router
except ImportError:
    class _FallbackSearchResult:
        """Simple search result for fallback router."""
        def __init__(self, title: str, url: str, content: str):
            self.title = title
            self.url = url
            self.content = content
            self.raw_content = content

    class _FallbackSearchRouter:
        """Fallback search router using Google GenAI client directly."""

        def search(self, query: str, max_results: int = 3) -> List[Any]:
            """Execute search using Google's grounding API."""
            from google.genai import Client
            client = Client(api_key=os.getenv("GEMINI_API_KEY"))
            response = client.models.generate_content(
                model="gemini-2.5-flash-preview-05-20",
                contents=query,
                config={
                    "tools": [{"google_search": {}}],
                    "temperature": 0,
                },
            )
            results = []
            # Extract grounding metadata if available
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "grounding_metadata"):
                    grounding = candidate.grounding_metadata
                    if hasattr(grounding, "grounding_chunks"):
                        for chunk in grounding.grounding_chunks[:max_results]:
                            web = getattr(chunk, "web", None)
                            if web:
                                results.append(_FallbackSearchResult(
                                    title=getattr(web, "title", ""),
                                    url=getattr(web, "uri", ""),
                                    content=getattr(chunk, "text", ""),
                                ))
            # Fallback: use text response if no grounding data
            if not results and hasattr(response, "text"):
                results.append(_FallbackSearchResult(
                    title="Search Results",
                    url="",
                    content=response.text,
                ))
            return results

    search_router = _FallbackSearchRouter()

logger = logging.getLogger(__name__)

# Initialize Google Search Client
genai_client = Client(api_key=os.getenv("GEMINI_API_KEY"))


@graph_registry.describe(
    "load_context",
    summary="Loads existing plan and artifacts from persistence layer.",
    tags=["persistence"],
    outputs=["todo_list", "artifacts"],
)
def load_context(state: OverallState, config: RunnableConfig) -> OverallState:
    """Load context from persistence layer if thread_id is available."""
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return {}

    data = load_plan(thread_id)
    if data:
        return {
            "todo_list": data.get("todo_list", []),
            "artifacts": data.get("artifacts", {}),
            "planning_steps": data.get("todo_list", [])
        }
    return {}


@graph_registry.describe(
    "generate_query",
    summary="LLM generates structured search queries from the conversation context.",
    tags=["llm", "search"],
    outputs=["search_query"],
)
def generate_query(state: OverallState, config: RunnableConfig) -> QueryGenerationState:
    """LangGraph node that generates search queries based on the User's question.

    Uses Gemini 2.0 Flash to create an optimized search queries for web research based on
    the User's question.
    """
    with observe_span("generate_query", config):
        configurable = Configuration.from_runnable_config(config)

        # check for custom initial search query count
        if state.get("initial_search_query_count") is None:
            state["initial_search_query_count"] = configurable.number_of_initial_queries

        # init Gemini 2.0 Flash
        llm = ChatGoogleGenerativeAI(
            model=configurable.query_generator_model,
            temperature=1.0,
            max_retries=2,
            api_key=os.getenv("GEMINI_API_KEY"),
        )
        structured_llm = llm.with_structured_output(SearchQueryList)

        # Format the prompt
        current_date = get_current_date()
        formatted_prompt = query_writer_instructions.format(
            current_date=current_date,
            research_topic=get_research_topic(state["messages"]),
            number_queries=state["initial_search_query_count"],
        )

        # Generate the search queries
        result = structured_llm.invoke(formatted_prompt, config=config)
        return {"search_query": result.query}


@graph_registry.describe(
    "continue_to_web_research",
    summary="Fan-out helper that routes each generated query to a web research task.",
    tags=["routing", "parallel"],
)
def continue_to_web_research(state: QueryGenerationState):
    """LangGraph node that sends the search queries to the web research node."""
    queries = state.get("search_query", [])
    if not queries:
        return []
    return [
        Send("web_research", {"search_query": search_query, "id": int(idx)})
        for idx, search_query in enumerate(queries)
    ]


@graph_registry.describe(
    "web_research",
    summary="Executes web search using configured providers via SearchRouter.",
    tags=["search", "tool"],
    outputs=["web_research_result", "sources_gathered"],
)
def web_research(state: WebSearchState, config: RunnableConfig) -> OverallState:
    """
    LangGraph node that performs web research.
    Updated to use the unified SearchRouter and AppConfig.
    """
    with observe_span("web_research", config):
        query = state["search_query"]

        # Use the SearchRouter for standardized search with fallback
        try:
            results = search_router.search(query, max_results=3)
        except Exception as e:
            logger.error(f"Web research failed: {e}")
            return {
                "sources_gathered": [],
                "search_query": [query],
                "web_research_result": [],
                "validation_notes": [f"Search failed for query '{query}': {e}"],
            }

        sources_gathered = []
        web_research_results = []

        for r in results:
            # Create source
            source = {
                "label": r.title,
                "short_url": r.url,
                "value": r.url
            }
            sources_gathered.append(source)

            # Append to result text with citation
            snippet = r.content or r.raw_content or ""
            web_research_results.append(f"{snippet} [{r.title}]({r.url})")

        combined_result = "\n\n".join(web_research_results)

        return {
            "sources_gathered": sources_gathered,
            "search_query": [query],
            "web_research_result": [combined_result],
        }


@graph_registry.describe(
    "planning_mode",
    summary="Creates structured plan steps from generated queries for user review.",
    tags=["planning", "ui"],
    outputs=["planning_steps", "planning_status", "planning_feedback"],
)
def planning_mode(state: OverallState, config: RunnableConfig) -> OverallState:
    """Create structured plan steps from generated queries for user review."""
    with observe_span("planning_mode", config):
        configurable = Configuration.from_runnable_config(config)
        queries = state.get("search_query", []) or []
        planning_status = state.get("planning_status")

        last_message = state["messages"][-1] if state.get("messages") else None
        if isinstance(last_message, dict):
            last_content = last_message.get("content", "")
        else:
            last_content = getattr(last_message, "content", "")
        last_content = last_content.strip().lower() if isinstance(last_content, str) else ""

        if last_content.startswith("/end_plan"):
            return {
                "planning_steps": [],
                "planning_status": "auto_approved",
                "planning_feedback": ["Planning skipped via /end_plan."]
            }

        if planning_status == "auto_approved" and not state.get("planning_steps"):
            return {"planning_steps": [], "planning_feedback": ["Planning skipped."]}

        if last_content.startswith("/plan"):
            state["planning_status"] = "awaiting_confirmation"

        plan_steps = []
        for idx, query in enumerate(queries):
            label = query if isinstance(query, str) else str(query)
            plan_steps.append(
                {
                    "id": f"plan-{idx}",
                    "title": f"Investigate: {label}",
                    "query": label,
                    "suggested_tool": "web_research",
                    "status": "pending",
                }
            )

        if not planning_status:
            status = (
                "awaiting_confirmation"
                if getattr(configurable, "require_planning_confirmation", False)
                else "auto_approved"
            )
        else:
            status = planning_status

        feedback = [f"Generated {len(plan_steps)} plan steps from initial queries."]
        if not plan_steps:
            feedback.append("No queries available; planning mode produced an empty plan.")

        thread_id = config.get("configurable", {}).get("thread_id")
        if thread_id:
            save_plan(thread_id, plan_steps, state.get("artifacts", {}) or {})

        return {
            "planning_steps": plan_steps,
            "todo_list": plan_steps,
            "planning_status": state.get("planning_status") or status,
            "planning_feedback": feedback,
        }


@graph_registry.describe(
    "planning_wait",
    summary="Pauses execution until the frontend confirms the plan.",
    tags=["planning", "ui"],
    outputs=["planning_feedback"],
)
def planning_wait(state: OverallState) -> OverallState:
    """Pause execution until user confirms the plan."""
    return {
        "planning_feedback": [
            "Awaiting user confirmation. Update planning_status to 'confirmed' to continue."
        ]
    }


def planning_router(state: OverallState, config: RunnableConfig):
    """Route based on planning status and user commands."""
    configurable = Configuration.from_runnable_config(config)
    planning_status = state.get("planning_status")
    last_message = state["messages"][-1] if state.get("messages") else None
    if isinstance(last_message, dict):
        last_content = last_message.get("content", "")
    else:
        last_content = getattr(last_message, "content", "")
    last_content = last_content.strip().lower() if isinstance(last_content, str) else ""

    if last_content.startswith("/plan"):
        state["planning_status"] = "awaiting_confirmation"
        return "planning_wait"

    if last_content.startswith("/end_plan"):
        state["planning_status"] = "auto_approved"
        return continue_to_web_research(state)

    if last_content.startswith("/confirm_plan"):
        state["planning_status"] = "confirmed"
        return continue_to_web_research(state)

    if getattr(configurable, "require_planning_confirmation", False) and planning_status != "confirmed":
        return "planning_wait"

    return continue_to_web_research(state)


def _flatten_queries(queries: List) -> List[str]:
    """Flatten nested query lists."""
    flattened: List[str] = []
    for item in queries:
        if isinstance(item, list):
            flattened.extend(_flatten_queries(item))
        elif isinstance(item, str):
            flattened.append(item)
    return flattened


def _keywords_from_queries(queries: List[str]) -> List[str]:
    """Extract keywords from queries (tokens >= 4 chars)."""
    keywords: List[str] = []
    for query in queries:
        for token in re.split(r"[^\w]+", query.lower()):
            if len(token) >= 4:
                keywords.append(token)
    return keywords


@graph_registry.describe(
    "validate_web_results",
    summary="Hybrid validation (Heuristics + LLM) with citation hard-fail.",
    tags=["validation", "quality"],
    outputs=["validated_web_research_result", "validation_notes"],
)
def validate_web_results(state: OverallState, config: RunnableConfig) -> OverallState:
    """
    Hybrid validation logic:
    1. Heuristic filtering (fuzzy match against query intent).
    2. LLM Claim-Check (if Validation Mode is hybrid).
    3. Citation Hard-Fail (if REQUIRE_CITATIONS is true).
    """
    with observe_span("validate_web_results", config):
        summaries = state.get("web_research_result", [])
        if not summaries:
            return {
                "validated_web_research_result": [],
                "validation_notes": ["No web research summaries available for validation."],
            }

        raw_queries = state.get("search_query", [])
        flattened_queries = _flatten_queries(raw_queries) if isinstance(raw_queries, list) else [str(raw_queries)]
        keywords = _keywords_from_queries(flattened_queries)

        validated: List[str] = []
        notes: List[str] = []

        # 1. Heuristics (Pre-filter)
        heuristic_passed = []

        # Check for markdown-style citations [Title](url)
        citation_pattern = r'\[[^\]]+\]\(https?://[^\)]+\)'

        for idx, summary in enumerate(summaries):
            normalized_summary = summary.lower()
            match_found = False

            has_citation = bool(re.search(citation_pattern, summary))

            if app_config.require_citations and not has_citation:
                notes.append(f"Result {idx+1} rejected: Missing citations (Hard Fail).")
                continue

            if keywords:
                if any(keyword in normalized_summary for keyword in keywords):
                    match_found = True
                else:
                    for keyword in keywords:
                        summary_words = normalized_summary.split()
                        matches = difflib.get_close_matches(keyword, summary_words, n=1, cutoff=0.8)
                        if matches:
                            match_found = True
                            break

            if match_found or not keywords:
                heuristic_passed.append(summary)
            else:
                notes.append(f"Result {idx + 1} filtered (Heuristics): Low overlap with query intent.")

        # 2. LLM Validation (Hybrid Mode)
        if app_config.validation_mode == "hybrid" and heuristic_passed:
            validated_by_llm = []

            llm = ChatGoogleGenerativeAI(
                model=app_config.model_validation,
                temperature=0,
                api_key=os.getenv("GEMINI_API_KEY"),
            )

            for candidate in heuristic_passed:
                # Lightweight claim check
                prompt = f"""
                Verify if the following snippet actually contains relevant information for the query: "{flattened_queries[0] if flattened_queries else 'research topic'}"
                Snippet: "{candidate[:500]}..."
                Reply with "YES" or "NO" only.
                """
                try:
                    # Assuming invoke returns AIMessage or similar
                    response = llm.invoke(prompt)
                    content = response.content if hasattr(response, "content") else str(response)

                    if "YES" in content.upper():
                        validated_by_llm.append(candidate)
                    else:
                        notes.append("Result rejected by LLM Validator: Content mismatch.")
                except Exception as e:
                    logger.warning(f"LLM validation failed: {e}. Accepting candidate.")
                    validated_by_llm.append(candidate)

            validated = validated_by_llm
        else:
            validated = heuristic_passed

        if not validated:
            notes.append("All summaries failed validation.")

        return {
            "validated_web_research_result": validated,
            "validation_notes": notes,
        }

@graph_registry.describe(
    "compression_node",
    summary="Tiered compression of research results.",
    tags=["compression", "optimization"],
    outputs=["web_research_result"],
)
def compression_node(state: OverallState, config: RunnableConfig) -> OverallState:
    """
    Tiered Compression:
    1. Extractive: Deduplicate and remove redundant phrases.
    2. Abstractive: Summarize while keeping citations (if enabled).
    """
    if not app_config.compression_enabled:
        return {} # No change

    # Fallback to web_research_result if validation was skipped or returned empty (backward compat)
    results = state.get("validated_web_research_result", []) or state.get("web_research_result", [])
    if not results:
        return {}

    # Tier 1: Extractive (Deduplicate while preserving order)
    seen = set()
    unique_results = []
    for r in results:
        if r not in seen:
            seen.add(r)
            unique_results.append(r)

    # Tier 2: Abstractive (LLM Summarization)
    if app_config.compression_mode == "tiered":
        # Simple prompt construction
        combined_text = "\n\n".join(unique_results)

        # Truncate if too long to avoid context overflow
        max_chars = 30000  # Reasonable limit for most models
        if len(combined_text) > max_chars:
            combined_text = combined_text[:max_chars] + "\n[... truncated]"

        prompt = f"""
        Compress the following research notes into a concise summary.
        CRITICAL: You MUST preserve all source citations in [Title](url) format.
        Do not lose any factual claims.

        Notes:
        {combined_text}
        """

        try:
            llm = ChatGoogleGenerativeAI(
                model=app_config.model_compression, # e.g. "gemini-2.0-flash-lite" or similar
                temperature=0,
                api_key=os.getenv("GEMINI_API_KEY"),
            )
            compressed = llm.invoke(prompt).content
            return {"validated_web_research_result": [compressed]}
        except Exception as e:
            logger.warning(f"Compression failed: {e}. Returning originals.")
            return {"validated_web_research_result": unique_results}

    return {"validated_web_research_result": unique_results}


@graph_registry.describe(
    "reflection",
    summary="Reasoning step that evaluates coverage and proposes follow-up queries.",
    tags=["llm", "reasoning"],
    outputs=["is_sufficient", "follow_up_queries"],
)
def reflection(state: OverallState, config: RunnableConfig) -> ReflectionState:
    """LangGraph node that identifies knowledge gaps and generates potential follow-up queries.

    Analyzes the current summary to identify areas for further research and generates
    potential follow-up queries. Uses structured output to extract
    the follow-up query in JSON format.
    """
    with observe_span("reflection", config):
        configurable = Configuration.from_runnable_config(config)
        state["research_loop_count"] = state.get("research_loop_count", 0) + 1
        reasoning_model = state.get("reasoning_model", configurable.reflection_model)

        current_date = get_current_date()
        # Use validated results for reflection
        summaries_source = state.get("validated_web_research_result") or state.get("web_research_result", [])

        formatted_prompt = reflection_instructions.format(
            current_date=current_date,
            research_topic=get_research_topic(state["messages"]),
            summaries="\n\n---\n\n".join(summaries_source),
        )

        llm = ChatGoogleGenerativeAI(
            model=reasoning_model,
            temperature=1.0,
            max_retries=2,
            api_key=os.getenv("GEMINI_API_KEY"),
        )
        result = llm.with_structured_output(Reflection).invoke(formatted_prompt, config=config)

        return {
            "is_sufficient": result.is_sufficient,
            "knowledge_gap": result.knowledge_gap,
            "follow_up_queries": result.follow_up_queries,
            "research_loop_count": state["research_loop_count"],
            "number_of_ran_queries": len(state["search_query"]),
        }


@graph_registry.describe(
    "evaluate_research",
    summary="Routing policy deciding between additional web searches or final answer.",
    tags=["routing", "policy"],
)
def evaluate_research(
    state: ReflectionState,
    config: RunnableConfig,
) -> OverallState:
    """LangGraph routing function that determines the next step in the research flow."""
    configurable = Configuration.from_runnable_config(config)
    max_research_loops = (
        state.get("max_research_loops")
        if state.get("max_research_loops") is not None
        else configurable.max_research_loops
    )
    if state["is_sufficient"] or state["research_loop_count"] >= max_research_loops:
        return "finalize_answer"
    else:
        return [
            Send(
                "web_research",
                {
                    "search_query": follow_up_query,
                    "id": state["number_of_ran_queries"] + int(idx),
                },
            )
            for idx, follow_up_query in enumerate(state["follow_up_queries"])
        ]


@graph_registry.describe(
    "finalize_answer",
    summary="Synthesizes final response with deduplicated sources and citations.",
    tags=["llm", "synthesis"],
    outputs=["messages", "sources_gathered"],
)
def finalize_answer(state: OverallState, config: RunnableConfig):
    """LangGraph node that finalizes the research summary."""
    with observe_span("finalize_answer", config):
        configurable = Configuration.from_runnable_config(config)
        reasoning_model = state.get("reasoning_model") or configurable.answer_model

        current_date = get_current_date()

        # Use validated (and optionally compressed) results
        summaries = state.get("validated_web_research_result") or state.get("web_research_result", [])

        formatted_prompt = answer_instructions.format(
            current_date=current_date,
            research_topic=get_research_topic(state["messages"]),
            summaries="\n---\n\n".join(summaries),
        )

        llm = ChatGoogleGenerativeAI(
            model=reasoning_model,
            temperature=0,
            max_retries=2,
            api_key=os.getenv("GEMINI_API_KEY"),
        )
        result = llm.invoke(formatted_prompt)

        # Replace the short urls with the original urls and add all used urls to the sources_gathered
        unique_sources = []
        if "sources_gathered" in state:
            for source in state["sources_gathered"]:
                # Robust regex pattern to match the short URL
                pattern = re.escape(source["short_url"])
                if re.search(pattern, result.content):
                    # Replace all occurrences using regex
                    result.content = re.sub(pattern, source["value"], result.content)
                    unique_sources.append(source)

        return {
            "messages": [AIMessage(content=result.content)],
            "sources_gathered": unique_sources,
        }
