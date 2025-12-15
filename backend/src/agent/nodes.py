# TODO: See docs/tasks/upstream_compatibility.md for future splitting of this file into _nodes.py (upstream) and nodes.py (evolved).
import concurrent.futures
import difflib
import logging
import os
import re
from typing import List

from backend.src.config.app_config import config as app_config
from backend.src.search.router import search_router
from google.genai import Client
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.types import Send

from agent.configuration import Configuration
from agent.persistence import load_plan, save_plan
from agent.prompts import (
    answer_instructions,
    get_current_date,
    query_writer_instructions,
    reflection_instructions,
)
from agent.rate_limiter import get_context_manager, get_rate_limiter
from agent.registry import graph_registry
from agent.scoping_prompts import scoping_instructions
from agent.scoping_schema import ScopingAssessment
from agent.tools_and_schemas import SearchQueryList, Reflection, MCP_TOOLS
from agent.state import (
    OverallState,
    QueryGenerationState,
    ReflectionState,
    WebSearchState,
)
from agent.utils import (
    get_research_topic,
)
from observability.langfuse import observe_span

logger = logging.getLogger(__name__)

# Initialize Google Search Client
genai_client = Client(api_key=os.getenv("GEMINI_API_KEY"))


def _get_rate_limited_llm(model: str, temperature: float = 0, max_retries: int = 2, prompt: str = "") -> ChatGoogleGenerativeAI:
    """Get a rate-limited LLM instance with context management.
    
    Args:
        model: Model name to use
        temperature: Temperature setting
        max_retries: Maximum retry attempts
        prompt: Prompt text for token estimation
        
    Returns:
        Configured ChatGoogleGenerativeAI instance
    """
    # Get rate limiter and context manager
    rate_limiter = get_rate_limiter(model)
    context_mgr = get_context_manager(model)
    
    # Estimate tokens if prompt provided
    if prompt:
        estimated_tokens = context_mgr.estimate_tokens(prompt)
        
        # Wait if necessary
        wait_time = rate_limiter.wait_if_needed(estimated_tokens)
        if wait_time > 0:
            logger.info(f"Rate limited: waited {wait_time:.2f}s for {model}")
        
        # Log usage
        usage = rate_limiter.get_current_usage()
        logger.debug(f"Rate limit usage for {model}: RPM={usage['rpm']}/{usage['rpm_limit']}, TPM={usage['tpm']}/{usage['tpm_limit']}, RPD={usage['rpd']}/{usage['rpd_limit']}")
    
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        max_retries=max_retries,
        api_key=os.getenv("GEMINI_API_KEY"),
    )


@graph_registry.describe(
    "scoping_node",
    summary="Analyzes query for ambiguity and asks clarifying questions if needed.",
    tags=["planning", "scoping"],
    outputs=["scoping_status", "clarification_questions", "messages"],
)
def scoping_node(state: OverallState, config: RunnableConfig) -> OverallState:
    """Scoping Phase:
    Checks if the user's request is ambiguous.
    If yes -> Generates questions and sets status to 'active' (interrupt).
    If no -> Sets status to 'complete' (proceed).

    TODO: [SOTA Deep Research] Verify full alignment with Open Deep Research (Clarification Loop).
    See docs/tasks/04_SOTA_DEEP_RESEARCH_TASKS.md
    Subtask: Implement `scoping_node` logic: Analyze input query. If ambiguous, generate clarifying questions and interrupt graph.
    """
    with observe_span("scoping_node", config):
        # 1. Check if we are processing a clarification answer
        if state.get("scoping_status") == "active":
            # We just got an answer back from the user (in messages)
            # We assume the user's last message IS the answer.
            # We treat this as "complete" for this turn, but ideally we loop back.
            # For simplicity in V1: If we asked, and user answered, we assume it's clear enough to try planning.
            return {"scoping_status": "complete"}

        # 2. Analyze Initial Query
        messages = state["messages"]
        if not messages:
            return {"scoping_status": "complete"} # Should not happen

        # Format prompt first for token estimation
        prompt = scoping_instructions.format(
            current_date=get_current_date(),
            research_topic=get_research_topic(messages)
        )

        # Use rate-limited Gemini to assess ambiguity
        from agent.models import DEFAULT_SCOPING_MODEL
        
        llm = _get_rate_limited_llm(
            model=DEFAULT_SCOPING_MODEL,
            temperature=0,
            prompt=prompt
        )
        structured_llm = llm.with_structured_output(ScopingAssessment)

        try:
            assessment = structured_llm.invoke(prompt)
        except Exception as e:
            logger.error(f"Scoping LLM failed: {e}")
            return {"scoping_status": "complete"} # Fail open

        if assessment.is_ambiguous:
            # Create a message to ask the user
            questions_text = "\n".join([f"- {q}" for q in assessment.clarifying_questions])
            msg = f"To ensure I research this effectively, could you clarify:\n{questions_text}"

            return {
                "scoping_status": "active",
                "clarification_questions": assessment.clarifying_questions,
                "messages": [AIMessage(content=msg)]
            }

        return {"scoping_status": "complete"}


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

    Uses Gemini 2.5 Flash to create optimized search queries for web research based on
    the User's question. Includes rate limiting and context window management.

    TODO: [Open SWE] Rename to 'generate_plan' or create a new node.
    It should generate a structured 'Plan' (List[Todo]) instead of just queries.
    See docs/tasks/02_OPEN_SWE_TASKS.md
    Subtask: Update prompt `query_writer_instructions` to generate a `Plan` (List of Todos).
    Subtask: Update output parser.
    """
    with observe_span("generate_query", config):
        configurable = Configuration.from_runnable_config(config)

        # check for custom initial search query count
        if state.get("initial_search_query_count") is None:
            state["initial_search_query_count"] = configurable.number_of_initial_queries


        # Format the prompt
        current_date = get_current_date()
        formatted_prompt = query_writer_instructions.format(
            current_date=current_date,
            research_topic=get_research_topic(state["messages"]),
            number_queries=state["initial_search_query_count"],
        )

        # Truncate if needed
        context_mgr = get_context_manager(configurable.query_generator_model)
        formatted_prompt = context_mgr.truncate_to_fit(formatted_prompt)

        # Get rate-limited LLM
        llm = _get_rate_limited_llm(
            model=configurable.query_generator_model,
            temperature=1.0,
            max_retries=2,
            prompt=formatted_prompt
        )
        # Bind MCP tools if available
        if MCP_TOOLS:
             logger.info(f"Binding {len(MCP_TOOLS)} MCP tools to generate_query model.")
             llm = llm.bind_tools(MCP_TOOLS)

        structured_llm = llm.with_structured_output(SearchQueryList)

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
    """LangGraph node that performs web research.
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


