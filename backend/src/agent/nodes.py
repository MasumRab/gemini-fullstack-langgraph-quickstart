import os
import re
import difflib
from typing import List, Dict, Any, Optional

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

    Args:
        state: Current graph state containing the User's question
        config: Configuration for the runnable, including LLM provider settings

    Returns:
        Dictionary with state update, including search_query key containing the generated queries
    """
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
    result = structured_llm.invoke(formatted_prompt)
    return {"search_query": result.query}


@graph_registry.describe(
    "continue_to_web_research",
    summary="Fan-out helper that routes each generated query to a web research task.",
    tags=["routing", "parallel"],
)
def continue_to_web_research(state: QueryGenerationState):
    """LangGraph node that sends the search queries to the web research node.

    This is used to spawn n number of web research nodes, one for each search query.
    """
    queries = state.get("search_query", [])
    if not queries:
        return []
    return [
        Send("web_research", {"search_query": search_query, "id": int(idx)})
        for idx, search_query in enumerate(queries)
    ]


@graph_registry.describe(
    "web_research",
    summary="Calls Google Search tool, resolves citations, and returns annotated snippets.",
    tags=["search", "tool"],
    outputs=["web_research_result", "sources_gathered"],
)
def web_research(state: WebSearchState, config: RunnableConfig) -> OverallState:
    """LangGraph node that performs web research using the native Google Search API tool.

    Executes a web search using the native Google Search API tool in combination with Gemini 2.0 Flash.
    Also supports Tavily as an alternative search provider if configured.

    Args:
        state: Current graph state containing the search query and research loop count
        config: Configuration for the runnable, including search API settings

    Returns:
        Dictionary with state update, including sources_gathered, research_loop_count, and web_research_results
    """
    configurable = Configuration.from_runnable_config(config)
    formatted_prompt = web_searcher_instructions.format(
        current_date=get_current_date(),
        research_topic=state["search_query"],
    )

    # Check for Tavily API Key - use Tavily if available
    tavily_key = os.getenv("TAVILY_API_KEY")
    if TAVILY_AVAILABLE and tavily_key:
        search_results = tavily_search_multiple(
            [state["search_query"]],
            max_results=3,
            include_raw_content=False,
        )
        
        sources_gathered = []
        web_research_results = []
        
        for response in search_results:
            for result in response.get("results", []):
                title = result.get("title", "Untitled")
                url = result.get("url", "")
                content = result.get("content", "")
                
                # Create source
                source = {
                    "label": title,
                    "short_url": url,
                    "value": url
                }
                sources_gathered.append(source)
                
                # Append to result text with citation
                web_research_results.append(f"{content} [{title}]({url})")
        
        return {
            "sources_gathered": sources_gathered,
            "search_query": [state["search_query"]],
            "web_research_result": ["\n\n".join(web_research_results)],
        }

    # Uses the google genai client as the langchain client doesn't return grounding metadata
    # The 'tools' config is compatible with both Gemini 1.5 and 2.x models
    response = genai_client.models.generate_content(
        model=configurable.query_generator_model,
        contents=formatted_prompt,
        config={
            "tools": [{"google_search": {}}],
            "temperature": 0,
        },
    )

    # Check if grounding metadata is available
    if not response.candidates or not response.candidates[0].grounding_metadata:
        # Fallback if no grounding metadata (though unlikely with google_search tool)
        return {
            "sources_gathered": [],
            "search_query": [state["search_query"]],
            "web_research_result": [response.text],
        }

    # resolve the urls to short urls for saving tokens and time
    resolved_urls = resolve_urls(
        response.candidates[0].grounding_metadata.grounding_chunks, state["id"]
    )

    # Gets the citations and adds them to the generated text
    citations = get_citations(response, resolved_urls)
    modified_text = insert_citation_markers(response.text, citations)
    sources_gathered = [item for citation in citations for item in citation["segments"]]

    return {
        "sources_gathered": sources_gathered,
        "search_query": [state["search_query"]],
        "web_research_result": [modified_text],
    }


@graph_registry.describe(
    "planning_mode",
    summary="Creates structured plan steps from generated queries for user review.",
    tags=["planning", "ui"],
    outputs=["planning_steps", "planning_status", "planning_feedback"],
)
def planning_mode(state: OverallState, config: RunnableConfig) -> OverallState:
    """Create structured plan steps from generated queries for user review."""
    configurable = Configuration.from_runnable_config(config)
    queries = state.get("search_query", []) or []
    planning_status = state.get("planning_status")

    # Check last message for commands
    last_message = state["messages"][-1] if state.get("messages") else None
    if isinstance(last_message, dict):
        last_content = last_message.get("content", "")
    else:
        last_content = getattr(last_message, "content", "")
    last_content = last_content.strip().lower() if isinstance(last_content, str) else ""

    # If the user explicitly asks to end planning right away
    if last_content.startswith("/end_plan"):
        return {
            "planning_steps": [],
            "planning_status": "auto_approved",
            "planning_feedback": ["Planning skipped via /end_plan."]
        }

    # If already skipped or confirmed, just return (idempotent)
    if planning_status == "auto_approved" and not state.get("planning_steps"):
        return {"planning_steps": [], "planning_feedback": ["Planning skipped."]}

    # Handle /plan command
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

    # Determine initial status based on config, unless already set by a command
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

    # Persist the plan
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

    # Command Handling
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
        for token in re.split(r"[^a-zA-Z0-9]+", query.lower()):
            if len(token) >= 4:
                keywords.append(token)
    return keywords


@graph_registry.describe(
    "validate_web_results",
    summary="Lightweight heuristic gate that filters summaries misaligned with the query intent.",
    tags=["validation", "quality"],
    outputs=["validated_web_research_result", "validation_notes"],
)
def validate_web_results(state: OverallState, config: RunnableConfig) -> OverallState:
    """Ensure returned summaries reference the core query intent before reflection.
    
    Uses fuzzy matching for robustness against typos and stemming differences.
    """
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

    for idx, summary in enumerate(summaries):
        normalized_summary = summary.lower()

        # Primary: Fuzzy Keyword Matching
        match_found = False
        if keywords:
            # Check for direct inclusion first (fastest)
            if any(keyword in normalized_summary for keyword in keywords):
                match_found = True
            else:
                # Fuzzy matching for robustness (e.g. typos, stemming differences)
                for keyword in keywords:
                    summary_words = normalized_summary.split()
                    matches = difflib.get_close_matches(keyword, summary_words, n=1, cutoff=0.8)
                    if matches:
                        match_found = True
                        break

        if match_found or not keywords:
            validated.append(summary)
        else:
            snippet = (summary[:50] + "...") if len(summary) > 50 else summary
            notes.append(
                f"Result {idx + 1} filtered: '{snippet}' missing overlap with query intent ({', '.join(keywords[:5])})."
            )

    if not validated:
        notes.append("All summaries failed heuristics; retaining originals to avoid data loss.")
        validated = summaries

    return {
        "validated_web_research_result": validated,
        "validation_notes": notes,
    }


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

    Args:
        state: Current graph state containing the running summary and research topic
        config: Configuration for the runnable, including LLM provider settings

    Returns:
        Dictionary with state update, including search_query key containing the generated follow-up query
    """
    configurable = Configuration.from_runnable_config(config)
    # Increment the research loop count and get the reasoning model
    state["research_loop_count"] = state.get("research_loop_count", 0) + 1
    reasoning_model = state.get("reasoning_model", configurable.reflection_model)

    # Format the prompt
    current_date = get_current_date()
    summaries_source = state.get("validated_web_research_result") or state.get("web_research_result", [])
    formatted_prompt = reflection_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        summaries="\n\n---\n\n".join(summaries_source),
    )

    # init Reasoning Model
    llm = ChatGoogleGenerativeAI(
        model=reasoning_model,
        temperature=1.0,
        max_retries=2,
        api_key=os.getenv("GEMINI_API_KEY"),
    )
    result = llm.with_structured_output(Reflection).invoke(formatted_prompt)

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
    """LangGraph routing function that determines the next step in the research flow.

    Controls the research loop by deciding whether to continue gathering information
    or to finalize the summary based on the configured maximum number of research loops.

    Args:
        state: Current graph state containing the research loop count
        config: Configuration for the runnable, including max_research_loops setting

    Returns:
        String literal indicating the next node to visit ("web_research" or "finalize_summary")
    """
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
    """LangGraph node that finalizes the research summary.

    Prepares the final output by deduplicating and formatting sources, then
    combining them with the running summary to create a well-structured
    research report with proper citations.

    Args:
        state: Current graph state containing the running summary and sources gathered

    Returns:
        Dictionary with state update, including running_summary key containing the formatted final summary with sources
    """
    configurable = Configuration.from_runnable_config(config)
    reasoning_model = state.get("reasoning_model") or configurable.answer_model

    # Format the prompt
    current_date = get_current_date()
    formatted_prompt = answer_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        summaries="\n---\n\n".join(state["web_research_result"]),
    )

    # init Reasoning Model, default to Gemini 2.5 Flash
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
            if source["short_url"] in result.content:
                result.content = result.content.replace(
                    source["short_url"], source["value"]
                )
                unique_sources.append(source)

    return {
        "messages": [AIMessage(content=result.content)],
        "sources_gathered": unique_sources,
    }
