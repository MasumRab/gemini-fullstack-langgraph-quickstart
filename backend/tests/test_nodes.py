import pathlib
import sys
from unittest.mock import Mock, patch, MagicMock
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from agent.nodes import (
    generate_query,
    continue_to_web_research,
    web_research,
    planning_mode,
    planning_wait,
    planning_router,
    _handle_end_plan,
    _handle_confirm_plan,
    _handle_start_plan,
    _flatten_queries,
    _keywords_from_queries,
    validate_web_results,
    reflection,
    evaluate_research,
    finalize_answer,
)


# Helper function to create minimal state
def make_state(**overrides):
    state = {
        "messages": [{"content": "User: research solar energy"}],
        "search_query": ["solar energy market outlook"],
        "web_research_result": [],
        "validated_web_research_result": [],
        "validation_notes": [],
        "sources_gathered": [],
        "planning_steps": None,
        "planning_status": None,
        "planning_feedback": [],
        "initial_search_query_count": 1,
        "max_research_loops": 1,
        "research_loop_count": 0,
        "reasoning_model": "gemini-2.0-flash",
    }
    state.update(overrides)
    return state


def make_config(**overrides):
    config = {
        "configurable": {
            "query_generator_model": "gemini-2.0-flash",
            "reflection_model": "gemini-2.5-flash",
            "answer_model": "gemini-2.5-pro",
            "number_of_initial_queries": 1,
            "max_research_loops": 1,
            "require_planning_confirmation": False,
        }
    }
    if overrides:
        config["configurable"].update(overrides)
    return RunnableConfig(configurable=config["configurable"])


# ========== Tests for generate_query ==========
class TestGenerateQuery:
    @patch("agent.nodes.ChatGoogleGenerativeAI")
    def test_generate_query_creates_structured_queries(self, mock_llm_class):
        """Test that generate_query produces search queries from conversation."""
        mock_llm_instance = Mock()
        mock_structured_llm = Mock()
        mock_llm_class.return_value = mock_llm_instance
        mock_llm_instance.with_structured_output.return_value = mock_structured_llm

        # Mock the structured output
        mock_result = Mock()
        mock_result.query = ["renewable energy trends 2024", "solar panel efficiency"]
        mock_structured_llm.invoke.return_value = mock_result

        state = make_state()
        config = make_config(number_of_initial_queries=2)

        result = generate_query(state, config)

        assert "search_query" in result
        assert len(result["search_query"]) == 2
        assert "renewable energy trends 2024" in result["search_query"]
        mock_structured_llm.invoke.assert_called_once()

    @patch("agent.nodes.ChatGoogleGenerativeAI")
    def test_generate_query_uses_custom_query_count(self, mock_llm_class):
        """Test that custom initial_search_query_count is respected."""
        mock_llm_instance = Mock()
        mock_structured_llm = Mock()
        mock_llm_class.return_value = mock_llm_instance
        mock_llm_instance.with_structured_output.return_value = mock_structured_llm

        mock_result = Mock()
        mock_result.query = ["query1", "query2", "query3"]
        mock_structured_llm.invoke.return_value = mock_result

        state = make_state(initial_search_query_count=3)
        config = make_config()

        result = generate_query(state, config)

        # Verify the prompt includes the custom count
        call_args = mock_structured_llm.invoke.call_args[0][0]
        assert "3" in call_args or state["initial_search_query_count"] == 3


# ========== Tests for continue_to_web_research ==========
class TestContinueToWebResearch:
    def test_continue_to_web_research_fans_out_queries(self):
        """Test that continue_to_web_research creates Send objects for each query."""
        state = {"search_query": ["query1", "query2", "query3"]}

        result = continue_to_web_research(state)

        assert isinstance(result, list)
        assert len(result) == 3
        assert all(hasattr(send, "node") for send in result)
        assert all(send.node == "web_research" for send in result)

    def test_continue_to_web_research_handles_empty_queries(self):
        """Test behavior with empty query list."""
        state = {"search_query": []}

        result = continue_to_web_research(state)

        assert isinstance(result, list)
        assert len(result) == 0

    def test_continue_to_web_research_assigns_ids(self):
        """Test that each Send object gets a unique ID."""
        state = {"search_query": ["query1", "query2"]}

        result = continue_to_web_research(state)

        # Check that IDs are assigned (0, 1, etc.)
        assert result[0].arg["id"] == 0
        assert result[1].arg["id"] == 1


