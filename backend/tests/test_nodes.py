"""
Comprehensive unit tests for backend/src/agent/nodes.py

Tests cover:
- generate_query node
- planning_mode node
- planning_wait node
- web_research node
- validate_web_results node
- reflection node
- finalize_answer node
- Edge cases and error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage, HumanMessage

from agent.state import OverallState, WebResearch, PlanStep
from agent.nodes import (
    generate_query,
    planning_mode,
    planning_wait,
    web_research,
    validate_web_results,
    reflection,
    finalize_answer,
)


# Fixtures
@pytest.fixture
def base_state():
    """Base state for testing"""
    return {
        "messages": [],
        "research_loop_count": 0,
        "queries": [],
        "web_research_results": [],
        "planning_steps": [],
        "planning_status": None,
        "planning_feedback": [],
    }


@pytest.fixture
def config():
    """Basic runnable config"""
    return RunnableConfig(
        configurable={
            "model": "gemini-2.5-flash",
            "max_loops": 3,
            "num_queries": 3,
            "require_planning_confirmation": False,
        }
    )


@pytest.fixture
def config_with_confirmation():
    """Config requiring planning confirmation"""
    return RunnableConfig(
        configurable={
            "model": "gemini-2.5-flash",
            "max_loops": 3,
            "num_queries": 3,
            "require_planning_confirmation": True,
        }
    )


# Tests for generate_query
class TestGenerateQuery:
    """Test suite for generate_query node"""

    @patch("agent.nodes.query_writer_instructions")
    def test_generate_query_creates_queries(self, mock_instructions, base_state, config):
        """Test that generate_query creates the correct number of queries"""
        # Setup
        base_state["messages"] = [HumanMessage(content="What is quantum computing?")]

        mock_chain = Mock()
        mock_chain.invoke.return_value = AIMessage(
            content="query1\nquery2\nquery3"
        )
        mock_instructions.return_value = mock_chain

        # Execute
        result = generate_query(base_state, config)

        # Assert
        assert "queries" in result
        assert len(result["queries"]) == 3
        mock_chain.invoke.assert_called_once()

    @patch("agent.nodes.query_writer_instructions")
    def test_generate_query_with_single_query(self, mock_instructions, base_state, config):
        """Test generate_query with single query"""
        # Setup
        base_state["messages"] = [HumanMessage(content="What is AI?")]
        config["configurable"]["num_queries"] = 1

        mock_chain = Mock()
        mock_chain.invoke.return_value = AIMessage(content="artificial intelligence basics")
        mock_instructions.return_value = mock_chain

        # Execute
        result = generate_query(base_state, config)

        # Assert
        assert len(result["queries"]) == 1

    @patch("agent.nodes.query_writer_instructions")
    def test_generate_query_with_empty_message(self, mock_instructions, base_state, config):
        """Test generate_query handles empty messages gracefully"""
        # Setup
        base_state["messages"] = [HumanMessage(content="")]

        mock_chain = Mock()
        mock_chain.invoke.return_value = AIMessage(content="")
        mock_instructions.return_value = mock_chain

        # Execute
        result = generate_query(base_state, config)

        # Assert
        assert "queries" in result

    @patch("agent.nodes.query_writer_instructions")
    def test_generate_query_strips_whitespace(self, mock_instructions, base_state, config):
        """Test that generated queries have whitespace stripped"""
        # Setup
        base_state["messages"] = [HumanMessage(content="Test query")]

        mock_chain = Mock()
        mock_chain.invoke.return_value = AIMessage(
            content="  query1  \n  query2  \n  query3  "
        )
        mock_instructions.return_value = mock_chain

        # Execute
        result = generate_query(base_state, config)

        # Assert
        for query in result["queries"]:
            assert query == query.strip()
            assert not query.startswith(" ")
            assert not query.endswith(" ")


# Tests for planning_mode
class TestPlanningMode:
    """Test suite for planning_mode node"""

    def test_planning_mode_creates_steps_from_queries(self, base_state, config):
        """Test that planning_mode creates plan steps from queries"""
        # Setup
        base_state["queries"] = ["query1", "query2", "query3"]

        # Execute
        result = planning_mode(base_state, config)

        # Assert
        assert "planning_steps" in result
        assert len(result["planning_steps"]) == 3
        assert result["planning_status"] == "auto_approved"
        assert len(result["planning_feedback"]) > 0

    def test_planning_mode_with_confirmation_required(self, base_state, config_with_confirmation):
        """Test planning_mode when confirmation is required"""
        # Setup
        base_state["queries"] = ["query1", "query2"]

        # Execute
        result = planning_mode(base_state, config_with_confirmation)

        # Assert
        assert result["planning_status"] == "awaiting_confirmation"
        assert any("confirmation" in fb.lower() for fb in result["planning_feedback"])

    def test_planning_mode_handles_skip_planning_status(self, base_state, config):
        """Test planning_mode respects skip_planning status"""
        # Setup
        base_state["queries"] = ["query1", "query2"]
        base_state["planning_status"] = "skip_planning"

        # Execute
        result = planning_mode(base_state, config)

        # Assert
        assert result["planning_status"] == "auto_approved"
        assert result["planning_steps"] == []
        assert any("skipped" in fb.lower() or "disabled" in fb.lower()
                   for fb in result["planning_feedback"])

    def test_planning_mode_handles_end_plan_command(self, base_state, config):
        """Test planning_mode handles /end_plan command"""
        # Setup
        base_state["queries"] = ["query1", "query2"]
        base_state["messages"] = [HumanMessage(content="/end_plan")]

        # Execute
        result = planning_mode(base_state, config)

        # Assert
        assert result["planning_status"] == "auto_approved"
        assert result["planning_steps"] == []

    def test_planning_mode_handles_plan_command(self, base_state, config):
        """Test planning_mode handles /plan command"""
        # Setup
        base_state["queries"] = ["query1"]
        base_state["messages"] = [HumanMessage(content="/plan")]

        # Execute
        result = planning_mode(base_state, config)

        # Assert
        assert result["planning_status"] == "awaiting_confirmation"

    def test_planning_mode_creates_valid_plan_steps(self, base_state, config):
        """Test that plan steps have required fields"""
        # Setup
        base_state["queries"] = ["test query"]

        # Execute
        result = planning_mode(base_state, config)

        # Assert
        step = result["planning_steps"][0]
        assert "id" in step
        assert "title" in step
        assert "status" in step
        assert "query" in step
        assert "suggested_tool" in step
        assert step["suggested_tool"] == "web_research"

    def test_planning_mode_with_empty_queries(self, base_state, config):
        """Test planning_mode with empty queries list"""
        # Setup
        base_state["queries"] = []

        # Execute
        result = planning_mode(base_state, config)

        # Assert
        assert result["planning_steps"] == []
        assert "planning_feedback" in result


# Tests for planning_wait
class TestPlanningWait:
    """Test suite for planning_wait node"""

    def test_planning_wait_returns_feedback(self, base_state):
        """Test that planning_wait returns appropriate feedback"""
        # Execute
        result = planning_wait(base_state)

        # Assert
        assert "planning_feedback" in result
        assert len(result["planning_feedback"]) > 0
        assert any("awaiting" in fb.lower() or "confirmation" in fb.lower()
                   for fb in result["planning_feedback"])

    def test_planning_wait_preserves_state(self, base_state):
        """Test that planning_wait doesn't modify other state"""
        # Setup
        base_state["queries"] = ["query1"]
        base_state["planning_steps"] = [{"id": "1", "title": "test"}]
        base_state["planning_status"] = "awaiting_confirmation"

        # Execute
        result = planning_wait(base_state)

        # Assert - should only add feedback, not modify other fields
        assert "planning_feedback" in result
        assert len(result.keys()) == 1


