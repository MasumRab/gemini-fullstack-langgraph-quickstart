from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph

from agent.configuration import Configuration
from agent.nodes import (
    continue_to_web_research,
    finalize_answer,
    generate_plan,
    load_context,
    web_research,
)
from agent.state import OverallState

load_dotenv()

# Upstream / Minimal Graph: No Planning, No Reflection, No Validation.
# Just Query -> Search -> Answer.

builder = StateGraph(OverallState, config_schema=Configuration)

builder.add_node("load_context", load_context)
builder.add_node("generate_plan", generate_plan)
builder.add_node("web_research", web_research)
builder.add_node("finalize_answer", finalize_answer)

builder.add_edge(START, "load_context")
builder.add_edge("load_context", "generate_plan")

# Fan out to all queries immediately
builder.add_conditional_edges(
    "generate_plan",
    continue_to_web_research,
    ["web_research"]
)

# Collect results and finalize immediately (No Reflection loop)
builder.add_edge("web_research", "finalize_answer")
builder.add_edge("finalize_answer", END)

graph = builder.compile(name="pro-search-agent-upstream")
