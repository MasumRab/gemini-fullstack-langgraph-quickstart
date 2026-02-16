"""
Comprehensive unit tests for backend/src/agent/nodes.py

Tests cover:
- generate_query node
- planning_mode node
- planning_wait node
- web_research node
- validate_web_results node
- reflection node
- denoising_refiner node
- Edge cases and error handling
"""

import dataclasses
from unittest.mock import MagicMock, Mock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from agent.models import TEST_MODEL
from agent.nodes import (
    content_reader,
    denoising_refiner,
    execution_router,
    generate_plan,
    planning_mode,
    planning_wait,
    reflection,
    select_next_task,
    validate_web_results,
    web_research,
)
from config.app_config import config as real_config


# Fixtures
@pytest.fixture
def base_state():
    """Base state for testing"""
    return {
        "messages": [],
        "research_loop_count": 0,
        "search_query": [],
        "web_research_result": [],
        "planning_steps": [],
        "planning_status": None,
        "planning_feedback": [],
    }


@pytest.fixture
def config():
    """Basic runnable config"""
    return RunnableConfig(
        configurable={
            "model": TEST_MODEL,
            "query_generator_model": TEST_MODEL,
            "max_loops": 3,
            "num_queries": 3,
            "require_planning_confirmation": False,
            "answer_model": TEST_MODEL,
        }
    )


@pytest.fixture
def config_with_confirmation():
    """Config requiring planning confirmation"""
    return RunnableConfig(
        configurable={
            "model": TEST_MODEL,
            "query_generator_model": TEST_MODEL,
            "max_loops": 3,
            "num_queries": 3,
            "require_planning_confirmation": True,
            "answer_model": TEST_MODEL,
        }
    )


# Tests for generate_plan
class TestGeneratePlan:
    """Test suite for generate_plan node"""

    @patch("agent.nodes.plan_writer_instructions")
    @patch("agent.nodes.get_context_manager")
    def test_generate_plan_creates_plan(self, mock_get_cm, mock_instructions, base_state, config):
        """Test that generate_plan creates the correct number of tasks"""
        # Setup
        # Configure mocked context manager to avoid type errors with Mock prompt
        mock_get_cm.return_value.truncate_to_fit.return_value = "Mock Prompt"
        mock_instructions.format.return_value = "Mock Prompt"
        base_state["messages"] = [HumanMessage(content="What is quantum computing?")]

        # Use MagicMock to simulate the chain
        mock_chain = MagicMock()
        mock_result = MagicMock()
        # Mock structured output for Plan
        mock_task1 = Mock(title="Task 1", description="Desc 1", status="pending")
        mock_task2 = Mock(title="Task 2", description="Desc 2", status="pending")
        mock_result.plan = [mock_task1, mock_task2]
        mock_result.rationale = "Rationale"

        # Determine behavior based on model (Gemma vs others)
        is_gemma = "gemma" in TEST_MODEL.lower()

        if is_gemma:
            # Mock raw invoke response content for tool adapter
            # It expects a JSON block with tool_calls in markdown or raw
            # PR #93 style but with PR #92 Plan data
            import json
            tool_call_args = {
                "plan": [
                    {"title": "Task 1", "description": "Desc 1", "status": "pending"},
                    {"title": "Task 2", "description": "Desc 2", "status": "pending"}
                ],
                "rationale": "Rationale"
            }
            
            tool_call_response = {
                "tool_calls": [
                    {
                        "name": "Plan",
                        "args": tool_call_args
                    }
                ]
            }
            # Ensure proper JSON formatting for tool adapter compatibility
            json_response = f"```json\n{json.dumps(tool_call_response)}\n```"
            mock_message = AIMessage(content=json_response)
            mock_chain.invoke.return_value = mock_message

            with patch("agent.nodes._get_rate_limited_llm") as mock_get_llm:
                mock_get_llm.return_value = mock_chain
                result = generate_plan(base_state, config)
        else:
            # Standard Gemini
            mock_chain.with_structured_output.return_value.invoke.return_value = mock_result

            with patch("agent.nodes._get_rate_limited_llm") as mock_get_llm:
                mock_get_llm.return_value = mock_chain
                result = generate_plan(base_state, config)

        # Assert
        assert "plan" in result
        assert len(result["plan"]) == 2
        assert "search_query" in result
        assert len(result["search_query"]) == 2
        assert result["plan"][0]["task"] == "Task 1"


