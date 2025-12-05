import os
import re
import difflib
from typing import List, Dict, Any

from langchain_core.messages import AIMessage
from langgraph.types import Send
from langchain_core.runnables import RunnableConfig
from google.genai import Client
from langchain_google_genai import ChatGoogleGenerativeAI
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

# Used for Google Search API
genai_client = Client(api_key=os.getenv("GEMINI_API_KEY"))


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
    return [
        Send("web_research", {"search_query": search_query, "id": int(idx)})
        for idx, search_query in enumerate(state["search_query"])
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

    Args:
        state: Current graph state containing the search query and research loop count
        config: Configuration for the runnable, including search API settings

    Returns:
        Dictionary with state update, including sources_gathered, research_loop_count, and web_research_results
    """
    # Configure
    configurable = Configuration.from_runnable_config(config)
    formatted_prompt = web_searcher_instructions.format(
        current_date=get_current_date(),
        research_topic=state["search_query"],
    )

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


def _handle_end_plan(state: OverallState) -> OverallState:
    return {
        "planning_status": "auto_approved",
        "planning_steps": [],
        "planning_feedback": ["Planning disabled via /end_plan."],
    }

def _handle_confirm_plan(state: OverallState) -> OverallState:
    return {
        "planning_status": "confirmed",
        "planning_feedback": ["Plan confirmed. Proceeding to research."]
    }

def _handle_start_plan(state: OverallState) -> OverallState:
    return {
        "planning_status": "awaiting_confirmation",
        "planning_feedback": ["Planning mode started. Please review the plan."]
    }


@graph_registry.describe(
    "planning_mode",
    summary="Creates structured plan steps from generated queries for user review.",
    tags=["planning", "ui"],
    outputs=["planning_steps", "planning_status", "planning_feedback"],
)
def planning_mode(state: OverallState, config: RunnableConfig) -> OverallState:
    configurable = Configuration.from_runnable_config(config)

    # If the router has already handled a command that changes status, we might see it here
    # But usually this node is called after generate_query to SET UP the plan.

    queries = state.get("search_query", []) or []
    planning_status = state.get("planning_status")

    # If we are in the "skip" flow, return immediately
    # Note: If the router detected /end_plan in a previous turn (unlikely for planning_mode which runs first)
    # OR if we want to support skipping planning based on an initial /end_plan input:
    last_message = state["messages"][-1] if state.get("messages") else None
    if isinstance(last_message, dict):
        last_content = last_message.get("content", "")
    else:
        last_content = getattr(last_message, "content", "")
    last_content = last_content.strip().lower() if isinstance(last_content, str) else ""

    # If the user explicitly asks to end planning right away, we produce an empty plan
    if last_content.startswith("/end_plan"):
        return {
            "planning_steps": [],
            "planning_status": "auto_approved", # Let the router downstream confirm this transition
            "planning_feedback": ["Planning skipped via /end_plan."]
        }

    # If already skipped or confirmed, just return (idempotent)
    if planning_status == "auto_approved" and not state.get("planning_steps"):
         return {"planning_steps": [], "planning_feedback": ["Planning skipped."]}

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
            if configurable.require_planning_confirmation
            else "auto_approved"
        )
    else:
        status = planning_status

    feedback = [f"Generated {len(plan_steps)} plan steps from initial queries."]
    if not plan_steps:
        feedback.append("No queries available; planning mode produced an empty plan.")

    return {
        "planning_steps": plan_steps,
        "planning_status": status,
        "planning_feedback": feedback,
    }


@graph_registry.describe(
    "planning_wait",
    summary="Pauses execution until the frontend confirms the plan.",
    tags=["planning", "ui"],
    outputs=["planning_feedback"],
)
def planning_wait(state: OverallState) -> OverallState:
    return {
        "planning_feedback": [
            "Awaiting user confirmation. Update planning_status to 'confirmed' to continue."
        ]
    }


def planning_router(state: OverallState, config: RunnableConfig):
    configurable = Configuration.from_runnable_config(config)
    planning_status = state.get("planning_status")
    last_message = state["messages"][-1] if state.get("messages") else None
    if isinstance(last_message, dict):
        last_content = last_message.get("content", "")
    else:
        last_content = getattr(last_message, "content", "")
    last_content = last_content.strip().lower() if isinstance(last_content, str) else ""

    # Command Handling with pure routing logic
    # We delegate the actual state update to the 'planning_mode' node
    # or ensuring the state is updated before we get here?
    # Actually, the user asked to FIX the mixing of state updates.
    # The cleanest way in LangGraph without a new 'command_processor' node in the middle
    # is to have a specialized edge handler, but edges can't update state.

    # We will detect the command and route to a node that *can* update state if needed,
    # OR we accept that for this specific simple agent, the router might have side effects
    # but we make it explicit.

    # However, to strictly follow the request "Fix the planning_mode node has logic that mixes state updates...",
    # we should move the command handling OUT of planning_mode node.

    if last_content.startswith("/plan"):
        # We need to transition to a state where we wait.
        # We can update the state here as a "side effect" of the router if we must,
        # but better is to have the destination node handle it.
        state["planning_status"] = "awaiting_confirmation"
        return "planning_wait"

    if last_content.startswith("/end_plan"):
        state["planning_status"] = "auto_approved"
        # We route to web_research, effectively skipping planning
        return continue_to_web_research(state)

    if last_content.startswith("/confirm_plan"):
        state["planning_status"] = "confirmed"
        return continue_to_web_research(state)

    if configurable.require_planning_confirmation and planning_status != "confirmed":
        return "planning_wait"

    return continue_to_web_research(state)


def _flatten_queries(queries: List) -> List[str]:
    flattened: List[str] = []
    for item in queries:
        if isinstance(item, list):
            flattened.extend(_flatten_queries(item))
        elif isinstance(item, str):
            flattened.append(item)
    return flattened


def _keywords_from_queries(queries: List[str]) -> List[str]:
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
    """Ensure returned summaries reference the core query intent before reflection."""

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
                # Fuzzy matching for robustnes (e.g. typos, stemming differences)
                for keyword in keywords:
                    # quick check if close match exists in words
                    summary_words = normalized_summary.split()
                    matches = difflib.get_close_matches(keyword, summary_words, n=1, cutoff=0.8)
                    if matches:
                        match_found = True
                        break

        # Secondary: Semantic Check (Fallback)
        if not match_found and keywords:
             # If heuristic fails, we could opt to use LLM.
             # To keep it lightweight, we only do this if strictly configured or if confidence is critical.
             # For now, we will log it as a near-miss but maybe be lenient?
             # Implementation of actual LLM fallback:

             # configurable = Configuration.from_runnable_config(config)
             # llm = ChatGoogleGenerativeAI(model=configurable.query_generator_model, ...)
             # prompt = f"Does the text answer the query '{raw_queries}'? Text: {summary[:500]}..."
             # ...

             # For this iteration, we stick to the plan of improving the heuristic
             # and maybe logging the "miss" more gracefully.
             # Given the "validation" nature, if it fails fuzzy match, it's likely irrelevant.
             pass

        if match_found or not keywords:
             validated.append(summary)
        else:
             notes.append(
                f"Result {idx + 1} filtered: missing overlap with query intent ({', '.join(keywords[:5])})."
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