# ========== Tests for planning helper functions ==========
class TestPlanningHelpers:
    def test_handle_end_plan_sets_correct_status(self):
        """Test _handle_end_plan returns expected state updates."""
        state = make_state()
        result = _handle_end_plan(state)

        assert result["planning_status"] == "auto_approved"
        assert result["planning_steps"] == []
        assert "Planning disabled via /end_plan" in result["planning_feedback"][0]

    def test_handle_confirm_plan_sets_confirmed_status(self):
        """Test _handle_confirm_plan returns confirmed status."""
        state = make_state()
        result = _handle_confirm_plan(state)

        assert result["planning_status"] == "confirmed"
        assert "Plan confirmed" in result["planning_feedback"][0]

    def test_handle_start_plan_awaits_confirmation(self):
        """Test _handle_start_plan sets awaiting_confirmation status."""
        state = make_state()
        result = _handle_start_plan(state)

        assert result["planning_status"] == "awaiting_confirmation"
        assert "Planning mode started" in result["planning_feedback"][0]


# ========== Tests for planning_mode ==========
class TestPlanningMode:
    def test_planning_mode_creates_plan_steps_from_queries(self):
        """Test planning_mode creates structured plan steps."""
        state = make_state(search_query=["query1", "query2"])
        config = make_config(require_planning_confirmation=False)

        result = planning_mode(state, config)

        assert len(result["planning_steps"]) == 2
        assert result["planning_steps"][0]["title"] == "Investigate: query1"
        assert result["planning_steps"][0]["query"] == "query1"
        assert result["planning_steps"][0]["suggested_tool"] == "web_research"
        assert result["planning_steps"][0]["status"] == "pending"

    def test_planning_mode_auto_approves_when_flag_false(self):
        """Test planning_mode auto-approves when require_planning_confirmation is False."""
        state = make_state()
        config = make_config(require_planning_confirmation=False)

        result = planning_mode(state, config)

        assert result["planning_status"] == "auto_approved"

    def test_planning_mode_awaits_confirmation_when_flag_true(self):
        """Test planning_mode awaits confirmation when flag is True."""
        state = make_state()
        config = make_config(require_planning_confirmation=True)

        result = planning_mode(state, config)

        assert result["planning_status"] == "awaiting_confirmation"

    def test_planning_mode_handles_end_plan_command(self):
        """Test planning_mode respects /end_plan command."""
        state = make_state(messages=[{"content": "/end_plan"}])
        config = make_config()

        result = planning_mode(state, config)

        assert result["planning_steps"] == []
        assert result["planning_status"] == "auto_approved"
        assert "Planning skipped via /end_plan" in result["planning_feedback"][0]

    def test_planning_mode_handles_empty_queries(self):
        """Test planning_mode gracefully handles no queries."""
        state = make_state(search_query=[])
        config = make_config()

        result = planning_mode(state, config)

        assert result["planning_steps"] == []
        assert any("No queries available" in fb for fb in result["planning_feedback"])

    def test_planning_mode_generates_unique_plan_ids(self):
        """Test that each plan step gets a unique ID."""
        state = make_state(search_query=["q1", "q2", "q3"])
        config = make_config()

        result = planning_mode(state, config)

        ids = [step["id"] for step in result["planning_steps"]]
        assert len(ids) == len(set(ids))  # All unique
        assert ids == ["plan-0", "plan-1", "plan-2"]


