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

import os
from typing import Dict, List, Any, Callable, Optional, Union
from dataclasses import dataclass, field
import logging

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, StructuredTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from agent.state import OverallState
from agent.configuration import Configuration
from agent.models import GEMINI_PRO

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
        """Load default tools from the project."""
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
            pass

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
            pass

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
            pass

    def register(
        self,
        name: str,
        func: Callable,
        description: str = "",
        category: str = "general",
        requires_confirmation: bool = False,
    ):
        """Register a tool."""
        self._tools[name] = ToolSpec(
            name=name,
            func=func,
            description=description or f"Tool: {name}",
            category=category,
            requires_confirmation=requires_confirmation,
        )
        logger.info(f"Registered tool: {name} [{category}]")

    def unregister(self, name: str):
        """Remove a tool."""
        if name in self._tools:
            del self._tools[name]

    def get_tools(self, category: Optional[str] = None) -> List[BaseTool]:
        """Get registered tools as LangChain tools."""
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
        """Get list of registered tool names."""
        return list(self._tools.keys())

    def get_tool(self, name: str) -> Optional[ToolSpec]:
        """Get a specific tool spec."""
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
        """Load default agents from the project."""
        try:
            from agent.graphs.upstream import graph as upstream
            self.register(
                "quick_search",
                upstream,
                description="Fast, minimal search agent",
                capabilities=["search", "quick_answer"],
            )
        except ImportError:
            pass

        try:
            from agent.graphs.planning import graph as planning
            self.register(
                "planner",
                planning,
                description="Research agent with planning and reflection",
                capabilities=["planning", "search", "reflection", "synthesis"],
            )
        except ImportError:
            pass

        try:
            from agent.graph import graph as enriched
            self.register(
                "deep_researcher",
                enriched,
                description="Full-featured research with KG and compression",
                capabilities=["planning", "search", "kg", "compression", "synthesis"],
            )
        except ImportError:
            pass

    def register(
        self,
        name: str,
        graph: Any,
        description: str = "",
        capabilities: List[str] = None,
    ):
        """Register a sub-agent."""
        self._agents[name] = AgentSpec(
            name=name,
            graph=graph,
            description=description or f"Agent: {name}",
            capabilities=capabilities or [],
        )
        logger.info(f"Registered agent: {name}")

    def unregister(self, name: str):
        """Remove an agent."""
        if name in self._agents:
            del self._agents[name]

    def get_agent(self, name: str) -> Optional[AgentSpec]:
        """Get a specific agent."""
        return self._agents.get(name)

    def get_agent_names(self) -> List[str]:
        """Get list of registered agent names."""
        return list(self._agents.keys())

    def get_agents_with_capability(self, capability: str) -> List[AgentSpec]:
        """Get agents that have a specific capability."""
        return [
            agent for agent in self._agents.values()
            if capability in agent.capabilities
        ]

    def get_agent_descriptions(self) -> str:
        """Get formatted descriptions for coordinator prompt."""
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
    """Create a coordinator node that routes to tools or agents.

    The coordinator:
    1. Analyzes the task
    2. Decides which tool or agent to invoke
    3. Returns the routing decision
    """

    def coordinator(state: OverallState, config: RunnableConfig) -> Dict[str, Any]:
        """Coordinator node that allocates tasks."""
        messages = state.get("messages", [])
        if not messages:
            return {"coordinator_decision": "finalize"}

        last_message = messages[-1]
        query = last_message.content if hasattr(last_message, "content") else str(last_message)

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
            llm = ChatGoogleGenerativeAI(
                model=model,
                temperature=0,
                api_key=os.getenv("GEMINI_API_KEY"),
            )
            response = llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            # Parse decision (simple extraction)
            import json
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
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
    tools: Optional[ToolRegistry] = None,
    agents: Optional[AgentPool] = None,
    coordinator_model: str = GEMINI_PRO,
    name: str = "orchestrated-agent",
) -> StateGraph:
    """Build a graph with coordinator-based orchestration.

    This creates a supervisor-style graph where:
    1. Coordinator analyzes the query
    2. Routes to appropriate sub-agent or tool
    3. Collects and synthesizes results

    Args:
        tools: ToolRegistry with available tools
        agents: AgentPool with available sub-agents
        coordinator_model: Model for the coordinator LLM
        name: Name for the compiled graph

    Returns:
        Compiled StateGraph with orchestration
    """
    if agents is None:
        agents = AgentPool()

    from agent.nodes import load_context, denoising_refiner

    builder = StateGraph(OverallState, config_schema=Configuration)

    # Core nodes
    builder.add_node("load_context", load_context)
    builder.add_node("coordinator", create_coordinator_node(tools, agents, coordinator_model))
    builder.add_node("finalize", denoising_refiner)

    # Add agent nodes (wrap each agent as a node)
    for agent_name in agents.get_agent_names():
        agent_spec = agents.get_agent(agent_name)
        if agent_spec:
            # Create a wrapper that invokes the sub-agent
            def make_agent_node(spec):
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
    """Get a ToolRegistry with default tools loaded."""
    return ToolRegistry()


def get_default_pool() -> AgentPool:
    """Get an AgentPool with default agents loaded."""
    return AgentPool()