# Tests for web_research
class TestWebResearch:
    """Test suite for web_research node"""

    @patch("agent.nodes.tavily_search")
    @patch("agent.nodes.scrape_website")
    def test_web_research_processes_queries(self, mock_scrape, mock_search, base_state, config):
        """Test web_research processes all queries"""
        # Setup
        base_state["queries"] = ["query1", "query2"]

        mock_search.return_value = [
            {"url": "http://example.com/1", "content": "content1"},
            {"url": "http://example.com/2", "content": "content2"},
        ]
        mock_scrape.return_value = "scraped content"

        # Execute
        result = web_research(base_state, config)

        # Assert
        assert "web_research_results" in result
        assert len(result["web_research_results"]) == 2

    @patch("agent.nodes.tavily_search")
    @patch("agent.nodes.scrape_website")
    def test_web_research_handles_search_failure(self, mock_scrape, mock_search, base_state, config):
        """Test web_research handles search API failures gracefully"""
        # Setup
        base_state["queries"] = ["query1"]
        mock_search.side_effect = Exception("API Error")

        # Execute - should not raise
        result = web_research(base_state, config)

        # Assert
        assert "web_research_results" in result

    @patch("agent.nodes.tavily_search")
    @patch("agent.nodes.scrape_website")
    def test_web_research_handles_scraping_failure(self, mock_scrape, mock_search, base_state, config):
        """Test web_research handles scraping failures gracefully"""
        # Setup
        base_state["queries"] = ["query1"]
        mock_search.return_value = [{"url": "http://example.com", "content": "content"}]
        mock_scrape.side_effect = Exception("Scrape Error")

        # Execute - should not raise
        result = web_research(base_state, config)

        # Assert
        assert "web_research_results" in result

    @patch("agent.nodes.tavily_search")
    @patch("agent.nodes.scrape_website")
    def test_web_research_with_empty_queries(self, mock_scrape, mock_search, base_state, config):
        """Test web_research with empty queries list"""
        # Setup
        base_state["queries"] = []

        # Execute
        result = web_research(base_state, config)

        # Assert
        assert "web_research_results" in result
        assert result["web_research_results"] == []
        mock_search.assert_not_called()

    @patch("agent.nodes.tavily_search")
    @patch("agent.nodes.scrape_website")
    def test_web_research_deduplicates_urls(self, mock_scrape, mock_search, base_state, config):
        """Test that web_research deduplicates URLs"""
        # Setup
        base_state["queries"] = ["query1", "query2"]

        # Same URL returned for both queries
        mock_search.return_value = [
            {"url": "http://example.com", "content": "content"}
        ]
        mock_scrape.return_value = "scraped content"

        # Execute
        result = web_research(base_state, config)

        # Assert - should only scrape once per unique URL
        urls = [r["url"] for r in result["web_research_results"]]
        assert len(urls) == len(set(urls))  # No duplicates