# ========== Tests for planning_wait ==========
class TestPlanningWait:
    def test_planning_wait_provides_feedback(self):
        """Test planning_wait returns appropriate feedback message."""
        state = make_state()

        result = planning_wait(state)

        assert "planning_feedback" in result
        assert "Awaiting user confirmation" in result["planning_feedback"][0]


# ========== Tests for planning_router ==========
class TestPlanningRouter:
    def test_planning_router_routes_to_wait_on_plan_command(self):
        """Test router sends to planning_wait on /plan command."""
        state = make_state(messages=[{"content": "/plan"}])
        config = make_config(require_planning_confirmation=True)

        result = planning_router(state, config)

        assert result == "planning_wait"

    def test_planning_router_routes_to_research_on_end_plan(self):
        """Test router sends to web_research on /end_plan command."""
        state = make_state(messages=[{"content": "/end_plan"}], search_query=["q1"])
        config = make_config()

        result = planning_router(state, config)

        assert isinstance(result, list)
        assert result[0].node == "web_research"

    def test_planning_router_routes_to_research_on_confirm(self):
        """Test router routes to research when plan is confirmed."""
        state = make_state(planning_status="confirmed", search_query=["q1"])
        config = make_config()

        result = planning_router(state, config)

        assert isinstance(result, list)
        assert result[0].node == "web_research"

    def test_planning_router_waits_when_confirmation_required(self):
        """Test router waits when confirmation is required and not yet given."""
        state = make_state(planning_status=None)
        config = make_config(require_planning_confirmation=True)

        result = planning_router(state, config)

        assert result == "planning_wait"

    def test_planning_router_auto_proceeds_without_confirmation_flag(self):
        """Test router proceeds automatically when confirmation not required."""
        state = make_state(planning_status="auto_approved", search_query=["q1"])
        config = make_config(require_planning_confirmation=False)

        result = planning_router(state, config)

        assert isinstance(result, list)
        assert result[0].node == "web_research"


# ========== Tests for validation helper functions ==========
class TestValidationHelpers:
    def test_flatten_queries_handles_nested_lists(self):
        """Test _flatten_queries flattens nested list structures."""
        queries = ["q1", ["q2", "q3"], [["q4"]]]

        result = _flatten_queries(queries)

        assert result == ["q1", "q2", "q3", "q4"]

    def test_flatten_queries_handles_flat_list(self):
        """Test _flatten_queries with already flat list."""
        queries = ["q1", "q2", "q3"]

        result = _flatten_queries(queries)

        assert result == ["q1", "q2", "q3"]

    def test_flatten_queries_handles_empty_list(self):
        """Test _flatten_queries with empty list."""
        result = _flatten_queries([])
        assert result == []

    def test_keywords_from_queries_extracts_keywords(self):
        """Test _keywords_from_queries extracts meaningful keywords."""
        queries = ["machine learning algorithms", "deep-neural networks"]

        result = _keywords_from_queries(queries)

        assert "machine" in result
        assert "learning" in result
        assert "algorithms" in result
        assert "deep" in result
        assert "neural" in result
        assert "networks" in result

    def test_keywords_from_queries_filters_short_tokens(self):
        """Test _keywords_from_queries filters tokens shorter than 4 chars."""
        queries = ["AI ML NLP deep learning"]

        result = _keywords_from_queries(queries)

        assert "AI" not in result
        assert "ML" not in result
        assert "NLP" not in result
        assert "deep" in result
        assert "learning" in result

    def test_keywords_from_queries_lowercases_tokens(self):
        """Test _keywords_from_queries converts to lowercase."""
        queries = ["MACHINE Learning"]

        result = _keywords_from_queries(queries)

        assert "machine" in result
        assert "learning" in result
        assert "MACHINE" not in result


