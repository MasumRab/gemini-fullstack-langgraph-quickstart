# TODO(priority=Low, complexity=Low): See docs/tasks/upstream_compatibility.md for future splitting of this file into _nodes.py (upstream) and nodes.py (evolved).
# TODO(priority=Medium, complexity=High): Investigate and integrate 'deepagents' patterns if applicable.
# See docs/tasks/04_SOTA_DEEP_RESEARCH_TASKS.md
# Subtask: Review 'deepagents' repo for relevant nodes (e.g. hierarchical planning).
# Subtask: Adapt useful patterns to `backend/src/agent/nodes.py`.

import concurrent.futures
import difflib
import json
import logging
import os
import re
from datetime import datetime
from typing import List

from config.app_config import config as app_config
from search.router import search_router
from google.genai import Client
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.types import Send

from agent.configuration import Configuration
from agent.persistence import load_plan, save_plan
from agent.prompts import (
    answer_instructions,
    gemma_answer_instructions,
    get_current_date,
    plan_writer_instructions,
    plan_updater_instructions,
    reflection_instructions,
    checklist_instructions,
    outline_instructions,
    denoising_instructions
)
from agent.rate_limiter import get_context_manager, get_rate_limiter
from agent.registry import graph_registry
from agent.scoping_prompts import scoping_instructions
from agent.scoping_schema import ScopingAssessment
from agent.tools_and_schemas import SearchQueryList, Reflection, MCP_TOOLS, Plan, Outline
from agent.models import is_gemma_model, is_gemini_model
from agent.tool_adapter import (
    format_tools_to_json_schema,
    GEMMA_TOOL_INSTRUCTION,
    parse_tool_calls
)
from pydantic import BaseModel, Field
from agent.state import (
    Evidence,
    OverallState,
    QueryGenerationState,
    ReflectionState,
    WebSearchState,
)
from agent.utils import (
    get_research_topic,
    join_and_truncate,
)
from observability.langfuse import observe_span

logger = logging.getLogger(__name__)

# Initialize Google Search Client
genai_client = Client(api_key=os.getenv("GEMINI_API_KEY"))

# ⚡ Bolt Optimization: Pre-compile regex for keyword extraction to avoid re-compilation in loops.
KEYWORD_SPLIT_PATTERN = re.compile(r"[^\w]+")

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
    
    # max_retries=0 to pass pydantic validation but hopefully avoid passing it to client
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        api_key=os.getenv("GEMINI_API_KEY"),
    )

# ⚡ Bolt Optimization: Define Pydantic models at module level to avoid
# reconstruction overhead on every function call.

class SearchInput(BaseModel):
    query: str = Field(description="The query to search for.")

class EvidenceItem(BaseModel):
    claim: str = Field(description="A distinct factual claim found in the text.")
    source_url: str = Field(description="The source URL associated with the claim.")
    context_snippet: str = Field(description="A brief snippet of text surrounding the claim.")