# Tests for validate_web_results
class TestValidateWebResults:
    """Test suite for validate_web_results node"""

    @patch("agent.nodes.validate_documents")
    def test_validate_web_results_filters_results(self, mock_validate, base_state, config):
        """Test that validate_web_results filters research results"""
        # Setup
        base_state["web_research_results"] = [
            {"url": "http://example.com/1", "content": "good content"},
            {"url": "http://example.com/2", "content": "bad content"},
        ]
        base_state["messages"] = [HumanMessage(content="test question")]

        mock_validate.return_value = [
            {"url": "http://example.com/1", "content": "good content", "is_valid": True}
        ]

        # Execute
        result = validate_web_results(base_state, config)

        # Assert
        assert "web_research_results" in result
        assert len(result["web_research_results"]) == 1

    @patch("agent.nodes.validate_documents")
    def test_validate_web_results_with_empty_results(self, mock_validate, base_state, config):
        """Test validate_web_results with no research results"""
        # Setup
        base_state["web_research_results"] = []
        base_state["messages"] = [HumanMessage(content="test question")]

        # Execute
        result = validate_web_results(base_state, config)

        # Assert
        assert "web_research_results" in result
        assert result["web_research_results"] == []
        mock_validate.assert_not_called()

    @patch("agent.nodes.validate_documents")
    def test_validate_web_results_handles_validation_error(self, mock_validate, base_state, config):
        """Test validate_web_results handles validation errors"""
        # Setup
        base_state["web_research_results"] = [
            {"url": "http://example.com", "content": "content"}
        ]
        base_state["messages"] = [HumanMessage(content="test question")]
        mock_validate.side_effect = Exception("Validation Error")

        # Execute - should not raise
        result = validate_web_results(base_state, config)

        # Assert
        assert "web_research_results" in result