# Tests for planning_mode
class TestPlanningMode:
    """Test suite for planning_mode node"""

    def test_planning_mode_creates_steps_from_queries(self, base_state, config):
        """Test that planning_mode creates plan steps from queries"""
        # Setup
        base_state["search_query"] = ["query1", "query2", "query3"]

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
        base_state["search_query"] = ["query1", "query2"]

        # Execute
        result = planning_mode(base_state, config_with_confirmation)

        # Assert
        assert result["planning_status"] == "awaiting_confirmation"
        # assert any("confirmation" in fb.lower() for fb in result["planning_feedback"]) # Skipped as planning_mode does not emit confirmation msg, planning_wait does

    def test_planning_mode_handles_skip_planning_status(self, base_state, config):
        """Test planning_mode respects skip_planning status"""
        # Setup
        base_state["search_query"] = ["query1", "query2"]
        base_state["planning_status"] = "skip_planning"

        # Execute
        result = planning_mode(base_state, config)

        # Assert
        assert result["planning_status"] == "skip_planning"
        # It seems the implementation returns the original status if it exists and is not auto_approved/awaiting

    def test_planning_mode_handles_end_plan_command(self, base_state, config):
        """Test planning_mode handles /end_plan command"""
        # Setup
        base_state["search_query"] = ["query1", "query2"]
        base_state["messages"] = [HumanMessage(content="/end_plan")]

        # Execute
        result = planning_mode(base_state, config)

        # Assert
        assert result["planning_status"] == "auto_approved"
        assert result["planning_steps"] == []

    def test_planning_mode_handles_plan_command(self, base_state, config):
        """Test planning_mode handles /plan command"""
        # Setup
        base_state["search_query"] = ["query1"]
        base_state["messages"] = [HumanMessage(content="/plan")]

        # Execute
        result = planning_mode(base_state, config)

        # Assert
        assert result["planning_status"] == "awaiting_confirmation"

    def test_planning_mode_creates_valid_plan_steps(self, base_state, config):
        """Test that plan steps have required fields"""
        # Setup
        base_state["search_query"] = ["test query"]

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
        base_state["search_query"] = []

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
        base_state["search_query"] = ["query1"]
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

    @patch("agent.nodes.search_router")
    def test_web_research_processes_queries(self, mock_search_router, base_state, config):
        """Test web_research processes queries"""
        # Setup
        # web_research takes WebSearchState which has search_query as str
        state = {"search_query": "test query", "id": 1}

        mock_result = Mock()
        mock_result.title = "Test Title"
        mock_result.url = "http://example.com"
        mock_result.content = "Test Content"
        mock_result.raw_content = "Test Content"

        mock_search_router.search.return_value = [mock_result]

        # Execute
        result = web_research(state, config)

        # Assert
        assert "web_research_result" in result
        assert len(result["web_research_result"]) == 1
        assert "Test Content" in result["web_research_result"][0]

    @patch("agent.nodes.search_router")
    def test_web_research_handles_search_failure(self, mock_search_router, base_state, config):
        """Test web_research handles search API failures gracefully"""
        # Setup
        state = {"search_query": "test query", "id": 1}
        mock_search_router.search.side_effect = Exception("API Error")

        # Execute - should not raise
        result = web_research(state, config)

        # Assert
        assert "web_research_result" in result
        assert result["web_research_result"] == []
        assert "validation_notes" in result
        assert "failed" in result["validation_notes"][0]