class EvidenceList(BaseModel):
    items: List[EvidenceItem]


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

    TODO(priority=High, complexity=High): [SOTA Deep Research] Verify full alignment with Open Deep Research (Clarification Loop).
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

        is_gemma = "gemma" in DEFAULT_SCOPING_MODEL.lower()
        if is_gemma:
            parser = PydanticOutputParser(pydantic_object=ScopingAssessment)
            prompt_with_format = f"{prompt}\n\n{parser.get_format_instructions()}"
            try:
                response = llm.invoke(prompt_with_format)
                content = response.content if hasattr(response, "content") else str(response)
                assessment = parser.parse(content)
            except Exception as e:
                logger.error(f"Scoping LLM failed (Gemma): {e}")
                return {"scoping_status": "complete"}
        else:
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
    "generate_plan",
    summary="LLM generates a structured research plan (Todos) from the conversation context.",
    tags=["llm", "planning"],
    outputs=["plan", "search_query"],
)
def generate_plan(state: OverallState, config: RunnableConfig) -> OverallState:
    """LangGraph node that generates a research plan based on the User's question.

    Uses Gemini 2.5 Flash to create an optimized plan (list of Todos).
    Each Todo serves as a step in the research process.
    """
    with observe_span("generate_plan", config):
        configurable = Configuration.from_runnable_config(config)

        # check for custom initial search query count
        if state.get("initial_search_query_count") is None:
            state["initial_search_query_count"] = configurable.number_of_initial_queries

        # Format the prompt
        current_date = get_current_date()
        formatted_prompt = plan_writer_instructions.format(
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
            prompt=formatted_prompt
        )

        plan_todos = []
        search_queries = []

        # Check if we are using a Gemma model (requires prompt-based tool calling)
        if is_gemma_model(configurable.query_generator_model):
            logger.info(f"Using Gemma adapter for structured output (and {len(MCP_TOOLS)} MCP tools if present).")

            # Optimization for Gemma: Explicitly request keyword-optimized queries for better search performance
            gemma_optimization_note = "\n\nIMPORTANT: When generating search queries for the plan, use specific KEYWORDS rather than full questions. This improves search engine effectiveness (e.g. 'solid state battery energy density 2024' instead of 'what is the energy density...')."
            formatted_prompt += gemma_optimization_note

            # Strategy for Gemma in this node:
            # We want `Plan` as the structured output.

            # 1. Define the expected output structure as a tool schema for the adapter
            plan_tool_schema = {
                "name": "Plan",
                "description": "Output structured research plan.",
                "parameters": Plan.model_json_schema()
            }

            # 2. Add this "output tool" to the schemas
            schemas_list = [plan_tool_schema]

            # 3. Add MCP tools schemas
            if MCP_TOOLS:
                other_schemas_str = format_tools_to_json_schema(MCP_TOOLS)
                schemas_list.extend(json.loads(other_schemas_str))

            schemas_str = json.dumps(schemas_list, indent=2)

            # 4. Construct instruction
            instruction = GEMMA_TOOL_INSTRUCTION.format(tool_schemas=schemas_str)
            instruction += "\n\nCRITICAL: You MUST call the 'Plan' tool to provide your answer."

            full_prompt = f"{instruction}\n\n{formatted_prompt}"

            # 5. Invoke LLM (raw)
            response = llm.invoke(full_prompt)
            content = response.content if hasattr(response, "content") else str(response)

            tool_calls = parse_tool_calls(content)

            # 6. Extract plan from Plan tool call
            for tc in tool_calls:
                if tc["name"] == "Plan":
                    args = tc["args"]
                    if "plan" in args:
                        # Convert dicts to Todo typed dict if needed, or leave as list of dicts
                        # Pydantic model dump might be dicts already
                        raw_plan = args["plan"]
                        for item in raw_plan:
                            # Normalize
                            todo = {
                                "task": item.get("title", ""),
                                "status": item.get("status", "pending"),
                                "result": None,
                            }
                            plan_todos.append(todo)
                            search_queries.append(todo["task"])
                    break

            # Fallback if parsing failed or model didn't use tool
            if not plan_todos:
                logger.warning("Gemma did not use Plan tool. Attempting fallback parsing.")
                # Basic fallback: Treat bullet points as tasks
                lines = [line.strip("- *") for line in content.split("\n") if line.strip().startswith(("-", "*"))]
                for line in lines:
                    todo = {
                        "task": line,
                        "status": "pending",
                        "result": None,
                    }
                    plan_todos.append(todo)
                    search_queries.append(line)

        else:
            # Standard Gemini Path
            # Bind MCP tools if available
            if MCP_TOOLS:
                 logger.info(f"Binding {len(MCP_TOOLS)} MCP tools to generate_plan model.")
                 llm = llm.bind_tools(MCP_TOOLS)

            structured_llm = llm.with_structured_output(Plan)

            # Generate the plan
            try:
                result = structured_llm.invoke(formatted_prompt, config=config)
                for item in result.plan:
                    todo = {
                        "task": item.title,
                        "status": item.status,
                        "result": None,
                    }
                    plan_todos.append(todo)
                    search_queries.append(item.title)
            except Exception as e:
                logger.error(f"Failed to generate plan: {e}")
                # Fallback to single query based on research topic
                topic = get_research_topic(state["messages"])
                todo = {
                    "task": f"Research {topic}",
                    "status": "pending",
                    "result": None,
                }
                plan_todos.append(todo)
                search_queries.append(topic)

        return {"plan": plan_todos, "search_query": search_queries}


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
    summary="Executes web search using configured providers via SearchRouter, with MCP tool support.",
    tags=["search", "tool"],
    outputs=["web_research_result", "sources_gathered"],
)
def web_research(state: WebSearchState, config: RunnableConfig) -> OverallState:
    """LangGraph node that performs web research or executes MCP tools.
    Updated to use the unified SearchRouter and AppConfig.
    If MCP tools are available, uses an LLM to decide whether to search or use a tool.
    """
    with observe_span("web_research", config):
        # Handle both list (from OverallState) and str (from Send)
        raw_query = state.get("search_query")
        if isinstance(raw_query, list):
            # Use the most recent query if it's a list
            query = raw_query[-1] if raw_query else ""
        else:
            query = raw_query

        configurable = Configuration.from_runnable_config(config)

        # Helper to format search results (used by both paths)
        def format_results(results_list):
            sources = []
            texts = []
            for r in results_list:
                source = {
                    "label": r.title,
                    "short_url": r.url,
                    "value": r.url
                }
                sources.append(source)
                snippet = r.content or r.raw_content or ""
                texts.append(f"{snippet} [{r.title}]({r.url})")
            return sources, texts

        # If no MCP tools, use direct deterministic search path
        if not MCP_TOOLS:
            try:
                results = search_router.search(query, max_results=3)
                sources_gathered, web_research_results = format_results(results)
                combined_result = "\n\n".join(web_research_results)
                return {
                    "sources_gathered": sources_gathered,
                    "search_query": [query],
                    "web_research_result": [combined_result],
                }
            except Exception as e:
                logger.error(f"Web research failed: {e}")
                return {
                    "sources_gathered": [],
                    "search_query": [query],
                    "web_research_result": [],
                    "validation_notes": [f"Search failed for query '{query}': {e}"],
                }

        # --- MCP Enabled Path ---
        # We define a "search" tool so the LLM can choose between search and other tools
        from langchain_core.tools import StructuredTool

        # Accumulate sources in outer scope
        sources_gathered = []

        def run_search(query: str) -> str:
            """Perform a web search."""
            res = search_router.search(query, max_results=3)
            new_sources, texts = format_results(res)
            sources_gathered.extend(new_sources)
            return "\n\n".join(texts)

        search_tool = StructuredTool.from_function(
            func=run_search,
            name="web_search",
            description="Search the web for information.",
            args_schema=SearchInput
        )

        all_tools = [search_tool] + MCP_TOOLS

        # Create a map for fast lookup during execution
        tools_map = {t.name: t for t in all_tools}

        # Determine model
        model_name = configurable.query_generator_model # Reusing query model for research agent

        # Construct prompt
        system_prompt = f"""You are a resourceful researcher. You have a query: "{query}".
Use the available tools to answer it.
If the query requires up-to-date web info, use 'web_search'.
If it matches another tool's capability, use that tool.
Provide the raw result from the tool."""

        # Get LLM
        llm = _get_rate_limited_llm(
            model=model_name,
            temperature=0,
            prompt=system_prompt
        )

        tool_output = ""
        # sources_gathered is already initialized above for closure capture

        # ⚡ Bolt Optimization: Helper to execute a single tool call
        def _exec_single_tool(tool_call, tools_map_ref):
            t_name = tool_call.get("name")
            t_args = tool_call.get("args") or tool_call.get("arguments") or {}

            selected = tools_map_ref.get(t_name)
            if selected:
                try:
                    res = selected.invoke(t_args)
                    return f"\nResult from {t_name}:\n{res}\n"
                except Exception as e:
                    return f"\nError executing {t_name}: {e}\n"
            return ""

        if is_gemini_model(model_name):
            # Gemini Native Binding
            llm_with_tools = llm.bind_tools(all_tools)
            response = llm_with_tools.invoke(system_prompt)

            # Execute tool calls
            if response.tool_calls:
                # ⚡ Bolt Optimization: Execute tool calls in parallel
                # This significantly speeds up cases where the LLM decides to call multiple tools
                # (e.g. searching for multiple sub-topics at once)
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(response.tool_calls))) as executor:
                    # Submit all tool calls (order doesn't strictly matter for set, but we usually want to preserve it)
                    # To be deterministic, we process based on list order:
                    results = list(executor.map(lambda tc: _exec_single_tool(tc, tools_map), response.tool_calls))
                    tool_output += "".join(results)

            else:
                # If no tool called, just use response text
                tool_output = response.content

        elif is_gemma_model(model_name):
            # Gemma Adapter Path
            schema_str = format_tools_to_json_schema(all_tools)
            instruction = GEMMA_TOOL_INSTRUCTION.format(tool_schemas=schema_str)
            full_prompt = f"{instruction}\n\n{system_prompt}"

            response = llm.invoke(full_prompt)
            content = response.content if hasattr(response, "content") else str(response)

            tool_calls = parse_tool_calls(content, allowed_tools=[t.name for t in all_tools])

            if tool_calls:
                 # ⚡ Bolt Optimization: Execute tool calls in parallel for Gemma as well
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(tool_calls))) as executor:
                    results = list(executor.map(lambda tc: _exec_single_tool(tc, tools_map), tool_calls))
                    tool_output += "".join(results)
            else:
                 # Fallback: if no tool called, assume the model tried to answer directly or failed
                 # If it failed to pick a tool, we might fallback to default search?
                 # For now, treat content as answer
                 tool_output = content

        if not tool_output.strip():
            # Fallback to direct search if LLM did nothing
            logger.warning(f"LLM produced no output for research. Falling back to direct search for {query}")
            try:
                results = search_router.search(query, max_results=3)
                sources_gathered, web_research_results = format_results(results)
                tool_output = "\n\n".join(web_research_results)
            except Exception as e:
                return {
                    "sources_gathered": [],
                    "search_query": [query],
                    "web_research_result": [],
                    "validation_notes": [f"Fallback search failed: {e}"]
                }

        return {
            "sources_gathered": sources_gathered, # Note: Empty if not direct search path or parsed
            "search_query": [query],
            "web_research_result": [tool_output],
        }


