from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from agent.configuration import Configuration

# Import the variant graphs
# graph.py now exports the Parallel/Default graph
from agent.graph import graph as parallel_graph
from agent.graphs.linear import graph as linear_graph
from agent.graphs.supervisor import graph as supervisor_graph
from agent.registry import graph_registry
from agent.state import OverallState

# Meta-Router Graph
# This graph acts as a facade, routing the initial request to the configured agent variant.

def router_node(state: OverallState, config: RunnableConfig):
    """Routes to the appropriate sub-agent based on configuration."""
    # We simply pass the state through; routing happens in the conditional edge.
    return {"messages": state.get("messages", [])}

def select_agent(state: OverallState, config: RunnableConfig) -> str:
    configurable = Configuration.from_runnable_config(config)
    # Default to parallel if not specified
    mode = getattr(configurable, "agent_mode", "parallel")

    if mode == "linear":
        return "linear_agent"
    elif mode == "supervisor":
        return "supervisor_agent"
    else:
        return "parallel_agent"

builder = StateGraph(OverallState, config_schema=Configuration)
builder.add_node("router", router_node)
builder.add_node("parallel_agent", parallel_graph)
builder.add_node("linear_agent", linear_graph)
builder.add_node("supervisor_agent", supervisor_graph)

builder.add_edge(START, "router")
builder.add_conditional_edges(
    "router",
    select_agent,
    {
        "parallel_agent": "parallel_agent",
        "linear_agent": "linear_agent",
        "supervisor_agent": "supervisor_agent"
    }
)
builder.add_edge("parallel_agent", END)
builder.add_edge("linear_agent", END)
builder.add_edge("supervisor_agent", END)

# Compile the meta-graph
graph = builder.compile()

# Observability injection (Opt-in)
# This wraps the graph with a default configuration containing the Langfuse callback if enabled.
try:
    from observability.config import is_enabled
    from observability.langfuse import get_langfuse_handler

    if is_enabled():
        handler = get_langfuse_handler()
        if handler:
            graph = graph.with_config({"callbacks": [handler]})
except ImportError:
    pass

__all__ = ["graph", "graph_registry"]