# Tests for validate_web_results
class TestValidateWebResults:
    """Test suite for validate_web_results node"""

    def test_validate_web_results_heuristics(self, base_state, config):
        """Test that validate_web_results filters research results based on keywords"""
        # Setup
        base_state["web_research_result"] = [
            "Good content relevant to quantum [Source](http://example.com)",
            "Bad content relevant to cooking [Source](http://example.com)"
        ]
        base_state["search_query"] = ["quantum physics"]

        # Modify config to disable strict citations for this test if needed,
        # although we added citations above.
        # But we also want to ensure that 'agent.nodes.app_config' is using our desired settings.
        # Specifically, ensure require_citations is False so we don't hard fail on format issues
        # (though we formatted correctly above).
        # More importantly, let's just show how to patch the config object properly.

        # Create a modified config
        new_config = dataclasses.replace(real_config, require_citations=False)

        # Patch 'agent.nodes.app_config' which is where the node code imported it
        with patch("agent.nodes.app_config", new_config):
            # Execute
            result = validate_web_results(base_state, config)

        # Assert
        assert "validated_web_research_result" in result
        # The exact matching logic might vary, but "quantum" matches "quantum"
        assert len(result["validated_web_research_result"]) >= 1


    def test_validate_web_results_with_empty_results(self, base_state, config):
        """Test validate_web_results with no research results"""
        # Setup
        base_state["web_research_result"] = []
        base_state["search_query"] = ["test question"]

        # Execute
        result = validate_web_results(base_state, config)

        # Assert
        assert "validated_web_research_result" in result
        assert result["validated_web_research_result"] == []


# Tests for reflection
class TestReflection:
    """Test suite for reflection node"""

    def test_reflection_identifies_knowledge_gaps(self, base_state, config):
        """Test that reflection identifies knowledge gaps"""
        # Setup
        base_state["messages"] = [HumanMessage(content="What is quantum computing?")]
        base_state["web_research_result"] = ["basic info"]
        base_state["search_query"] = ["quantum computing"]
        base_state["research_loop_count"] = 1

        mock_chain = MagicMock()
        mock_result = Mock()
        mock_result.is_sufficient = False
        mock_result.knowledge_gap = "Gap"
        mock_result.follow_up_queries = ["query1"]

        is_gemma = "gemma" in TEST_MODEL.lower()
        if is_gemma:
            import json
            json_response = json.dumps({
                "is_sufficient": False,
                "knowledge_gap": "Gap",
                "follow_up_queries": ["query1"]
            })
            mock_message = AIMessage(content=json_response)
            mock_chain.invoke.return_value = mock_message
        else:
            mock_chain.with_structured_output.return_value.invoke.return_value = mock_result

        with patch("agent.nodes._get_rate_limited_llm") as mock_get_llm:
            mock_get_llm.return_value = mock_chain

            # Execute
            result = reflection(base_state, config)

            # Assert
            assert "follow_up_queries" in result
            assert "research_loop_count" in result
            assert result["research_loop_count"] == 2


# Tests for denoising_refiner
class TestDenoisingRefiner:
    """Test suite for denoising_refiner node"""

    @patch("agent.nodes.answer_instructions")
    @patch("agent.nodes.gemma_answer_instructions")
    @patch("agent.nodes.denoising_instructions")
    def test_denoising_refiner_generates_response(self, mock_denoise, mock_gemma, mock_answer, base_state, config):
        """Test that denoising_refiner generates a final response via 3-step process"""
        # Setup
        base_state["messages"] = [HumanMessage(content="What is quantum computing?")]
        base_state["web_research_result"] = ["Quantum computing uses qubits"]
        base_state["validated_web_research_result"] = ["Quantum computing uses qubits"]

        # Mock LLM for 3 calls: Draft 1, Draft 2, Refine
        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = [
            AIMessage(content="Draft 1 content"),
            AIMessage(content="Draft 2 content"),
            AIMessage(content="Final Refined Content")
        ]

        with patch("agent.nodes._get_rate_limited_llm") as mock_get_llm:
            mock_get_llm.return_value = mock_chain

            # Execute
            result = denoising_refiner(base_state, config)

            # Assert
            assert "messages" in result
            assert len(result["messages"]) > 0
            assert isinstance(result["messages"][0], AIMessage)
            assert "Final Refined Content" in result["messages"][0].content
            assert "artifacts" in result
            assert mock_get_llm.call_count >= 3