@graph_registry.describe(
    "planning_mode",
    summary="Creates structured plan steps from generated queries for user review.",
    tags=["planning", "ui"],
    outputs=["planning_steps", "planning_status", "planning_feedback"],
)
def planning_mode(state: OverallState, config: RunnableConfig) -> OverallState:
    """Processes plan steps or routes based on user commands."""
    with observe_span("planning_mode", config):
        configurable = Configuration.from_runnable_config(config)

        # Prefer pre-generated plan if available
        plan = state.get("plan", [])
        if plan:
            # If we have a plan, map it to planning_steps format
            plan_steps = []
            for idx, todo in enumerate(plan):
                 plan_steps.append({
                    "id": f"plan-{idx}",
                    "title": todo["task"],
                    "query": todo["task"],  # Map task to query
                    "description": "",
                    "suggested_tool": "web_research",
                    "status": todo.get("status", "pending"),
                })
        else:
             # Backward compatibility: generate from search_query
            queries = state.get("search_query", []) or []
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

        if planning_status == "auto_approved" and not state.get("planning_steps") and not plan_steps:
             # Only return empty if truly empty
            return {"planning_steps": [], "planning_feedback": ["Generated 0 plan steps. No plan available."]}

        if last_content.startswith("/plan"):
            state["planning_status"] = "awaiting_confirmation"

        if not planning_status:
            status = (
                "awaiting_confirmation"
                if getattr(configurable, "require_planning_confirmation", False)
                else "auto_approved"
            )
        else:
            status = planning_status

        feedback = [f"Generated {len(plan_steps)} plan steps."]
        if not plan_steps:
            feedback.append("No plan available.")

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