# ========== Tests for validate_web_results ==========
class TestValidateWebResults:
    def test_validate_web_results_keeps_relevant_summaries(self):
        """Test validation keeps summaries matching query keywords."""
        state = make_state(
            search_query=["renewable energy"],
            web_research_result=[
                "Renewable energy sources are growing rapidly.",
                "Celebrity news and gossip.",
            ],
        )
        config = make_config()

        result = validate_web_results(state, config)

        assert len(result["validated_web_research_result"]) == 1
        assert "Renewable energy sources" in result["validated_web_research_result"][0]
        assert any("Result 2 filtered" in note for note in result["validation_notes"])

    def test_validate_web_results_handles_fuzzy_matching(self):
        """Test validation handles fuzzy keyword matching."""
        state = make_state(
            search_query=["quantum computing"],
            web_research_result=[
                "Quantum computers achieve breakthrough.",  # Close match
                "Classical computing history.",
            ],
        )
        config = make_config()

        result = validate_web_results(state, config)

        # Should keep the quantum-related summary
        assert len(result["validated_web_research_result"]) >= 1
        assert "Quantum" in result["validated_web_research_result"][0]

    def test_validate_web_results_falls_back_on_no_matches(self):
        """Test validation falls back to original summaries if all fail."""
        state = make_state(
            search_query=["specific technical term xyz123"],
            web_research_result=["Generic summary about nothing related."],
        )
        config = make_config()

        result = validate_web_results(state, config)

        # Should retain original to avoid data loss
        assert result["validated_web_research_result"] == state["web_research_result"]
        assert any("All summaries failed" in note for note in result["validation_notes"])

    def test_validate_web_results_handles_empty_summaries(self):
        """Test validation handles empty summary list."""
        state = make_state(search_query=["query"], web_research_result=[])
        config = make_config()

        result = validate_web_results(state, config)

        assert result["validated_web_research_result"] == []
        assert "No web research summaries available" in result["validation_notes"][0]

    def test_validate_web_results_handles_nested_queries(self):
        """Test validation handles nested query structures."""
        state = make_state(
            search_query=[["machine learning", "deep learning"]],
            web_research_result=["Machine learning models are advancing."],
        )
        config = make_config()

        result = validate_web_results(state, config)

        assert len(result["validated_web_research_result"]) == 1


# ========== Tests for evaluate_research ==========
class TestEvaluateResearch:
    def test_evaluate_research_finalizes_when_sufficient(self):
        """Test evaluate_research routes to finalize when research is sufficient."""
        state = make_state(
            is_sufficient=True,
            research_loop_count=1,
            follow_up_queries=[],
            number_of_ran_queries=3,
        )
        config = make_config()

        result = evaluate_research(state, config)

        assert result == "finalize_answer"

    def test_evaluate_research_finalizes_at_max_loops(self):
        """Test evaluate_research finalizes at max research loops."""
        state = make_state(
            is_sufficient=False,
            research_loop_count=5,
            max_research_loops=5,
            follow_up_queries=["more research"],
            number_of_ran_queries=10,
        )
        config = make_config(max_research_loops=5)

        result = evaluate_research(state, config)

        assert result == "finalize_answer"

    def test_evaluate_research_continues_when_insufficient(self):
        """Test evaluate_research continues research when insufficient."""
        state = make_state(
            is_sufficient=False,
            research_loop_count=1,
            max_research_loops=5,
            follow_up_queries=["follow up query 1", "follow up query 2"],
            number_of_ran_queries=3,
        )
        config = make_config(max_research_loops=5)

        result = evaluate_research(state, config)

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(send.node == "web_research" for send in result)

    def test_evaluate_research_uses_custom_max_loops_from_state(self):
        """Test evaluate_research uses max_research_loops from state if available."""
        state = make_state(
            is_sufficient=False,
            research_loop_count=3,
            max_research_loops=3,  # State value
            follow_up_queries=["query"],
            number_of_ran_queries=5,
        )
        config = make_config(max_research_loops=10)  # Config value

        result = evaluate_research(state, config)

        # Should finalize because state's max_research_loops (3) is reached
        assert result == "finalize_answer"


