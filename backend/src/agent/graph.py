import os
from agent.state import OverallState
from agent.configuration import Configuration

# Import the variant graphs
from agent.graphs.parallel import graph as parallel_graph
from agent.graphs.linear import graph as linear_graph
from agent.graphs.supervisor import graph as supervisor_graph

from agent.registry import graph_registry

# We expose the "Parallel" graph as the default for backward compatibility
# and 'langgraph.json' entry point.
# Ideally, we would use a Router Graph here, but LangGraph static config
# in langgraph.json points to a specific compiled graph object.

# To support dynamic switching via 'configurable', we can wrap them in a
# 'Meta Graph' or simply expose the default one and let the user change
# langgraph.json to point to 'graphs/linear.py' if they want that variant permanently.

# However, the user asked for a "Configurable Router".
# We can implement a simple StateGraph that has one node "router"
# which calls the appropriate subgraph based on config.

from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig

def router_node(state: OverallState, config: RunnableConfig):
    """Routes to the appropriate sub-agent based on configuration."""
    configurable = Configuration.from_runnable_config(config)
    mode = getattr(configurable, "agent_mode", "parallel")

    # We return the state as is, the routing happens in the conditional edge
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

# Also expose the registry for docs
__all__ = ["graph", "graph_registry"]