@graph_registry.describe(
    "update_plan",
    summary="Updates the plan by marking the current task as done and adding follow-up tasks.",
    tags=["planning", "state-update"],
    outputs=["plan"],
)
def update_plan(state: OverallState, config: RunnableConfig) -> OverallState:
    """
    Updates the research plan based on latest findings.
    Implements FlowSearch/Open SWE logic to dynamically adjust tasks.
    """
    with observe_span("update_plan", config):
        configurable = Configuration.from_runnable_config(config)

        # Inputs
        current_plan = state.get("plan", [])
        
        # Prevent Recursion: Proactively mark current task as done in the context fed to LLM.
        # This ensures the LLM sees the task as completed and moves to the next one,
        # preventing infinite loops where the LLM keeps a task "pending".
        current_idx = state.get("current_task_idx")
        # specific_task_done = False # Unused variable
        
        # Create a working copy for the prompt to avoid modifying state directly yet
        prompt_plan = [dict(t) for t in current_plan]
        
        if current_idx is not None and 0 <= current_idx < len(prompt_plan):
            prompt_plan[current_idx]["status"] = "done"

        # We use all accumulated research results to ensure the LLM has full context
        results = state.get("web_research_result", [])

        current_date = get_current_date()
        research_topic = get_research_topic(state["messages"])

        formatted_prompt = plan_updater_instructions.format(
            current_date=current_date,
            research_topic=research_topic,
            current_plan=json.dumps(prompt_plan, indent=2),
            research_results="\n\n".join(results)
        )

        # Truncate if needed
        # We use the query_generator_model (or a specific planning model)
        model_name = configurable.query_generator_model
        context_mgr = get_context_manager(model_name)
        formatted_prompt = context_mgr.truncate_to_fit(formatted_prompt)

        # Get rate-limited LLM
        llm = _get_rate_limited_llm(
            model=model_name,
            temperature=0, # Low temperature for plan updates to be deterministic/stable
            prompt=formatted_prompt
        )

        plan_todos = []

        # Check if we are using a Gemma model (requires prompt-based tool calling)
        if is_gemma_model(model_name):
            logger.info("Using Gemma adapter for plan update.")

            # Reuse the "Plan" tool schema from tools_and_schemas.py
            plan_tool_schema = {
                "name": "Plan",
                "description": "Output structured research plan.",
                "parameters": Plan.model_json_schema()
            }

            schemas_list = [plan_tool_schema]
            schemas_str = json.dumps(schemas_list, indent=2)

            instruction = GEMMA_TOOL_INSTRUCTION.format(tool_schemas=schemas_str)
            instruction += "\n\nCRITICAL: You MUST call the 'Plan' tool to provide your answer."

            full_prompt = f"{instruction}\n\n{formatted_prompt}"

            try:
                response = llm.invoke(full_prompt)
                content = response.content if hasattr(response, "content") else str(response)
                tool_calls = parse_tool_calls(content)

                for tc in tool_calls:
                    if tc["name"] == "Plan":
                        args = tc["args"]
                        if "plan" in args:
                            raw_plan = args["plan"]
                            for item in raw_plan:
                                todo = {
                                    "title": item.get("title", ""),
                                    "description": item.get("description", ""),
                                    "status": item.get("status", "pending"),
                                    "query": item.get("title", ""),
                                }
                                plan_todos.append(todo)
                        break
            except Exception as e:
                logger.error(f"Gemma plan update failed: {e}")
                # Fallback: keep existing plan to avoid data loss
                return {"plan": current_plan}

        else:
            # Standard Gemini Path
            structured_llm = llm.with_structured_output(Plan)
            try:
                result = structured_llm.invoke(formatted_prompt, config=config)
                for item in result.plan:
                    todo = {
                        "title": item.title,
                        "description": item.description,
                        "status": item.status,
                        "query": item.title
                    }
                    plan_todos.append(todo)
            except Exception as e:
                logger.error(f"Failed to update plan (Gemini): {e}")
                return {"plan": current_plan}



        # Safety Fallback: Ensure the executed task is actually marked as done in the new plan
        # This overrides the LLM if it fails to update the status, preventing infinite loops.
        if current_idx is not None and 0 <= current_idx < len(current_plan):
             executed_title = current_plan[current_idx].get("title")
             # Try to find matching task in new plan
             for task in plan_todos:
                 # Check title match (robust against reordering)
                 if task.get("title") == executed_title:
                     if task.get("status") != "done":
                         logger.warning(f"Force-marking task '{executed_title}' as done (LLM left it pending).")
                         task["status"] = "done"
                     break
        
        return {"plan": plan_todos}