# ========== Tests for finalize_answer ==========
class TestFinalizeAnswer:
    @patch("agent.nodes.ChatGoogleGenerativeAI")
    def test_finalize_answer_creates_ai_message(self, mock_llm_class):
        """Test finalize_answer generates AI message with answer."""
        mock_llm_instance = Mock()
        mock_llm_class.return_value = mock_llm_instance

        mock_response = Mock()
        mock_response.content = "Final answer with citations [1]."
        mock_llm_instance.invoke.return_value = mock_response

        state = make_state(
            web_research_result=["Summary 1", "Summary 2"],
            sources_gathered=[
                {"short_url": "[1]", "value": "https://example.com"},
            ],
        )
        config = make_config()

        result = finalize_answer(state, config)

        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)
        assert "Final answer" in result["messages"][0].content

    @patch("agent.nodes.ChatGoogleGenerativeAI")
    def test_finalize_answer_replaces_short_urls(self, mock_llm_class):
        """Test finalize_answer replaces short URLs with original URLs."""
        mock_llm_instance = Mock()
        mock_llm_class.return_value = mock_llm_instance

        mock_response = Mock()
        mock_response.content = "Answer with citation [1] and [2]."
        mock_llm_instance.invoke.return_value = mock_response

        state = make_state(
            web_research_result=["Summary"],
            sources_gathered=[
                {"short_url": "[1]", "value": "https://example.com/page1"},
                {"short_url": "[2]", "value": "https://example.com/page2"},
            ],
        )
        config = make_config()

        result = finalize_answer(state, config)

        content = result["messages"][0].content
        assert "https://example.com/page1" in content
        assert "https://example.com/page2" in content
        assert "[1]" not in content
        assert "[2]" not in content

    @patch("agent.nodes.ChatGoogleGenerativeAI")
    def test_finalize_answer_includes_only_used_sources(self, mock_llm_class):
        """Test finalize_answer includes only sources referenced in answer."""
        mock_llm_instance = Mock()
        mock_llm_class.return_value = mock_llm_instance

        mock_response = Mock()
        mock_response.content = "Answer with citation [1]."
        mock_llm_instance.invoke.return_value = mock_response

        state = make_state(
            web_research_result=["Summary"],
            sources_gathered=[
                {"short_url": "[1]", "value": "https://used.com"},
                {"short_url": "[2]", "value": "https://unused.com"},
            ],
        )
        config = make_config()

        result = finalize_answer(state, config)

        assert len(result["sources_gathered"]) == 1
        assert result["sources_gathered"][0]["value"] == "https://used.com"

    @patch("agent.nodes.ChatGoogleGenerativeAI")
    def test_finalize_answer_uses_custom_reasoning_model(self, mock_llm_class):
        """Test finalize_answer uses reasoning_model from state if available."""
        mock_llm_instance = Mock()
        mock_llm_class.return_value = mock_llm_instance

        mock_response = Mock()
        mock_response.content = "Answer"
        mock_llm_instance.invoke.return_value = mock_response

        state = make_state(
            reasoning_model="gemini-2.5-flash-preview-04-17",
            web_research_result=["Summary"],
            sources_gathered=[],
        )
        config = make_config()

        result = finalize_answer(state, config)

        # Verify the model parameter
        mock_llm_class.assert_called_once()
        call_kwargs = mock_llm_class.call_args[1]
        assert call_kwargs["model"] == "gemini-2.5-flash-preview-04-17"