def update_plan(state: OverallState, config: RunnableConfig) -> OverallState:
    """
    Refines the research plan based on new findings.

    TODO: [Open SWE] Implement 'update_plan' Node
    Logic: Read state.plan & state.web_research_result -> Prompt LLM -> Update Plan.
    See docs/tasks/02_OPEN_SWE_TASKS.md
    Subtask: Read `state.plan` and `state.web_research_result`.
    Subtask: Prompt LLM: "Given the result, update the plan (mark done, add new tasks)."
    Subtask: Parse output -> Update state.
    """
    raise NotImplementedError("update_plan not implemented")

def outline_gen(state: OverallState, config: RunnableConfig) -> OverallState:
    """
    Generates a hierarchical outline (Sections -> Subsections) for the research.

    TODO: [SOTA Deep Research] Implement 'outline_gen' Node (STORM)
    Logic: Generate hierarchical outline (Sections -> Subsections).
    See docs/tasks/04_SOTA_DEEP_RESEARCH_TASKS.md
    Subtask: Input: Refined user query + initial context.
    Subtask: Output: Populate `OverallState.outline`.
    """
    raise NotImplementedError("outline_gen not implemented")

def flow_update(state: OverallState, config: RunnableConfig) -> OverallState:
    """
    Dynamically expands the research DAG based on findings.

    TODO: [SOTA Deep Research] Implement 'flow_update' Node (FlowSearch)
    Logic: Dynamic DAG expansion based on findings.
    See docs/tasks/04_SOTA_DEEP_RESEARCH_TASKS.md
    Subtask: Analyze findings. Decide to (a) Mark task done, (b) Add new tasks (DAG expansion), (c) Refine existing tasks.
    Subtask: Output: Updated `todo_list` (DAG structure).
    """
    raise NotImplementedError("flow_update not implemented")

def content_reader(state: OverallState, config: RunnableConfig) -> OverallState:
    """
    Extracts structured evidence from raw web content.

    TODO: [SOTA Deep Research] Implement 'content_reader' Node (ManuSearch)
    Logic: Extract structured Evidence (Claim, Source, Context).
    See docs/tasks/04_SOTA_DEEP_RESEARCH_TASKS.md
    Subtask: Input: Raw HTML/Text from search.
    Subtask: Output: List of `Evidence` objects appended to `OverallState.evidence_bank`.
    """
    raise NotImplementedError("content_reader not implemented")

def research_subgraph(state: OverallState, config: RunnableConfig) -> OverallState:
    """
    Executes a recursive research subgraph for a specific sub-topic.

    TODO: [SOTA Deep Research] Implement 'research_subgraph' Node (GPT Researcher)
    Logic: Recursive research call for sub-topics.
    See docs/tasks/04_SOTA_DEEP_RESEARCH_TASKS.md
    Subtask: Input: A sub-topic query.
    Subtask: Logic: Compile and run a fresh instance of the `ResearchGraph`.
    """
    raise NotImplementedError("research_subgraph not implemented")