@graph_registry.describe(
    "select_next_task",
    summary="Selects the next pending task from the plan for execution.",
    tags=["planning", "routing"],
    outputs=["current_task_idx", "search_query"],
)
def select_next_task(state: OverallState, config: RunnableConfig) -> OverallState:
    """Selects the next pending task from the plan."""
    plan = state.get("plan", [])
    for idx, task in enumerate(plan):
        if task.get("status") == "pending":
            return {
                "current_task_idx": idx,
                "search_query": [task.get("query") or task.get("title")]
            }

    # Should be handled by execution_router, but safety fallback
    return {"current_task_idx": None}


def execution_router(state: OverallState) -> str:
    """Routes to next task or final answer based on plan status."""
    plan = state.get("plan", [])
    if any(t.get("status") == "pending" for t in plan):
        return "select_next_task"
    return "denoising_refiner"

@graph_registry.describe(
    "outline_gen",
    summary="Generates a hierarchical outline (Sections -> Subsections) for the research.",
    tags=["planning", "outline"],
    outputs=["outline"],
)
def outline_gen(state: OverallState, config: RunnableConfig) -> OverallState:
    """
    Generates a hierarchical outline (Sections -> Subsections) for the research.
    Implements STORM pattern for structured long-form content generation.
    See docs/tasks/04_SOTA_DEEP_RESEARCH_TASKS.md
    """
    with observe_span("outline_gen", config):
        messages = state.get("messages", [])
        topic = get_research_topic(messages)
        
        configurable = Configuration.from_runnable_config(config)
        model_name = configurable.query_generator_model # Use a strong model

        prompt = outline_instructions.format(
            current_date=get_current_date(),
            research_topic=topic
        )

        llm = _get_rate_limited_llm(
            model=model_name,
            temperature=0.2, # Slight variety for creative outlines
            prompt=prompt
        )

        try:
            # For structured output, we use with_structured_output if supported,
            # or manual parsing for Gemma.
            is_gemma = "gemma" in model_name.lower()
            if is_gemma:
                # Simple parsing logic for Gemma (expects JSON in markdown)
                # In a real scenario, we'd use the tool_adapter or PydanticOutputParser
                response = llm.invoke(prompt)
                content = response.content if hasattr(response, "content") else str(response)
                # Heuristic: Find first { and last }
                import json
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1:
                    outline_data = json.loads(content[start:end+1])
                else:
                    raise ValueError("Could not find JSON in Gemma output")
            else:
                structured_llm = llm.with_structured_output(Outline)
                outline_data = structured_llm.invoke(prompt)

            return {"outline": outline_data}
        except Exception as e:
            logger.error(f"Outline generation failed: {e}")
            # Return a simple default outline to keep the graph moving
            return {
                "outline": {
                    "title": topic,
                    "sections": [
                        {"title": "Introduction", "subsections": [{"title": "Overview", "description": "General summary of the topic"}]},
                        {"title": "Analysis", "subsections": [{"title": "Key Findings", "description": "Main results of the research"}]},
                        {"title": "Conclusion", "subsections": [{"title": "Summary", "description": "Final thoughts"}]}
                    ]
                }
            }

