"""Orchestration layer for dynamic tool and agent management.

This module provides:
1. ToolRegistry - Register and discover tools
2. AgentPool - Register and allocate sub-agents
3. OrchestratedGraphBuilder - Build graphs with dynamic tool/agent selection

Usage:
    from agent.orchestration import ToolRegistry, AgentPool, build_orchestrated_graph

    # Register custom tools
    registry = ToolRegistry()
    registry.register("semantic_search", my_semantic_search_tool)
    registry.register("code_executor", my_code_tool)

    # Register sub-agents
    agents = AgentPool()
    agents.register("researcher", researcher_agent)
    agents.register("fact_checker", fact_check_agent)

    # Build orchestrated graph
    graph = build_orchestrated_graph(
        tools=registry,
        agents=agents,
        coordinator_model=GEMINI_PRO,
    )
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agent.configuration import Configuration
from agent.models import GEMINI_PRO
from agent.state import OverallState
from agent.utils import get_cached_llm

logger = logging.getLogger(__name__)


# =============================================================================
# Tool Registry
# =============================================================================


@dataclass
class ToolSpec:
    """Specification for a registered tool."""

    name: str
    func: Callable
    description: str
    category: str = "general"
    requires_confirmation: bool = False


class ToolRegistry:
    """Registry for dynamically adding and discovering tools.

    Usage:
        registry = ToolRegistry()

        # Register a function as a tool
        registry.register(
            "web_search",
            web_search_func,
            description="Search the web for information",
            category="search",
        )

        # Get all tools
        tools = registry.get_tools()

        # Get tools by category
        search_tools = registry.get_tools(category="search")
    """

    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}
        self._load_default_tools()

    def _load_default_tools(self):
        """
        Register available default tools into the registry (web_search, rag_search, tavily_search) by probing optional project modules and adding corresponding ToolSpec entries.
        
        Each tool is registered only when its provider module is importable and any provider-level enablement checks pass. Missing or unavailable providers are skipped and a debug message is emitted.
        """
        # Web search
        try:
            from search.router import search_router

            self.register(
                "web_search",
                lambda query: search_router.search(query, max_results=3),
                description="Search the web for current information",
                category="search",
            )
        except ImportError:
            logger.debug("search.router not available; web_search tool not registered")

        # RAG retrieval
        try:
            from agent.rag import create_rag_tool, is_rag_enabled

            if is_rag_enabled():
                rag_tool = create_rag_tool([])
                if rag_tool:
                    self.register(
                        "rag_search",
                        rag_tool.invoke,
                        description="Search internal knowledge base",
                        category="search",
                    )
        except ImportError:
            logger.debug("agent.rag not available; rag_search tool not registered")

        # Tavily (if available)
        try:
            from agent.research_tools import TAVILY_AVAILABLE, tavily_search_multiple

            if TAVILY_AVAILABLE:
                self.register(
                    "tavily_search",
                    tavily_search_multiple,
                    description="Deep web search using Tavily API",
                    category="search",
                )
        except ImportError:
            logger.debug("agent.research_tools not available; tavily_search tool not registered")

    def register(
        self,
        name: str,
        func: Callable,
        description: str = "",
        category: str = "general",
        requires_confirmation: bool = False,
    ):
        """
        Register or update a tool specification in the registry.
        
        Parameters:
            name (str): Unique identifier for the tool.
            func (Callable): Callable invoked when the tool is executed.
            description (str): Human-readable description shown to coordinators or users; defaults to "Tool: {name}" when empty.
            category (str): Classification used to filter or group tools (default "general").
            requires_confirmation (bool): If True, indicates the tool requires explicit user confirmation before use.
        """
        self._tools[name] = ToolSpec(
            name=name,
            func=func,
            description=description or f"Tool: {name}",
            category=category,
            requires_confirmation=requires_confirmation,
        )
        logger.info(f"Registered tool: {name} [{category}]")

    def unregister(self, name: str):
        """
        Unregister a tool from the registry by name.
        
        If a tool with the given name exists in the registry, removes its entry; does nothing if the name is not registered.
        
        Parameters:
            name (str): The registered tool name to remove.
        """
        if name in self._tools:
            del self._tools[name]

    def get_tools(self, category: str | None = None) -> List[BaseTool]:
        """
        Return registered tools as LangChain StructuredTool objects, optionally filtered by category.
        
        Parameters:
            category (str | None): If provided, only tools whose ToolSpec.category equals this value are returned; if None, all registered tools are returned.
        
        Returns:
            List[BaseTool]: A list of LangChain StructuredTool instances corresponding to the registered tools (empty list if no tools match).
        """
        tools = []
        for spec in self._tools.values():
            if category and spec.category != category:
                continue
            # Convert to LangChain tool
            lc_tool = StructuredTool.from_function(
                func=spec.func,
                name=spec.name,
                description=spec.description,
            )
            tools.append(lc_tool)
        return tools

    def get_tool_names(self) -> List[str]:
        """
        List names of all registered tools.
        
        Returns:
            tool_names (List[str]): A list of registered tool names.
        """
        return list(self._tools.keys())

    def get_tool(self, name: str) -> ToolSpec | None:
        """
        Retrieve the ToolSpec registered under the given tool name.
        
        Parameters:
        	name (str): The name of the tool to look up.
        
        Returns:
        	ToolSpec | None: The ToolSpec for the tool if found, `None` if no tool is registered under that name.
        """
        return self._tools.get(name)


# =============================================================================
# Agent Pool
# =============================================================================


@dataclass
class AgentSpec:
    """Specification for a registered agent."""

    name: str
    graph: Any  # Compiled StateGraph
    description: str
    capabilities: List[str] = field(default_factory=list)


class AgentPool:
    """Pool of sub-agents for task allocation.

    Usage:
        pool = AgentPool()

        # Register a sub-agent
        pool.register(
            "researcher",
            researcher_graph,
            description="Performs deep web research",
            capabilities=["search", "synthesis"],
        )

        # Get agent for a task
        agent = pool.get_agent_for_task("find information about X")
    """

    def __init__(self):
        self._agents: Dict[str, AgentSpec] = {}
        self._load_default_agents()

    def _load_default_agents(self):
        """
        Register available default sub-agents discovered in the project into the pool.
        
        Attempts to import and register these optional agents by name and capabilities:
        - "quick_search": fast minimal search agent with ["search", "quick_answer"]
        - "planner": planning and reflection agent with ["planning", "search", "reflection", "synthesis"]
        - "deep_researcher": full-featured research agent with ["planning", "search", "kg", "compression", "synthesis"]
        
        If an agent module is not importable, the function skips registration for that agent and emits a debug log message.
        """
        try:
            from agent.graphs.upstream import graph as upstream

            self.register(
                "quick_search",
                upstream,
                description="Fast, minimal search agent",
                capabilities=["search", "quick_answer"],
            )
        except ImportError:
            logger.debug("agent.graphs.upstream not available; quick_search agent not registered")

        try:
            from agent.graphs.planning import graph as planning

            self.register(
                "planner",
                planning,
                description="Research agent with planning and reflection",
                capabilities=["planning", "search", "reflection", "synthesis"],
            )
        except ImportError:
            logger.debug("agent.graphs.planning not available; planner agent not registered")

        try:
            from agent.graph import graph as enriched

            self.register(
                "deep_researcher",
                enriched,
                description="Full-featured research with KG and compression",
                capabilities=["planning", "search", "kg", "compression", "synthesis"],
            )
        except ImportError:
            logger.debug("agent.graph not available; deep_researcher agent not registered")

    def register(
        self,
        name: str,
        graph: Any,
        description: str = "",
        capabilities: List[str] = None,
    ):
        """
        Register or update a sub-agent in the pool.
        
        Adds or updates an AgentSpec under the given name.
        
        Parameters:
            name (str): Unique identifier for the agent.
            graph (Any): Compiled state graph or callable representing the agent's execution graph.
            description (str): Human-readable description of the agent. If empty, a default description of the form "Agent: <name>" is used.
            capabilities (List[str] | None): List of capability keywords the agent declares; treated as an empty list if None.
        """
        self._agents[name] = AgentSpec(
            name=name,
            graph=graph,
            description=description or f"Agent: {name}",
            capabilities=capabilities or [],
        )
        logger.info(f"Registered agent: {name}")

    def unregister(self, name: str):
        """
        Remove an agent from the pool if it exists.
        
        Parameters:
            name (str): The registered agent's name to remove. If no agent with this name exists, the method does nothing.
        """
        if name in self._agents:
            del self._agents[name]

    def get_agent(self, name: str) -> AgentSpec | None:
        """
        Retrieve a registered agent by name.
        
        Returns:
            AgentSpec: The agent specification for the given name, or `None` if no agent with that name is registered.
        """
        return self._agents.get(name)

    def get_agent_names(self) -> List[str]:
        """Get list of registered agent names."""
        return list(self._agents.keys())

    def get_agents_with_capability(self, capability: str) -> List[AgentSpec]:
        """
        Find agents that declare the given capability.
        
        Parameters:
            capability (str): Capability name to filter agents by.
        
        Returns:
            List[AgentSpec]: Agents whose `capabilities` list includes `capability`.
        """
        return [
            agent for agent in self._agents.values() if capability in agent.capabilities
        ]

    def get_agent_descriptions(self) -> str:
        """
        Produce a formatted list of agent descriptions for use in coordinator prompts.
        
        Each line represents one registered agent in the form:
        "- {name}: {description} [capabilities: {cap1, cap2}]" — agents with no declared capabilities use "general".
        
        Returns:
            A newline-separated string containing one formatted description per agent.
        """
        lines = []
        for agent in self._agents.values():
            caps = ", ".join(agent.capabilities) if agent.capabilities else "general"
            lines.append(f"- {agent.name}: {agent.description} [capabilities: {caps}]")
        return "\n".join(lines)


# =============================================================================
# Coordinator Node
# =============================================================================


def create_coordinator_node(
    tools: ToolRegistry,
    agents: AgentPool,
    model: str = GEMINI_PRO,
):
    """
    Create a coordinator callable that decides whether to delegate to an agent, invoke a tool, or produce a direct answer.
    
    The returned callable examines the current overall state and returns a routing decision dictionary describing the chosen action, the target (agent or tool name), and a brief reason.
    
    Parameters:
        model (str): Identifier of the LLM model used to make routing decisions.
    
    Returns:
        dict: A routing decision with keys:
            - coordinator_decision (str): One of "delegate_agent", "use_tool", or "direct_answer".
            - coordinator_target (str): The chosen agent name or tool name to handle the task.
            - coordinator_reason (str): A short explanation for the decision.
    """

    def coordinator(state: OverallState, config: RunnableConfig) -> Dict[str, Any]:
        """
        Decides how to route the latest user query: delegate to an agent, invoke a tool, or produce a direct answer.
        
        Analyzes the most recent message in `state` and formulates a routing decision by prompting an LLM; the returned mapping contains the chosen action, a target agent or tool name, and a short rationale. If no messages are present, the decision is to finalize immediately. On parsing or invocation failures, falls back to delegating to the "planner" agent.
        
        Returns:
            dict: A dictionary with keys:
                - "coordinator_decision" (str): One of "delegate_agent", "use_tool", or "direct_answer".
                - "coordinator_target" (str): The agent name or tool name selected (defaults to "planner" on fallback).
                - "coordinator_reason" (str): Short explanation for the decision.
        """
        messages = state.get("messages", [])
        if not messages:
            return {"coordinator_decision": "finalize"}

        last_message = messages[-1]
        query = (
            last_message.content
            if hasattr(last_message, "content")
            else str(last_message)
        )

        # Build routing prompt
        tool_list = ", ".join(tools.get_tool_names())
        agent_descriptions = agents.get_agent_descriptions()

        prompt = f"""You are a research coordinator. Analyze the query and decide the best approach.

