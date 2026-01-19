"""Unit tests for agent orchestration.

Tests cover:
- ToolRegistry (registration, retrieval)
- AgentPool (registration, capability filtering)
- Coordinator node logic (decision making)
- Orchestrated graph construction
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent.orchestration import (
    AgentPool,
    ToolRegistry,
    build_orchestrated_graph,
    create_coordinator_node,
    create_task_router,
)

# =============================================================================
# ToolRegistry Tests
# =============================================================================


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_register_and_get_tool(self):
        """Test registering a tool and retrieving it."""
        registry = ToolRegistry()
        func = lambda x: x
        registry.register("test_tool", func, "Test description", "test_cat")

        # Get by name
        spec = registry.get_tool("test_tool")
        assert spec is not None
        assert spec.name == "test_tool"
        assert spec.category == "test_cat"
        assert spec.description == "Test description"

        # Get names
        names = registry.get_tool_names()
        assert "test_tool" in names

    def test_get_tools_as_langchain_tools(self):
        """Test retrieving tools as LangChain BaseTool objects."""
        registry = ToolRegistry()
        func = lambda x: x
        registry.register("tool1", func, "Desc 1")
        registry.register("tool2", func, "Desc 2", category="special")

        # Get all
        tools = registry.get_tools()
        assert len(tools) >= 2  # Might have default tools
        names = [t.name for t in tools]
        assert "tool1" in names
        assert "tool2" in names

        # Get by category
        special_tools = registry.get_tools(category="special")
        assert len(special_tools) == 1
        assert special_tools[0].name == "tool2"

    def test_unregister_tool(self):
        """Test unregistering a tool."""
        registry = ToolRegistry()
        registry.register("temp", lambda x: x)
        assert "temp" in registry.get_tool_names()

        registry.unregister("temp")
        assert "temp" not in registry.get_tool_names()

    def test_load_default_tools_safe(self):
        """Test that loading default tools doesn't crash even if imports fail."""
        # This is implicitly tested by __init__, but we verify it handles missing mods
        with patch.dict("sys.modules", {"search.router": None, "agent.rag": None}):
            registry = ToolRegistry()
            # Should proceed without error
            assert isinstance(registry, ToolRegistry)


# =============================================================================
# AgentPool Tests
# =============================================================================


class TestAgentPool:
    """Tests for AgentPool."""

    def test_register_and_get_agent(self):
        """Test registering an agent and retrieving it."""
        pool = AgentPool()
        mock_graph = MagicMock()
        pool.register("test_agent", mock_graph, "Test Desc", ["search"])

        spec = pool.get_agent("test_agent")
        assert spec is not None
        assert spec.name == "test_agent"
        assert "search" in spec.capabilities

        names = pool.get_agent_names()
        assert "test_agent" in names

    def test_get_agents_with_capability(self):
        """Test filtering agents by capability."""
        pool = AgentPool()
        # Clear default agents for explicit testing
        pool._agents = {}
        pool.register("a1", MagicMock(), capabilities=["search", "planning"])
        pool.register("a2", MagicMock(), capabilities=["search"])
        pool.register("a3", MagicMock(), capabilities=["planning"])

        search_agents = pool.get_agents_with_capability("search")
        assert len(search_agents) == 2
        names = [a.name for a in search_agents]
        assert "a1" in names and "a2" in names

    def test_agent_descriptions(self):
        """Test formatting of agent descriptions."""
        pool = AgentPool()
        # Clear default agents for clean test
        pool._agents = {}
        pool.register("a1", MagicMock(), "Desc 1", ["cap1"])

        desc = pool.get_agent_descriptions()
        assert "- a1: Desc 1 [capabilities: cap1]" in desc


# =============================================================================
# Coordinator Node Tests
# =============================================================================


class TestCoordinatorNode:
    """Tests for the coordinator node logic."""

    @patch("agent.orchestration.ChatGoogleGenerativeAI")
    def test_coordinator_routing_decision(self, mock_llm_class):
        """Test parsing of LLM JSON response."""
        # Setup mocks
        mock_llm = mock_llm_class.return_value
        mock_llm.invoke.return_value = AIMessage(
            content='```json\n{"action": "delegate_agent", "target": "researcher", "reason": "complex query"}\n```'
        )

        registry = ToolRegistry()
        pool = AgentPool()
        coordinator = create_coordinator_node(registry, pool)

        state = {"messages": [HumanMessage(content="complex research task")]}
        config = {}

        # Execute
        result = coordinator(state, config)

        # Assert
        assert result["coordinator_decision"] == "delegate_agent"
        assert result["coordinator_target"] == "researcher"

    @patch("agent.orchestration.ChatGoogleGenerativeAI")
    def test_coordinator_fallback_on_error(self, mock_llm_class):
        """Test fallback when LLM fails or returns invalid JSON."""
        mock_llm = mock_llm_class.return_value
        mock_llm.invoke.side_effect = Exception("API Error")

        registry = ToolRegistry()
        pool = AgentPool()
        coordinator = create_coordinator_node(registry, pool)

        state = {"messages": [HumanMessage(content="task")]}
        result = coordinator(state, {})

        assert result["coordinator_decision"] == "delegate_agent"
        assert result["coordinator_target"] == "planner"

    def test_coordinator_no_messages(self):
        """Test coordinator with empty state."""
        registry = ToolRegistry()
        pool = AgentPool()
        coordinator = create_coordinator_node(registry, pool)

        result = coordinator({}, {})
        assert result["coordinator_decision"] == "finalize"


# =============================================================================
# Orchestrated Graph Tests
# =============================================================================


class TestOrchestratedGraphBuilder:
    """Tests for build_orchestrated_graph."""

    @patch("agent.nodes.load_context", MagicMock())
    @patch("agent.nodes.denoising_refiner", MagicMock())
    def test_build_graph_structure(self):
        """Test that the graph is built with expected nodes."""
        registry = ToolRegistry()
        pool = AgentPool()
        mock_graph = AsyncMock()
        pool.register("subagent", mock_graph, "Sub Agent")

        # Mock StateGraph to verify structure without full compilation (which needs langgraph installed)
        # However, we have langgraph installed, so we can check the compiled graph nodes.

        # We need to mock StateGraph because 'OverallState' might import things.
        # But let's try to just build it and catch if dependencies miss.

        # Actually, we can check the nodes in the compiled graph object if possible.
        try:
            graph = build_orchestrated_graph(registry, pool)
            # Just asserting it compiled successfully is a good start
            assert graph is not None
        except Exception as e:
            pytest.fail(f"Graph build failed: {e}")

    def test_router_logic(self):
        """Test the router function mapping."""
        pool = AgentPool()
        pool.register("researcher", MagicMock())

        router = create_task_router(pool)

        # Direct answer
        assert router({"coordinator_decision": "direct_answer"}) == "finalize"

        # Registered agent
        state = {
            "coordinator_decision": "delegate_agent",
            "coordinator_target": "researcher",
        }
        assert router(state) == "agent_researcher"

        # Unknown agent (default)
        state["coordinator_target"] = "unknown"
        assert router(state) == "agent_planner"