def checklist_verifier(state: OverallState, config: RunnableConfig) -> OverallState:
    """
    Audits gathered evidence against the outline requirements.

    TODO: [SOTA Deep Research] Implement 'checklist_verifier'
    See docs/tasks/04_SOTA_DEEP_RESEARCH_TASKS.md
    Subtask: Audit the `evidence_bank` against the `outline` requirements.
    """
    raise NotImplementedError("checklist_verifier not implemented")

def denoising_refiner(state: OverallState, config: RunnableConfig) -> OverallState:
    """
    Refines the final answer by synthesizing multiple drafts.

    TODO: [SOTA Deep Research] Implement 'denoising_refiner'
    See docs/tasks/04_SOTA_DEEP_RESEARCH_TASKS.md
    Subtask: Generate N draft answers, critique them, and synthesize the best components.
    """
    raise NotImplementedError("denoising_refiner not implemented")

def update_artifact(id: str, content: str, type: str) -> str:
    """
    Updates a collaborative artifact.

    TODO: [Open Canvas] Implement 'update_artifact' tool
    See docs/tasks/03_OPEN_CANVAS_TASKS.md
    Subtask: Create a helper function/tool `update_artifact(id, content, type)`.
    """
    raise NotImplementedError("update_artifact not implemented")

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


def _validate_single_candidate(candidate: str, flattened_queries: List[str]) -> tuple[str, bool, str | None]:
    """Helper to validate a single candidate using LLM."""
    prompt = f"""
    Verify if the following snippet actually contains relevant information for the query: "{flattened_queries[0] if flattened_queries else 'research topic'}"
    Snippet: "{candidate[:500]}..."
    Reply with "YES" or "NO" only.
    """

    # Use rate-limited LLM
    llm = _get_rate_limited_llm(
        model=app_config.model_validation,
        temperature=0,
        prompt=prompt
    )

    try:
        # Assuming invoke returns AIMessage or similar
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        if "YES" in content.upper():
            return candidate, True, None
        else:
            return candidate, False, "Result rejected by LLM Validator: Content mismatch."
    except Exception as e:
        logger.warning(f"LLM validation failed: {e}. Accepting candidate.")
        return candidate, True, None # Fail open on error


@graph_registry.describe(
    "validate_web_results",
    summary="Hybrid validation (Heuristics + LLM) with citation hard-fail.",
    tags=["validation", "quality"],
    outputs=["validated_web_research_result", "validation_notes"],
)
def validate_web_results(state: OverallState, config: RunnableConfig) -> OverallState:
    """Hybrid validation logic:
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
                    # ⚡ Bolt Optimization: Move split() outside loop to avoid redundant computation
                    summary_words = normalized_summary.split()
                    for keyword in keywords:
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

            # ⚡ Bolt Optimization: Parallelize validation calls
            # Using ThreadPoolExecutor to run blocking LLM calls in parallel
            # Since the RateLimiter is thread-safe and the network call happens outside the lock,
            # this speeds up validation significantly (e.g. 5x faster for 5 candidates).
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # Submit all validation tasks
                # Collect results as they complete (order doesn't strictly matter for set, but we usually want to preserve it)
                # To preserve order, we can map over heuristic_passed
                results = list(executor.map(lambda c: _validate_single_candidate(c, flattened_queries), heuristic_passed))
                
                for candidate, is_valid, note in results:
                    if is_valid:
                        validated_by_llm.append(candidate)
                    if note:
                        notes.append(note)

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
    """Tiered Compression:
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

        prompt = f"""
        Compress the following research notes into a concise summary.
        CRITICAL: You MUST preserve all source citations in [Title](url) format.
        Do not lose any factual claims.

        Notes:
        {combined_text}
        """

        try:
            # Use context manager to truncate if needed
            context_mgr = get_context_manager(app_config.model_compression)
            truncated_prompt = context_mgr.truncate_to_fit(prompt)
            
            # Use rate-limited LLM
            llm = _get_rate_limited_llm(
                model=app_config.model_compression,
                temperature=0,
                prompt=truncated_prompt
            )
            compressed = llm.invoke(truncated_prompt).content
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

        # Use rate-limited LLM
        llm = _get_rate_limited_llm(
            model=reasoning_model,
            temperature=1.0,
            max_retries=2,
            prompt=formatted_prompt
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

        # Use rate-limited LLM
        llm = _get_rate_limited_llm(
            model=reasoning_model,
            temperature=0,
            max_retries=2,
            prompt=formatted_prompt
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