def flow_update(state: OverallState, config: RunnableConfig) -> OverallState:
    """
    Dynamically expands the research DAG based on findings.

    Fine-grained implementation guide:
    
    TODO(priority=High, complexity=Low): [flow_update:1] Extract current task from state
    - Read `current_task_idx` and `plan` from state
    - Get the task object being evaluated
    
    TODO(priority=High, complexity=Medium): [flow_update:2] Analyze task completion
    - Compare task query against `web_research_result`
    - Use fuzzy matching or LLM to determine if task is adequately answered
    - Return completion_score (0.0-1.0)
    
    TODO(priority=High, complexity=Medium): [flow_update:3] Identify knowledge gaps
    - Parse research results for "unclear", "contradictory", or "insufficient" signals
    - Generate list of follow-up questions if gaps detected
    
    TODO(priority=Medium, complexity=High): [flow_update:4] DAG expansion logic
    - If gaps detected: Create new tasks and insert into plan
    - If task complete: Mark status='done' and increment current_task_idx
    - If no more tasks: Set research_complete=True
    
    TODO(priority=Low, complexity=Low): [flow_update:5] Return updated state
    - Return dict with updated `plan`, `current_task_idx`, `research_complete`
    
    See docs/tasks/04_SOTA_DEEP_RESEARCH_TASKS.md
    """
    raise NotImplementedError("flow_update not implemented")

@graph_registry.describe(
    "content_reader",
    summary="Extracts structured evidence (claims, sources) from raw search results.",
    tags=["extraction", "nlp"],
    outputs=["evidence_bank"],
)
def content_reader(state: OverallState, config: RunnableConfig) -> OverallState:
    """
    Extracts structured evidence from raw web content.
    Implements ManuSearch logic to convert raw search results into `Evidence` objects.
    """
    with observe_span("content_reader", config):
        # Prefer validated results, fallback to raw
        results = state.get("validated_web_research_result") or state.get("web_research_result", [])
        if not results:
            return {"evidence_bank": []}

        configurable = Configuration.from_runnable_config(config)
        # Re-use query model or define a new one in config?
        # For now, using query_generator_model as it is usually a strong model (Gemini/Gemma).
        model_name = configurable.query_generator_model

        # Prepare content
        # Limit content size to avoid context window issues
        # ⚡ Bolt Optimization: Use join_and_truncate to avoid building full string before slicing.
        combined_text = join_and_truncate(results, 50000)

        prompt = f"""
        Analyze the following search results and extract structured evidence.
        For each distinct factual claim, provide:
        1. The Claim (concise statement).
        2. The Source URL (found in the text as [Title](url)).
        3. The Context Snippet (quote supports the claim).

        Search Results:
        {combined_text}
        """

        # Get rate-limited LLM
        llm = _get_rate_limited_llm(
            model=model_name,
            temperature=0,
            prompt=prompt
        )

        extracted_evidence: List[Evidence] = []

        if is_gemma_model(model_name):
            # Gemma Adapter Path
            schema = {
                "name": "EvidenceList",
                "description": "Extract structured evidence.",
                "parameters": EvidenceList.model_json_schema()
            }
            schemas_str = json.dumps([schema], indent=2)
            instruction = GEMMA_TOOL_INSTRUCTION.format(tool_schemas=schemas_str)
            full_prompt = f"{instruction}\n\n{prompt}"

            try:
                response = llm.invoke(full_prompt)
                content = response.content if hasattr(response, "content") else str(response)
                tool_calls = parse_tool_calls(content)

                for tc in tool_calls:
                    if tc["name"] == "EvidenceList":
                        items = tc["args"].get("items", [])
                        for item in items:
                            extracted_evidence.append({
                                "claim": item.get("claim", ""),
                                "source_url": item.get("source_url", ""),
                                "context_snippet": item.get("context_snippet", "")
                            })
            except Exception as e:
                logger.error(f"Content Reader (Gemma) failed: {e}")

        else:
            # Gemini Structured Output
            structured_llm = llm.with_structured_output(EvidenceList)
            try:
                result = structured_llm.invoke(prompt)
                if result and result.items:
                    for item in result.items:
                        extracted_evidence.append({
                            "claim": item.claim,
                            "source_url": item.source_url,
                            "context_snippet": item.context_snippet
                        })
            except Exception as e:
                logger.error(f"Content Reader (Gemini) failed: {e}")

        return {"evidence_bank": extracted_evidence}

def research_subgraph(state: OverallState, config: RunnableConfig) -> OverallState:
    """
    Executes a recursive research subgraph for a specific sub-topic.

    Fine-grained implementation guide:
    
    TODO(priority=High, complexity=Low): [research_subgraph:1] Extract sub-topic query
    - Read `subtopic_query` from state (passed via Send)
    - Validate query is non-empty string
    
    TODO(priority=High, complexity=Medium): [research_subgraph:2] Create child graph config
    - Clone parent config with new thread_id suffix (e.g., `{parent_id}_sub_{idx}`)
    - Set recursion_depth = parent_depth + 1
    - Set max_recursion_depth limit (default: 2)
    
    TODO(priority=High, complexity=Medium): [research_subgraph:3] Guard against infinite recursion
    - Check recursion_depth against max_recursion_depth
    - If exceeded: Return early with partial results and warning
    
    TODO(priority=High, complexity=High): [research_subgraph:4] Invoke child graph
    - Import graph from agent.graph
    - Call graph.invoke({"messages": [subtopic_query]}, child_config)
    - Handle exceptions gracefully
    
    TODO(priority=Medium, complexity=Medium): [research_subgraph:5] Merge child results
    - Extract `web_research_result` and `evidence_bank` from child output
    - Append to parent state's lists
    - Deduplicate sources
    
    TODO(priority=Low, complexity=Low): [research_subgraph:6] Return merged state
    - Return dict with updated `web_research_result`, `evidence_bank`, `sources_gathered`
    
    See docs/tasks/04_SOTA_DEEP_RESEARCH_TASKS.md
    """
    raise NotImplementedError("research_subgraph not implemented")

