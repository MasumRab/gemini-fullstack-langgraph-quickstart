import os
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END

from agent.state import OverallState
from agent.configuration import Configuration
from agent.registry import graph_registry
from agent.nodes import (
    load_context,
    generate_query,
    planning_mode,
    planning_wait,
    planning_router,
    web_research,
    validate_web_results,
    compression_node,
    reflection,
    finalize_answer,
    evaluate_research,
)
from agent.kg import kg_enrich
from agent.mcp_config import load_mcp_settings, validate
from agent.memory_tools import save_plan_tool, load_plan_tool

# Ensure config is loaded
from config.app_config import config

load_dotenv()

# Load and validate MCP settings at module level to ensure early failure on misconfiguration
# This does NOT connect to servers yet, only validates config structure
mcp_settings = load_mcp_settings()
try:
    validate(mcp_settings)
except ValueError as e:
    # We log but do not crash the module load unless critical
    # For now, we print to stderr as a warning
    print(f"WARN: MCP Configuration invalid: {e}")

if os.getenv("GEMINI_API_KEY") is None:
    raise ValueError("GEMINI_API_KEY is not set")

# Create our Agent Graph using the standard builder wiring
# Note: LangGraph v1.0 deprecates config_schema in favor of context_schema (Comment may be outdated for v0.2)
builder = StateGraph(OverallState, config_schema=Configuration)


# If MCP is enabled, we would register MCP tools here or modify the schema
# For now, this is a placeholder wiring to satisfy the requirement of "Agent Wiring"
if mcp_settings.enabled:
    print(f"INFO: MCP Enabled with endpoint {mcp_settings.endpoint}")
    # Note: Tools are loaded into agent.tools_and_schemas.MCP_TOOLS during app startup.
    # Nodes can access them from there at runtime.
    # TODO: [MCP Integration] Bind MCP tools to 'web_research' or new 'tool_node'.
    # See docs/tasks/01_MCP_TASKS.md
    # Subtask: In `web_research` (or new node), bind these tools to the LLM.
    # builder.bind_tools(mcp_tools)
    # In future: builder.bind_tools(mcp_tools)
    # builder.bind_tools([save_plan_tool, load_plan_tool]) # Example wiring

builder.add_node("load_context", load_context)
# TODO: Phase 2 - Rename 'generate_query' to 'generate_plan'
# This node will eventually generate a structured Todo list and bind MCP tools (load_thread_plan, save_thread_plan)
# to allow the agent to manage long-term state.
builder.add_node("generate_query", generate_query)
builder.add_node("planning_mode", planning_mode)
builder.add_node("planning_wait", planning_wait)
builder.add_node("web_research", web_research)
builder.add_node("validate_web_results", validate_web_results)
builder.add_node("compression_node", compression_node)
builder.add_node("kg_enrich", kg_enrich)
builder.add_node("reflection", reflection)
builder.add_node("finalize_answer", finalize_answer)

builder.add_edge(START, "load_context")
builder.add_edge("load_context", "generate_query")
# TODO: Future - Insert 'save_plan' step here to persist the generated plan automatically
builder.add_edge("generate_query", "planning_mode")

# TODO(priority=Medium, complexity=Medium): [Open SWE] Wire up 'execution_router' to loop between 'web_research' and 'update_plan'.
# See docs/tasks/02_OPEN_SWE_TASKS.md
# Subtask: Create routing logic: `if pending_tasks: return "web_research" else: return "finalize"`.

builder.add_conditional_edges(
    "planning_mode", planning_router, ["planning_wait", "web_research"]
)
builder.add_conditional_edges(
    "planning_wait", planning_router, ["planning_wait", "web_research"]
)
builder.add_edge("web_research", "validate_web_results")

# Pipeline: Validate -> Compression -> KG Enrich -> Reflection
builder.add_edge("validate_web_results", "compression_node")
builder.add_edge("compression_node", "kg_enrich")
builder.add_edge("kg_enrich", "reflection")

builder.add_conditional_edges(
    "reflection", evaluate_research, ["web_research", "finalize_answer"]
)
builder.add_edge("finalize_answer", END)

# Document edges for registry/tooling
graph_registry.document_edge(
    "generate_query",
    "planning_mode",
    description="Initial queries are summarized into a plan for user review.",
)
graph_registry.document_edge(
    "planning_mode",
    "web_research",
    description="Once approved (or auto-approved), plan steps dispatch to web research.",
)
graph_registry.document_edge(
    "planning_mode",
    "planning_wait",
    description="If confirmation is required, execution pauses for user feedback.",
)
graph_registry.document_edge(
    "web_research",
    "validate_web_results",
    description="Heuristic validation guards against irrelevant summaries.",
)
graph_registry.document_edge(
    "validate_web_results",
    "compression_node",
    description="Validated results are compressed/summarized.",
)
graph_registry.document_edge(
    "compression_node",
    "kg_enrich",
    description="Compressed results are optionally enriched into KG.",
)
graph_registry.document_edge(
    "kg_enrich",
    "reflection",
    description="Enriched/Compressed results reach the reasoning loop.",
)
graph_registry.document_edge(
    "reflection",
    "web_research",
    description="Follow-up queries trigger additional web searches until sufficient.",
)
graph_registry.document_edge(
    "reflection",
    "finalize_answer",
    description="Once sufficient or max loops reached, finalize the response.",
)
graph_registry.document_edge(
    "finalize_answer",
    END,
    description="Graph terminates after final answer is produced.",
)

graph = builder.compile(name="pro-search-agent")

# TODO(priority=High, complexity=Low): Add visualization support for notebooks.
# See docs/tasks/03_OPEN_CANVAS_TASKS.md
# Subtask: Implement `get_graph().draw_mermaid_png()` compatible method.
# Subtask: Ensure `visualize_graphs.py` uses this method.