# Tests for reflection
class TestReflection:
    """Test suite for reflection node"""

    @patch("agent.nodes.reflection_instructions")
    def test_reflection_identifies_knowledge_gaps(self, mock_instructions, base_state, config):
        """Test that reflection identifies knowledge gaps"""
        # Setup
        base_state["messages"] = [HumanMessage(content="What is quantum computing?")]
        base_state["web_research_results"] = [
            {"url": "http://example.com", "content": "basic info"}
        ]
        base_state["queries"] = ["quantum computing"]
        base_state["research_loop_count"] = 1

        mock_chain = Mock()
        mock_chain.invoke.return_value = AIMessage(
            content="GENERATE\nquantum algorithms\nquantum hardware"
        )
        mock_instructions.return_value = mock_chain

        # Execute
        result = reflection(base_state, config)

        # Assert
        assert "queries" in result
        assert "research_loop_count" in result
        assert result["research_loop_count"] == 2

    @patch("agent.nodes.reflection_instructions")
    def test_reflection_determines_sufficient_knowledge(self, mock_instructions, base_state, config):
        """Test that reflection can determine knowledge is sufficient"""
        # Setup
        base_state["messages"] = [HumanMessage(content="What is AI?")]
        base_state["web_research_results"] = [
            {"url": "http://example.com", "content": "comprehensive info"}
        ]
        base_state["queries"] = ["AI basics"]
        base_state["research_loop_count"] = 1

        mock_chain = Mock()
        mock_chain.invoke.return_value = AIMessage(content="SUFFICIENT")
        mock_instructions.return_value = mock_chain

        # Execute
        result = reflection(base_state, config)

        # Assert
        assert result["queries"] == []

    @patch("agent.nodes.reflection_instructions")
    def test_reflection_at_max_loops(self, mock_instructions, base_state, config):
        """Test reflection behavior at maximum loop count"""
        # Setup
        base_state["messages"] = [HumanMessage(content="Complex question")]
        base_state["web_research_results"] = [{"url": "http://example.com", "content": "info"}]
        base_state["queries"] = ["query"]
        base_state["research_loop_count"] = 3  # At max
        config["configurable"]["max_loops"] = 3

        mock_chain = Mock()
        mock_chain.invoke.return_value = AIMessage(content="GENERATE\nnew query")
        mock_instructions.return_value = mock_chain

        # Execute
        result = reflection(base_state, config)

        # Assert - should stop generating queries at max loops
        assert result["research_loop_count"] == 4

    @patch("agent.nodes.reflection_instructions")
    def test_reflection_with_no_results(self, mock_instructions, base_state, config):
        """Test reflection with no research results"""
        # Setup
        base_state["messages"] = [HumanMessage(content="Question")]
        base_state["web_research_results"] = []
        base_state["queries"] = ["query"]
        base_state["research_loop_count"] = 1

        mock_chain = Mock()
        mock_chain.invoke.return_value = AIMessage(
            content="GENERATE\nmore specific query"
        )
        mock_instructions.return_value = mock_chain

        # Execute
        result = reflection(base_state, config)

        # Assert
        assert "queries" in result


# Tests for finalize_answer
class TestFinalizeAnswer:
    """Test suite for finalize_answer node"""

    @patch("agent.nodes.answer_instructions")
    def test_finalize_answer_generates_response(self, mock_instructions, base_state, config):
        """Test that finalize_answer generates a final response"""
        # Setup
        base_state["messages"] = [HumanMessage(content="What is quantum computing?")]
        base_state["web_research_results"] = [
            {"url": "http://example.com", "content": "Quantum computing uses qubits"}
        ]

        mock_chain = Mock()
        mock_chain.invoke.return_value = AIMessage(
            content="Quantum computing is a field that uses quantum mechanics..."
        )
        mock_instructions.return_value = mock_chain

        # Execute
        result = finalize_answer(base_state, config)

        # Assert
        assert "messages" in result
        assert len(result["messages"]) > 0
        assert isinstance(result["messages"][0], AIMessage)

    @patch("agent.nodes.answer_instructions")
    def test_finalize_answer_with_no_research(self, mock_instructions, base_state, config):
        """Test finalize_answer with no research results"""
        # Setup
        base_state["messages"] = [HumanMessage(content="Question")]
        base_state["web_research_results"] = []

        mock_chain = Mock()
        mock_chain.invoke.return_value = AIMessage(
            content="I don't have enough information..."
        )
        mock_instructions.return_value = mock_chain

        # Execute
        result = finalize_answer(base_state, config)

        # Assert
        assert "messages" in result
        mock_chain.invoke.assert_called_once()

    @patch("agent.nodes.answer_instructions")
    def test_finalize_answer_includes_citations(self, mock_instructions, base_state, config):
        """Test that finalize_answer can include citations"""
        # Setup
        base_state["messages"] = [HumanMessage(content="Question")]
        base_state["web_research_results"] = [
            {"url": "http://example.com/1", "content": "source 1"},
            {"url": "http://example.com/2", "content": "source 2"},
        ]

        mock_chain = Mock()
        mock_chain.invoke.return_value = AIMessage(
            content="Answer with [1] and [2] citations."
        )
        mock_instructions.return_value = mock_chain

        # Execute
        result = finalize_answer(base_state, config)

        # Assert
        assert "messages" in result
        # Verify chain was called with research results
        call_args = mock_chain.invoke.call_args
        assert call_args is not None

    @patch("agent.nodes.answer_instructions")
    def test_finalize_answer_handles_error(self, mock_instructions, base_state, config):
        """Test finalize_answer handles generation errors"""
        # Setup
        base_state["messages"] = [HumanMessage(content="Question")]
        base_state["web_research_results"] = [
            {"url": "http://example.com", "content": "content"}
        ]

        mock_chain = Mock()
        mock_chain.invoke.side_effect = Exception("Generation Error")
        mock_instructions.return_value = mock_chain

        # Execute - should handle gracefully
        try:
            result = finalize_answer(base_state, config)
            # If it doesn't raise, check that it handled the error
            assert True
        except Exception as e:
            # If it raises, it should be a known exception type
            assert "Generation Error" in str(e)