@graph_registry.describe(
    "checklist_verifier",
    summary="Audits gathered evidence against outline requirements.",
    tags=["validation", "quality"],
    outputs=["validation_notes"],
)
def checklist_verifier(state: OverallState, config: RunnableConfig) -> OverallState:
    """
    Audits gathered evidence against the outline requirements.

    Generates a markdown report flagging missing citations or insufficient evidence
    for each section of the outline.
    """
    with observe_span("checklist_verifier", config):
        configurable = Configuration.from_runnable_config(config)
        outline = state.get("outline")
        evidence_bank = state.get("evidence_bank", [])

        # Fallback to research summaries if evidence bank is empty
        if not evidence_bank:
            evidence_source = state.get("validated_web_research_result") or state.get("web_research_result", [])
            evidence_text = "\n\n".join(evidence_source)
        else:
            # Format evidence bank items
            evidence_items = []
            for item in evidence_bank:
                evidence_items.append(f"Claim: {item.get('claim')}\nSource: {item.get('source_url')}\nContext: {item.get('context_snippet')}")
            evidence_text = "\n---\n".join(evidence_items)

        if not outline:
            return {"validation_notes": ["Skipped Checklist Verification: No outline available."]}

        if not evidence_text:
             return {"validation_notes": ["Skipped Checklist Verification: No evidence gathered."]}

        prompt = checklist_instructions.format(
            outline=json.dumps(outline, indent=2) if isinstance(outline, dict) else str(outline),
            evidence=evidence_text
        )

        # Use rate-limited LLM (using answer model or validation model)
        model = configurable.answer_model

        llm = _get_rate_limited_llm(
            model=model,
            temperature=0,
            prompt=prompt
        )

        try:
            response = llm.invoke(prompt)
            report = response.content if hasattr(response, "content") else str(response)
            return {"validation_notes": [report]}
        except Exception as e:
            logger.error(f"Checklist verification failed: {e}")
            return {"validation_notes": [f"Checklist verification failed: {e}"]}

@graph_registry.describe(
    "denoising_refiner",
    summary="Refines the final answer by synthesizing multiple drafts (TTD-DR).",
    tags=["synthesis", "quality"],
    outputs=["messages", "artifacts"],
)
def denoising_refiner(state: OverallState, config: RunnableConfig) -> OverallState:
    """
    Refines the final answer by synthesizing multiple drafts.
    Implements TTD-DR pattern for high-fidelity report synthesis.
    Ensures URL restoration for citations.
    """
    with observe_span("denoising_refiner", config):
        configurable = Configuration.from_runnable_config(config)
        model_name = configurable.answer_model
        
        # 1. Gather research context
        messages = state.get("messages", [])
        topic = get_research_topic(messages)
        
        web_results = state.get("validated_web_research_result") or state.get("web_research_result", [])
        summaries = "\n\n".join(web_results)
        
        # 2. Generate Draft 1 (Standard Answer) - Use Gemma instructions if appropriate
        if is_gemma_model(model_name):
            prompt_1 = gemma_answer_instructions.format(
                current_date=get_current_date(),
                research_topic=topic,
                summaries=summaries
            )
        else:
            prompt_1 = answer_instructions.format(
                current_date=get_current_date(),
                research_topic=topic,
                summaries=summaries
            )
        
        llm_1 = _get_rate_limited_llm(model=model_name, temperature=0.7, prompt=prompt_1)
        draft_1 = llm_1.invoke(prompt_1).content
        
        # 3. Generate Draft 2 (Technical/Deep focus)
        prompt_2 = draft_1 + "\n\nNote: Focus more on specific data points, technical specifics and precise metrics."
        llm_2 = _get_rate_limited_llm(model=model_name, temperature=0.5, prompt=prompt_2)
        draft_2 = llm_2.invoke(prompt_2).content
        
        # 4. Denoise/Synthesize
        refine_prompt = denoising_instructions.format(
            current_date=get_current_date(),
            drafts=f"--- DRAFT 1 ---\n{draft_1}\n\n--- DRAFT 2 ---\n{draft_2}"
        )
        
        llm_refiner = _get_rate_limited_llm(model=model_name, temperature=0, prompt=refine_prompt)
        final_content = llm_refiner.invoke(refine_prompt).content
        
        # 5. Restore URLs (Critical for Citations)
        if "sources_gathered" in state:
            for source in state["sources_gathered"]:
                pattern = re.escape(source["short_url"])
                if re.search(pattern, final_content):
                    final_content = re.sub(pattern, source["value"], final_content)

        # 6. Create Artifact for Open Canvas
        artifact_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        artifact = {
            "id": artifact_id,
            "title": f"Research Report: {topic}",
            "content": final_content,
            "type": "markdown",
            "version": 1
        }
        
        return {
            "messages": [AIMessage(content=f"I have finalized the comprehensive research report. You can interact with it in the preview panel.\n\nSummary: {final_content[:300]}...")],
            "artifacts": {artifact_id: artifact}
        }