Query: {query}

Available Tools: {tool_list}
Available Agents:
{agent_descriptions}

Based on the query complexity:
- For simple factual questions: use "quick_search" agent
- For complex research: use "planner" or "deep_researcher" agent
- For specific tool needs: specify the tool name

Respond with JSON:
{{"action": "delegate_agent" | "use_tool" | "direct_answer", "target": "<agent_name or tool_name>", "reason": "<brief reason>"}}
"""

        try:
            # ⚡ Bolt Optimization: Use centralized cached factory
            llm = get_cached_llm(model, 0)
            response = llm.invoke(prompt)
            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Parse decision (simple extraction)
            import json
            import re

            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group())
                return {
                    "coordinator_decision": decision.get("action", "delegate_agent"),
                    "coordinator_target": decision.get("target", "planner"),
                    "coordinator_reason": decision.get("reason", ""),
                }
        except Exception as e:
            logger.error(f"Coordinator error: {e}")

        # Default: use planner agent
        return {
            "coordinator_decision": "delegate_agent",
            "coordinator_target": "planner",
            "coordinator_reason": "Default routing",
        }

    return coordinator


def create_task_router(agents: AgentPool):
    """Create a router function based on coordinator decision."""

    def router(state: OverallState) -> str:
        decision = state.get("coordinator_decision", "delegate_agent")
        target = state.get("coordinator_target", "planner")

        if decision == "direct_answer":
            return "finalize"

        # Map target to node name
        if target in agents.get_agent_names():
            return f"agent_{target}"

        return "agent_planner"  # Default

    return router


# =============================================================================
# Orchestrated Graph Builder
# =============================================================================


def build_orchestrated_graph(
    tools: ToolRegistry | None = None,
    agents: AgentPool | None = None,
    coordinator_model: str = GEMINI_PRO,
    name: str = "orchestrated-agent",
) -> StateGraph:
    """
    Builds a supervisor-style state graph that routes tasks via a coordinator to tools or sub-agents and then finalizes results.
    
    Parameters:
        tools (ToolRegistry | None): Optional registry of available tools; a default ToolRegistry is not created here.
        agents (AgentPool | None): Optional pool of sub-agents; if None, a default AgentPool is instantiated.
        coordinator_model (str): Model identifier used by the coordinator LLM to make routing decisions.
        name (str): Name assigned to the compiled StateGraph.
    
    Returns:
        StateGraph: A compiled StateGraph named `name` that contains nodes for context loading, a coordinator, per-agent nodes (agent_<name>), an optional tools node, and a finalization node. The coordinator routes execution to one of these nodes and the graph ends after finalization.
    """
    if agents is None:
        agents = AgentPool()

    from agent.nodes import denoising_refiner, load_context

    builder = StateGraph(OverallState, config_schema=Configuration)

    # Core nodes
    builder.add_node("load_context", load_context)
    builder.add_node(
        "coordinator", create_coordinator_node(tools, agents, coordinator_model)
    )
    builder.add_node("finalize", denoising_refiner)

    # Add agent nodes (wrap each agent as a node)
    for agent_name in agents.get_agent_names():
        agent_spec = agents.get_agent(agent_name)
        if agent_spec:
            # Create a wrapper that invokes the sub-agent
            def make_agent_node(spec):
                """
                Create an async node function that invokes an agent's compiled graph.
                
                Parameters:
                    spec: An object representing an agent (e.g., AgentSpec) whose `graph` exposes an async `ainvoke(state, config)` method. The `graph` will be invoked when the returned node is called.
                
                Returns:
                    An async callable(state: OverallState, config: RunnableConfig) that invokes `spec.graph.ainvoke(state, config)` and returns the value produced by that invocation.
                """
                async def agent_node(state: OverallState, config: RunnableConfig):
                    result = await spec.graph.ainvoke(state, config)
                    return result

                return agent_node

            builder.add_node(f"agent_{agent_name}", make_agent_node(agent_spec))

    # Add tool node if tools are available
    lc_tools = tools.get_tools()
    if lc_tools:
        builder.add_node("tools", ToolNode(lc_tools))

    # Edges
    builder.add_edge(START, "load_context")
    builder.add_edge("load_context", "coordinator")

    # Conditional routing from coordinator
    route_targets = ["finalize"]
    for agent_name in agents.get_agent_names():
        route_targets.append(f"agent_{agent_name}")
    if lc_tools:
        route_targets.append("tools")

    builder.add_conditional_edges(
        "coordinator",
        create_task_router(agents),
        route_targets,
    )

    # All agent outputs go to finalize
    for agent_name in agents.get_agent_names():
        builder.add_edge(f"agent_{agent_name}", "finalize")

    if lc_tools:
        builder.add_edge("tools", "finalize")

    builder.add_edge("finalize", END)

    return builder.compile(name=name)


# =============================================================================
# Convenience Functions
# =============================================================================


def get_default_registry() -> ToolRegistry:
    """
    Create a ToolRegistry populated with default tools.
    
    Returns:
        tool_registry (ToolRegistry): A new ToolRegistry instance with available default tools registered.
    """
    return ToolRegistry()


def get_default_pool() -> AgentPool:
    """Get an AgentPool with default agents loaded."""
    return AgentPool()
