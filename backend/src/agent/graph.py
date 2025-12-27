import os
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END

from agent.state import OverallState
from agent.configuration import Configuration
from agent.registry import graph_registry
from agent.nodes import (
    load_context,
    scoping_node, # New Node
    generate_plan,
    planning_mode,
    planning_wait,
    planning_router,
    web_research,
    validate_web_results,
    compression_node,  # New Node
    reflection,
    finalize_answer,
    denoising_refiner, # New Node
    evaluate_research,
    update_plan,
    select_next_task,
    execution_router,
    outline_gen, # New Node
    checklist_verifier, # New Node
)
from agent.kg import kg_enrich # New Node
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
# Note: context_schema was renamed/used in main? My branch used config_schema.
# Checking main's usage: builder = StateGraph(OverallState, config_schema=Configuration) in conflict block?
# No, `StateGraph(OverallState, config_schema=Configuration)` is standard.
# Let's check if 'context_schema' was introduced in main.
# The previous read showed `builder = StateGraph(OverallState, config_schema=Configuration)` in the lower block.
# LangGraph v0.2+ uses config_schema. Check if main updated langgraph version.
# Assuming config_schema is safer for now unless I see errors.
# Note: LangGraph v1.0 deprecates config_schema in favor of context_schema (if using older langgraph),
# but sticking to config_schema per existing pattern unless updated.
# Update: Recent LangGraph versions might prefer 'config_schema' OR 'context_schema' depending on exact minor version.
# We will silence the warning or update if needed.
# Since we are on langgraph 1.x, we should check which param is preferred.
# For now, suppressing warning by continuing to use the existing pattern, or we can silence it.
# Actually, let's just stick to what works and ignore the warning for now to avoid breaking changes if user downgrades.
builder = StateGraph(OverallState, config_schema=Configuration)

# If MCP is enabled, we log it. Tools are loaded via lifespan in app.py to ensure event loop safety.
if mcp_settings.enabled:
    print(f"INFO: MCP Enabled with endpoint {mcp_settings.endpoint}")
    # Note: Tools are loaded into agent.tools_and_schemas.MCP_TOOLS during app startup.
    # Nodes (like 'web_research') access them dynamically from there at runtime.
    # Binding is handled inside the nodes to support both Gemini (native) and Gemma (adapter).

builder.add_node("load_context", load_context)
builder.add_node("scoping_node", scoping_node)
builder.add_node("generate_plan", generate_plan)
builder.add_node("planning_mode", planning_mode)
builder.add_node("planning_wait", planning_wait)
builder.add_node("web_research", web_research)
builder.add_node("validate_web_results", validate_web_results)
builder.add_node("compression_node", compression_node) # Add Compression
builder.add_node("kg_enrich", kg_enrich) # Add KG Pilot
builder.add_node("reflection", reflection)
builder.add_node("finalize_answer", finalize_answer)
builder.add_node("denoising_refiner", denoising_refiner) # Add TTD-DR Refiner
builder.add_node("update_plan", update_plan)
builder.add_node("select_next_task", select_next_task)
builder.add_node("outline_gen", outline_gen) # Add STORM Outline Gen
builder.add_node("checklist_verifier", checklist_verifier) # Add RhinoInsight Verifier

builder.add_edge(START, "load_context")
builder.add_edge("load_context", "scoping_node")

def scoping_router(state: OverallState) -> str:
    """Route based on scoping status."""
    if state.get("scoping_status") == "active":
        return "planning_wait" # Reusing planning_wait to pause for user input
    return "generate_plan"

builder.add_conditional_edges(
    "scoping_node", scoping_router, ["planning_wait", "outline_gen"]
)

builder.add_edge("outline_gen", "generate_plan")

# builder.add_edge("generate_plan", "planning_mode") # Removed as it's destination of router
builder.add_edge("generate_plan", "planning_mode")

# TODO(priority=Medium, complexity=Medium): [Open SWE] Wire up 'execution_router' to loop between 'web_research' and 'update_plan'.
# See docs/tasks/02_OPEN_SWE_TASKS.md
# Subtask: Create routing logic: `if pending_tasks: return "web_research" else: return "finalize"`.

builder.add_conditional_edges(
    "planning_mode", planning_router, ["planning_wait", "select_next_task"]
)
builder.add_conditional_edges(
    "planning_wait", planning_router, ["planning_wait", "select_next_task"]
)

# New execution loop wiring
builder.add_edge("select_next_task", "web_research")
builder.add_edge("web_research", "validate_web_results")

# Pipeline: Validate -> Compression -> KG Enrich -> Checklist Verifier -> Reflection
builder.add_edge("validate_web_results", "compression_node")
builder.add_edge("compression_node", "kg_enrich")
builder.add_edge("kg_enrich", "checklist_verifier")
builder.add_edge("checklist_verifier", "reflection")

# Reflection now goes to update_plan instead of evaluate_research
builder.add_edge("reflection", "update_plan")

# Update plan goes to execution_router to decide next step
builder.add_conditional_edges(
    "update_plan", execution_router, ["select_next_task", "denoising_refiner"]
)
builder.add_edge("denoising_refiner", END)

# Document edges for registry/tooling
graph_registry.document_edge(
    "scoping_node",
    "planning_wait",
    description="If query is ambiguous, pause to ask user clarifying questions.",
)
graph_registry.document_edge(
    "scoping_node",
    "generate_plan",
    description="If query is clear, proceed to plan generation.",
)
graph_registry.document_edge(
    "generate_plan",
    "planning_mode",
    description="Initial plan is prepared for user review.",
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

def draw_graph_png():
    """Helper to draw the graph as a PNG (for notebooks)."""
    return graph.get_graph().draw_mermaid_png()

# Removed stale TODOs for visualization as draw_graph_png is now implemented.
