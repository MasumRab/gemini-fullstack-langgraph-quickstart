"""
Comprehensive unit tests for backend/src/agent/graphs/supervisor.py

Tests cover:
- compress_context node functionality
- State management and merging
- Edge cases and error handling
- Graph compilation and structure
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any
from langchain_core.runnables import RunnableConfig

from unittest.mock import patch
from agent.state import OverallState
from agent.graphs.supervisor import compress_context, graph


# =============================================================================
# Fixtures
# =============================================================================

import dataclasses
from agent.graphs import supervisor

@pytest.fixture(autouse=True)
def disable_compression():
    """Disable compression for deterministic testing."""
    # Since AppConfig is frozen, we must replace the entire config object
    original_config = supervisor.app_config
    new_config = dataclasses.replace(original_config, compression_enabled=False)

    with patch("agent.graphs.supervisor.app_config", new_config):
        yield

@pytest.fixture
def base_supervisor_state() -> Dict[str, Any]:
    """Base state for supervisor tests."""
    return {
        "messages": [],
        "search_query": [],
        "web_research_result": [],
        "validated_web_research_result": [],
        "validation_notes": [],
        "sources_gathered": [],
        "research_loop_count": 0,
        "planning_status": None,
        "planning_feedback": [],
        "planning_steps": None,
        "scoping_status": None,
        "clarification_questions": None,
        "clarification_answers": [],
        "initial_search_query_count": 3,
        "max_research_loops": 2,
        "reasoning_model": "gemini-2.5-flash",
        "todo_list": None,
        "artifacts": None,
    }


@pytest.fixture
def config() -> RunnableConfig:
    """Basic runnable config for tests."""
    return RunnableConfig(
        configurable={
            "thread_id": "test-thread",
            "checkpoint_ns": "",
            "checkpoint_id": "",
        }
    )


# =============================================================================
# Tests for compress_context Node
# =============================================================================

class TestCompressContext:
    """Test suite for compress_context node."""

    @patch("agent.graphs.supervisor.app_config")
    def test_compress_context_merges_new_and_existing_results(self, mock_config, base_supervisor_state, config):
        """Test that compress_context merges new and existing results."""
        # Mock config to ensure compression is disabled for this test case
        # because if enabled, it compresses to 1 result.
        mock_config.compression_enabled = False

        # Setup
        base_supervisor_state["web_research_result"] = [
            "existing result 1",
            "existing result 2",
        ]
        base_supervisor_state["validated_web_research_result"] = [
            "new result 1",
            "new result 2",
        ]

        # Execute
        result = compress_context(base_supervisor_state, config)

        # Assert
        assert "web_research_result" in result
        assert len(result["web_research_result"]) == 4
        assert "existing result 1" in result["web_research_result"]
        assert "existing result 2" in result["web_research_result"]
        assert "new result 1" in result["web_research_result"]
        assert "new result 2" in result["web_research_result"]

    @patch("agent.graphs.supervisor.app_config")
    def test_compress_context_with_empty_validated_results(self, mock_config, base_supervisor_state, config):
        """Test compress_context when no new validated results exist."""
        mock_config.compression_enabled = False
        # Setup
        base_supervisor_state["web_research_result"] = ["existing result"]
        base_supervisor_state["validated_web_research_result"] = []

        # Execute
        result = compress_context(base_supervisor_state, config)

        # Assert
        assert "web_research_result" in result
        assert len(result["web_research_result"]) == 1
        assert result["web_research_result"][0] == "existing result"

    @patch("agent.graphs.supervisor.app_config")
    def test_compress_context_with_empty_existing_results(self, mock_config, base_supervisor_state, config):
        """Test compress_context when no existing results."""
        mock_config.compression_enabled = False
        # Setup
        base_supervisor_state["web_research_result"] = []
        base_supervisor_state["validated_web_research_result"] = [
            "new result 1",
            "new result 2",
        ]

        # Execute
        result = compress_context(base_supervisor_state, config)

        # Assert
        assert "web_research_result" in result
        assert len(result["web_research_result"]) == 2
        assert "new result 1" in result["web_research_result"]
        assert "new result 2" in result["web_research_result"]

    @patch("agent.graphs.supervisor.app_config")
    def test_compress_context_with_both_empty(self, mock_config, base_supervisor_state, config):
        """Test compress_context when both result lists are empty."""
        mock_config.compression_enabled = False
        # Setup
        base_supervisor_state["web_research_result"] = []
        base_supervisor_state["validated_web_research_result"] = []

        # Execute
        result = compress_context(base_supervisor_state, config)

        # Assert
        assert "web_research_result" in result
        assert result["web_research_result"] == []

    @patch("agent.graphs.supervisor.app_config")
    def test_compress_context_with_missing_keys(self, mock_config, config):
        """Test compress_context handles missing state keys gracefully."""
        mock_config.compression_enabled = False
        # Setup - minimal state without the expected keys
        minimal_state = {
            "messages": [],
            "research_loop_count": 0,
        }

        # Execute
        result = compress_context(minimal_state, config)

        # Assert - should handle missing keys with get() defaults
        assert "web_research_result" in result
        assert result["web_research_result"] == []

    @patch("agent.graphs.supervisor.app_config")
    def test_compress_context_preserves_order(self, mock_config, base_supervisor_state, config):
        """Test that compress_context preserves order (existing then new)."""
        mock_config.compression_enabled = False
        # Setup
        base_supervisor_state["web_research_result"] = ["first", "second"]
        base_supervisor_state["validated_web_research_result"] = ["third", "fourth"]

        # Execute
        result = compress_context(base_supervisor_state, config)

        # Assert
        assert result["web_research_result"] == ["first", "second", "third", "fourth"]

    @patch("agent.graphs.supervisor.app_config")
    def test_compress_context_with_large_result_set(self, mock_config, base_supervisor_state, config):
        """Test compress_context handles large numbers of results."""
        mock_config.compression_enabled = False
        # Setup
        base_supervisor_state["web_research_result"] = [f"existing_{i}" for i in range(100)]
        base_supervisor_state["validated_web_research_result"] = [f"new_{i}" for i in range(100)]

        # Execute
        result = compress_context(base_supervisor_state, config)

        # Assert
        assert len(result["web_research_result"]) == 200
        assert "existing_0" in result["web_research_result"]
        assert "new_99" in result["web_research_result"]


class TestSupervisorGraph:
    """Test suite for supervisor graph structure and compilation."""

    def test_supervisor_graph_compiles_successfully(self):
        """Test that supervisor graph compiles without errors."""
        # The graph is compiled at module level
        assert graph is not None
        assert hasattr(graph, 'invoke')
        assert hasattr(graph, 'stream')

    def test_supervisor_graph_has_compress_context_node(self):
        """Test that compress_context node is registered in the graph."""
        # Check that the node exists in the graph
        assert graph is not None
        # The compiled graph should have the node in its structure
        assert "compress_context" in str(graph.get_graph())

    def test_supervisor_graph_name(self):
        """Test that supervisor graph has correct name."""
        assert graph is not None
        assert graph.name == "pro-search-agent-supervisor"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])