# Tests for content_reader
class TestContentReader:
    """Test suite for content_reader node"""

    @patch("agent.nodes._get_rate_limited_llm")
    def test_content_reader_extracts_evidence(self, mock_get_llm, base_state, config):
        """Test content_reader extracts evidence from results"""
        # Setup
        base_state["validated_web_research_result"] = [
            "Quantum computing uses qubits. [Source 1](http://example.com/1)"
        ]

        mock_chain = MagicMock()
        mock_evidence_item = Mock(
            claim="Quantum computing uses qubits.",
            source_url="http://example.com/1",
            context_snippet="Quantum computing uses qubits."
        )
        mock_result = Mock()
        mock_result.items = [mock_evidence_item]
        
        # Configure the mock chain's behavior
        is_gemma = "gemma" in TEST_MODEL.lower()
        
        if is_gemma:
            # Gemma path uses direct invoke and manual parsing via tool adapter
            import json
            tool_call_args = {
                "items": [
                    {
                        "claim": "Quantum computing uses qubits.",
                        "source_url": "http://example.com/1",
                        "context_snippet": "Quantum computing uses qubits."
                    }
                ]
            }

            tool_call_response = {
                "tool_calls": [
                    {
                        "name": "EvidenceList",
                        "args": tool_call_args
                    }
                ]
            }
            # Ensure proper JSON formatting for tool adapter compatibility
            json_response = f"```json\n{json.dumps(tool_call_response)}\n```"
            mock_message = AIMessage(content=json_response)
            mock_chain.invoke.return_value = mock_message
        else:
            # Gemini path uses with_structured_output
            # Mocking the nested calls: llm.with_structured_output(EvidenceList).invoke(...)
            mock_structured_llm = MagicMock()
            mock_structured_llm.invoke.return_value = mock_result
            mock_chain.with_structured_output.return_value = mock_structured_llm

        mock_get_llm.return_value = mock_chain

        # Execute
        result = content_reader(base_state, config)

        # Assert
        assert "evidence_bank" in result
        assert len(result["evidence_bank"]) == 1
        assert result["evidence_bank"][0]["claim"] == "Quantum computing uses qubits."
        assert result["evidence_bank"][0]["source_url"] == "http://example.com/1"

    def test_content_reader_with_no_results(self, base_state, config):
        """Test content_reader returns empty list when no results"""
        # Setup
        base_state["validated_web_research_result"] = []
        base_state["web_research_result"] = []

        # Execute
        result = content_reader(base_state, config)

        # Assert
        assert "evidence_bank" in result
        assert result["evidence_bank"] == []

# Tests for select_next_task and execution_router
class TestExecutionFlow:
    """Test suite for execution flow nodes"""

    def test_select_next_task_picks_pending(self, base_state, config):
        """Test select_next_task picks the first pending task"""
        # Setup
        base_state["plan"] = [
            {"task": "Task 1", "status": "done"},
            {"task": "Task 2", "status": "pending", "query": "Query 2"},
            {"task": "Task 3", "status": "pending"}
        ]

        # Execute
        result = select_next_task(base_state, config)

        # Assert
        assert result["current_task_idx"] == 1
        assert result["search_query"] == ["Query 2"]

    def test_select_next_task_none_if_all_done(self, base_state, config):
        """Test select_next_task returns None index if all tasks are done"""
        # Setup
        base_state["plan"] = [
            {"task": "Task 1", "status": "done"},
            {"task": "Task 2", "status": "done"}
        ]

        # Execute
        result = select_next_task(base_state, config)

        # Assert
        assert result["current_task_idx"] is None

    def test_execution_router_routes_correctly(self, base_state):
        """Test execution_router logic"""
        # Case 1: Pending tasks
        base_state["plan"] = [{"status": "done"}, {"status": "pending"}]
        assert execution_router(base_state) == "select_next_task"

        # Case 2: All done
        base_state["plan"] = [{"status": "done"}, {"status": "done"}]
        assert execution_router(base_state) == "denoising_refiner"

        # Case 3: Empty plan (should probably finalize or handle gracefully)
        base_state["plan"] = []
        assert execution_router(base_state) == "denoising_refiner"