# ========== Tests for web_research (mocked) ==========
class TestWebResearch:
    @patch("agent.nodes.genai_client")
    @patch("agent.nodes.resolve_urls")
    @patch("agent.nodes.get_citations")
    @patch("agent.nodes.insert_citation_markers")
    def test_web_research_returns_research_results(
        self, mock_insert, mock_citations, mock_resolve, mock_client
    ):
        """Test web_research returns formatted research results."""
        # Mock the Gemini API response
        mock_response = Mock()
        mock_response.text = "Research summary about solar energy."
        mock_candidate = Mock()
        mock_candidate.grounding_metadata = Mock()
        mock_candidate.grounding_metadata.grounding_chunks = []
        mock_response.candidates = [mock_candidate]

        mock_client.models.generate_content.return_value = mock_response
        mock_resolve.return_value = {}
        mock_citations.return_value = []
        mock_insert.return_value = "Research summary with citations."

        state = {"search_query": "solar energy", "id": "0"}
        config = make_config()

        result = web_research(state, config)

        assert "web_research_result" in result
        assert "sources_gathered" in result
        assert "search_query" in result
        assert len(result["web_research_result"]) == 1

    @patch("agent.nodes.genai_client")
    def test_web_research_handles_no_grounding_metadata(self, mock_client):
        """Test web_research handles missing grounding metadata gracefully."""
        mock_response = Mock()
        mock_response.text = "Plain text response."
        mock_response.candidates = []

        mock_client.models.generate_content.return_value = mock_response

        state = {"search_query": "test query", "id": "0"}
        config = make_config()

        result = web_research(state, config)

        assert "web_research_result" in result
        assert result["web_research_result"] == ["Plain text response."]
        assert result["sources_gathered"] == []


# ========== Tests for reflection (mocked) ==========
class TestReflection:
    @patch("agent.nodes.ChatGoogleGenerativeAI")
    def test_reflection_identifies_knowledge_gaps(self, mock_llm_class):
        """Test reflection node identifies knowledge gaps and suggests follow-ups."""
        mock_llm_instance = Mock()
        mock_structured_llm = Mock()
        mock_llm_class.return_value = mock_llm_instance
        mock_llm_instance.with_structured_output.return_value = mock_structured_llm

        mock_result = Mock()
        mock_result.is_sufficient = False
        mock_result.knowledge_gap = "Need more recent data"
        mock_result.follow_up_queries = ["latest solar energy stats 2024"]
        mock_structured_llm.invoke.return_value = mock_result

        state = make_state(
            validated_web_research_result=["Summary 1"],
            research_loop_count=0,
        )
        config = make_config()

        result = reflection(state, config)

        assert result["is_sufficient"] is False
        assert "Need more recent data" in result["knowledge_gap"]
        assert len(result["follow_up_queries"]) == 1

    @patch("agent.nodes.ChatGoogleGenerativeAI")
    def test_reflection_marks_sufficient_when_complete(self, mock_llm_class):
        """Test reflection marks research as sufficient when criteria met."""
        mock_llm_instance = Mock()
        mock_structured_llm = Mock()
        mock_llm_class.return_value = mock_llm_instance
        mock_llm_instance.with_structured_output.return_value = mock_structured_llm

        mock_result = Mock()
        mock_result.is_sufficient = True
        mock_result.knowledge_gap = ""
        mock_result.follow_up_queries = []
        mock_structured_llm.invoke.return_value = mock_result

        state = make_state(validated_web_research_result=["Comprehensive summary"])
        config = make_config()

        result = reflection(state, config)

        assert result["is_sufficient"] is True
        assert result["follow_up_queries"] == []

    @patch("agent.nodes.ChatGoogleGenerativeAI")
    def test_reflection_increments_research_loop_count(self, mock_llm_class):
        """Test reflection increments the research loop counter."""
        mock_llm_instance = Mock()
        mock_structured_llm = Mock()
        mock_llm_class.return_value = mock_llm_instance
        mock_llm_instance.with_structured_output.return_value = mock_structured_llm

        mock_result = Mock()
        mock_result.is_sufficient = False
        mock_result.knowledge_gap = "Gap"
        mock_result.follow_up_queries = ["query"]
        mock_structured_llm.invoke.return_value = mock_result

        state = make_state(research_loop_count=2)
        config = make_config()

        result = reflection(state, config)

        assert result["research_loop_count"] == 3