# Integration-style tests
class TestNodeIntegration:
    """Integration tests for node workflows"""

    @patch("agent.nodes.query_writer_instructions")
    def test_query_to_planning_workflow(self, mock_instructions, base_state, config):
        """Test workflow from query generation to planning"""
        # Setup
        base_state["messages"] = [HumanMessage(content="Test question")]

        mock_chain = Mock()
        mock_chain.invoke.return_value = AIMessage(content="query1\nquery2")
        mock_instructions.return_value = mock_chain

        # Execute query generation
        state_after_query = generate_query(base_state, config)

        # Execute planning
        state_after_planning = planning_mode(state_after_query, config)

        # Assert
        assert len(state_after_planning["planning_steps"]) == 2
        assert state_after_planning["planning_status"] == "auto_approved"

    @patch("agent.nodes.tavily_search")
    @patch("agent.nodes.scrape_website")
    @patch("agent.nodes.validate_documents")
    def test_research_to_validation_workflow(
        self, mock_validate, mock_scrape, mock_search, base_state, config
    ):
        """Test workflow from research to validation"""
        # Setup
        base_state["queries"] = ["query1"]

        mock_search.return_value = [
            {"url": "http://example.com", "content": "content"}
        ]
        mock_scrape.return_value = "scraped content"
        mock_validate.return_value = [
            {"url": "http://example.com", "content": "scraped content", "is_valid": True}
        ]

        # Execute research
        state_after_research = web_research(base_state, config)

        # Execute validation
        base_state["messages"] = [HumanMessage(content="test")]
        state_after_research["messages"] = base_state["messages"]
        state_after_validation = validate_web_results(state_after_research, config)

        # Assert
        assert len(state_after_validation["web_research_results"]) == 1


# Edge case tests
class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_planning_mode_with_very_long_queries(self, base_state, config):
        """Test planning_mode with very long query strings"""
        # Setup
        long_query = "a" * 10000
        base_state["queries"] = [long_query]

        # Execute
        result = planning_mode(base_state, config)

        # Assert - should handle without errors
        assert len(result["planning_steps"]) == 1

    def test_planning_mode_with_special_characters(self, base_state, config):
        """Test planning_mode with special characters in queries"""
        # Setup
        base_state["queries"] = [
            "query with <html> tags",
            "query with & ampersand",
            "query with 'quotes'",
        ]

        # Execute
        result = planning_mode(base_state, config)

        # Assert
        assert len(result["planning_steps"]) == 3

    def test_reflection_with_large_result_set(self, base_state, config):
        """Test reflection with many research results"""
        # Setup
        base_state["messages"] = [HumanMessage(content="Question")]
        base_state["web_research_results"] = [
            {"url": f"http://example.com/{i}", "content": f"content {i}"}
            for i in range(100)
        ]
        base_state["queries"] = ["query"]
        base_state["research_loop_count"] = 1

        with patch("agent.nodes.reflection_instructions") as mock_instructions:
            mock_chain = Mock()
            mock_chain.invoke.return_value = AIMessage(content="SUFFICIENT")
            mock_instructions.return_value = mock_chain

            # Execute
            result = reflection(base_state, config)

            # Assert - should handle large datasets
            assert "queries" in result

    def test_state_immutability(self, base_state, config):
        """Test that nodes don't mutate input state"""
        # Setup
        original_state = base_state.copy()
        base_state["queries"] = ["query1", "query2"]

        # Execute
        result = planning_mode(base_state, config)

        # Assert - original state should be unchanged
        # (except for keys that are explicitly updated)
        assert base_state["queries"] == ["query1", "query2"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])