def update_artifact(id: str, content: str, type: str) -> str:
    """
    Updates a collaborative artifact.
    Returns a JSON string representation of the updated artifact.
    """
    artifact = {
        "id": id,
        "content": content,
        "type": type,
        "created_at": datetime.now().isoformat(),
    }
    return json.dumps(artifact)

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
        # Switch to sequential execution via select_next_task
        return "select_next_task"

    if last_content.startswith("/confirm_plan"):
        state["planning_status"] = "confirmed"
        # Switch to sequential execution via select_next_task
        return "select_next_task"

    if getattr(configurable, "require_planning_confirmation", False) and planning_status != "confirmed":
        return "planning_wait"

    # Default: Proceed to execution (sequential)
    return "select_next_task"


def _flatten_queries(queries: List) -> List[str]:
    """Flatten nested query lists."""
    flattened: List[str] = []
    for item in queries:
        if isinstance(item, list):
            flattened.extend(_flatten_queries(item))
        elif isinstance(item, str):
            flattened.append(item)
    return flattened


# ⚡ Bolt Optimization: Pre-compile regex patterns for performance
TOKEN_SPLIT_PATTERN = re.compile(r"[^\w]+")
CITATION_PATTERN = re.compile(r'\[[^\]]+\]\(https?://[^\)]+\)')


def _keywords_from_queries(queries: List[str]) -> List[str]:
    """Extract keywords from queries (tokens >= 4 chars)."""
    keywords: set[str] = set()
    for query in queries:
        # ⚡ Bolt Optimization: Use pre-compiled regex and set for deduplication
        for token in KEYWORD_SPLIT_PATTERN.split(query.lower()):
            if len(token) >= 4:
                keywords.add(token)
    return list(keywords)


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

        # ⚡ Bolt Optimization: Deduplicate keywords to avoid redundant fuzzy matching calls.
        # This reduces expensive O(N) calls to difflib.get_close_matches for duplicate tokens.
        keywords = list(set(_keywords_from_queries(flattened_queries)))

        validated: List[str] = []
        notes: List[str] = []

        # 1. Heuristics (Pre-filter)
        heuristic_passed = []

        for idx, summary in enumerate(summaries):
            normalized_summary = summary.lower()
            match_found = False

            # ⚡ Bolt Optimization: Use pre-compiled regex
            has_citation = bool(CITATION_PATTERN.search(summary))

            if app_config.require_citations and not has_citation:
                notes.append(f"Result {idx+1} rejected: Missing citations (Hard Fail).")
                continue

            if keywords:
                if any(keyword in normalized_summary for keyword in keywords):
                    match_found = True
                else:
                    # ⚡ Bolt Optimization: Deduplicate words before fuzzy matching.
                    # Reduces Search Space: For a 5000-word summary with ~150 unique words,
                    # this speeds up get_close_matches by ~97%.
                    summary_words = list(set(normalized_summary.split()))
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
            prompt=formatted_prompt
        )

        is_gemma = "gemma" in reasoning_model.lower()
        if is_gemma:
            parser = PydanticOutputParser(pydantic_object=Reflection)
            prompt_with_format = f"{formatted_prompt}\n\n{parser.get_format_instructions()}"
            try:
                response = llm.invoke(prompt_with_format, config=config)
                content = response.content if hasattr(response, "content") else str(response)
                result = parser.parse(content)
            except Exception as e:
                logger.error(f"Reflection LLM failed (Gemma): {e}")
                # Fallback to sufficient to avoid infinite loops on error
                return {
                    "is_sufficient": True,
                    "knowledge_gap": "Error parsing reflection.",
                    "follow_up_queries": [],
                    "research_loop_count": state["research_loop_count"],
                    "number_of_ran_queries": len(state["search_query"]),
                }
        else:
            result = llm.with_structured_output(Reflection).invoke(formatted_prompt, config=config)

        return {
            "is_sufficient": result.is_sufficient,
            "knowledge_gap": result.knowledge_gap,
            "follow_up_queries": result.follow_up_queries,
            "research_loop_count": state["research_loop_count"],
            "number_of_ran_queries": len(state["search_query"]),
        }






