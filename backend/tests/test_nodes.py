import pathlib
import sys
from unittest.mock import Mock, patch, MagicMock

import pytest
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Send

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from agent.nodes import (  # noqa: E402
    generate_query,
    continue_to_web_research,
    web_research,
    planning_mode,
    planning_wait,
    planning_router,
    validate_web_results,
    reflection,
    evaluate_research,
    finalize_answer,
    _flatten_queries,
    _keywords_from_queries,
    _handle_end_plan,
    _handle_confirm_plan,
    _handle_start_plan,
)


class TestHelperFunctions:
    """Test suite for helper functions in nodes.py."""

    def test_flatten_queries_with_nested_lists(self):
        """Test _flatten_queries with nested list structures."""
        queries = ["query1", ["query2", "query3"], [["query4"], "query5"]]
        result = _flatten_queries(queries)
        assert result == ["query1", "query2", "query3", "query4", "query5"]

    def test_flatten_queries_with_flat_list(self):
        """Test _flatten_queries with already flat list."""
        queries = ["query1", "query2", "query3"]
        result = _flatten_queries(queries)
        assert result == ["query1", "query2", "query3"]

    def test_flatten_queries_empty_list(self):
        """Test _flatten_queries with empty list."""
        result = _flatten_queries([])
        assert result == []

    def test_keywords_from_queries_basic(self):
        """Test _keywords_from_queries extracts keywords correctly."""
        queries = ["quantum computing advancements", "machine learning trends"]
        keywords = _keywords_from_queries(queries)
        assert "quantum" in keywords
        assert "computing" in keywords
        assert "advancements" in keywords
        assert "machine" in keywords
        assert "learning" in keywords
        assert "trends" in keywords

    def test_keywords_from_queries_filters_short_tokens(self):
        """Test that tokens shorter than 4 characters are filtered."""
        queries = ["ai ml in cs"]
        keywords = _keywords_from_queries(queries)
        # All tokens are < 4 chars, should be empty
        assert keywords == []

    def test_keywords_from_queries_handles_special_characters(self):
        """Test keyword extraction with special characters."""
        queries = ["what-is-quantum-computing?", "ai/ml trends 2024"]
        keywords = _keywords_from_queries(queries)
        assert "what" in keywords
        assert "quantum" in keywords
        assert "computing" in keywords
        assert "trends" in keywords
        assert "2024" in keywords

    def test_keywords_from_queries_lowercase_normalization(self):
        """Test that keywords are normalized to lowercase."""
        queries = ["QUANTUM Computing", "Machine LEARNING"]
        keywords = _keywords_from_queries(queries)
        assert "quantum" in keywords
        assert "computing" in keywords
        assert "machine" in keywords
        assert "learning" in keywords
        # Should not contain uppercase versions
        assert "QUANTUM" not in keywords

    def test_handle_end_plan(self):
        """Test _handle_end_plan returns correct state update."""
        state = {"planning_status": None, "planning_steps": None}
        result = _handle_end_plan(state)
        assert result["planning_status"] == "auto_approved"
        assert result["planning_steps"] == []
        assert "Planning disabled via /end_plan." in result["planning_feedback"]

    def test_handle_confirm_plan(self):
        """Test _handle_confirm_plan returns correct state update."""
        state = {"planning_status": "awaiting_confirmation"}
        result = _handle_confirm_plan(state)
        assert result["planning_status"] == "confirmed"
        assert "Plan confirmed. Proceeding to research." in result["planning_feedback"]

    def test_handle_start_plan(self):
        """Test _handle_start_plan returns correct state update."""
        state = {"planning_status": None}
        result = _handle_start_plan(state)
        assert result["planning_status"] == "awaiting_confirmation"
        assert "Planning mode started. Please review the plan." in result["planning_feedback"]


class TestGenerateQuery:
    """Test suite for generate_query node."""

    @patch("agent.nodes.ChatGoogleGenerativeAI")
    @patch("agent.nodes.get_current_date")
    @patch("agent.nodes.get_research_topic")
    def test_generate_query_basic(self, mock_get_topic, mock_get_date, mock_llm_class):
        """Test generate_query generates queries correctly."""
        # Setup mocks
        mock_get_date.return_value = "January 1, 2024"
        mock_get_topic.return_value = "quantum computing"
        
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_result = Mock()
        mock_result.query = ["quantum computing basics", "quantum algorithms"]
        mock_structured_llm.invoke.return_value = mock_result
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_llm_class.return_value = mock_llm

        state = {
            "messages": [{"content": "Tell me about quantum computing"}],
            "initial_search_query_count": None,
        }
        config = RunnableConfig(configurable={"number_of_initial_queries": 2})

        result = generate_query(state, config)

        assert result["search_query"] == ["quantum computing basics", "quantum algorithms"]
        mock_llm_class.assert_called_once()
        mock_llm.with_structured_output.assert_called_once()

    @patch("agent.nodes.ChatGoogleGenerativeAI")
    @patch("agent.nodes.get_current_date")
    @patch("agent.nodes.get_research_topic")
    def test_generate_query_uses_state_query_count(
        self, mock_get_topic, mock_get_date, mock_llm_class
    ):
        """Test that generate_query uses initial_search_query_count from state."""
        mock_get_date.return_value = "January 1, 2024"
        mock_get_topic.return_value = "AI"
        
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_result = Mock()
        mock_result.query = ["query1", "query2", "query3"]
        mock_structured_llm.invoke.return_value = mock_result
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_llm_class.return_value = mock_llm

        state = {
            "messages": [{"content": "Research AI"}],
            "initial_search_query_count": 3,
        }
        config = RunnableConfig(configurable={"number_of_initial_queries": 2})

        result = generate_query(state, config)

        # Should use state value (3), not config value (2)
        assert result["search_query"] == ["query1", "query2", "query3"]


class TestContinueToWebResearch:
    """Test suite for continue_to_web_research node."""

    def test_continue_to_web_research_creates_send_objects(self):
        """Test that continue_to_web_research creates Send objects for each query."""
        state = {"search_query": ["query1", "query2", "query3"]}
        result = continue_to_web_research(state)

        assert len(result) == 3
        assert all(isinstance(send, Send) for send in result)
        assert result[0].node == "web_research"
        assert result[0].arg["search_query"] == "query1"
        assert result[0].arg["id"] == 0
        assert result[2].arg["search_query"] == "query3"
        assert result[2].arg["id"] == 2

    def test_continue_to_web_research_empty_queries(self):
        """Test with empty query list."""
        state = {"search_query": []}
        result = continue_to_web_research(state)
        assert result == []

    def test_continue_to_web_research_single_query(self):
        """Test with single query."""
        state = {"search_query": ["solo query"]}
        result = continue_to_web_research(state)
        assert len(result) == 1
        assert result[0].arg["search_query"] == "solo query"


class TestWebResearch:
    """Test suite for web_research node."""

    @patch("agent.nodes.genai_client")
    @patch("agent.nodes.get_current_date")
    @patch("agent.nodes.resolve_urls")
    @patch("agent.nodes.get_citations")
    @patch("agent.nodes.insert_citation_markers")
    def test_web_research_successful_search(
        self,
        mock_insert_markers,
        mock_get_citations,
        mock_resolve_urls,
        mock_get_date,
        mock_genai_client,
    ):
        """Test successful web research with grounding metadata."""
        mock_get_date.return_value = "January 1, 2024"
        
        # Mock the response from genai client
        mock_response = Mock()
        mock_response.text = "Research findings about quantum computing"
        mock_candidate = Mock()
        mock_grounding_metadata = Mock()
        mock_grounding_metadata.grounding_chunks = ["chunk1", "chunk2"]
        mock_candidate.grounding_metadata = mock_grounding_metadata
        mock_response.candidates = [mock_candidate]
        
        mock_genai_client.models.generate_content.return_value = mock_response
        
        # Mock utility functions
        mock_resolve_urls.return_value = {"url1": "short1", "url2": "short2"}
        mock_citations = [
            {"segments": [{"label": "source1", "value": "url1"}]},
            {"segments": [{"label": "source2", "value": "url2"}]},
        ]
        mock_get_citations.return_value = mock_citations
        mock_insert_markers.return_value = "Research findings [1][2]"

        state = {"search_query": "quantum computing", "id": "0"}
        config = RunnableConfig(configurable={"query_generator_model": "gemini-2.0-flash"})

        result = web_research(state, config)

        assert result["search_query"] == ["quantum computing"]
        assert result["web_research_result"] == ["Research findings [1][2]"]
        assert len(result["sources_gathered"]) == 2
        mock_genai_client.models.generate_content.assert_called_once()

    @patch("agent.nodes.genai_client")
    @patch("agent.nodes.get_current_date")
    def test_web_research_no_grounding_metadata(self, mock_get_date, mock_genai_client):
        """Test web research fallback when no grounding metadata available."""
        mock_get_date.return_value = "January 1, 2024"
        
        mock_response = Mock()
        mock_response.text = "Basic research text"
        mock_response.candidates = []
        
        mock_genai_client.models.generate_content.return_value = mock_response

        state = {"search_query": "AI research", "id": "1"}
        config = RunnableConfig(configurable={"query_generator_model": "gemini-2.0-flash"})

        result = web_research(state, config)

        assert result["sources_gathered"] == []
        assert result["search_query"] == ["AI research"]
        assert result["web_research_result"] == ["Basic research text"]


class TestPlanningMode:
    """Test suite for planning_mode node."""

    def test_planning_mode_creates_steps_from_queries(self):
        """Test that planning_mode creates plan steps from queries."""
        state = {
            "messages": [{"content": "research topic"}],
            "search_query": ["query1", "query2", "query3"],
            "planning_status": None,
        }
        config = RunnableConfig(configurable={"require_planning_confirmation": False})

        result = planning_mode(state, config)

        assert len(result["planning_steps"]) == 3
        assert result["planning_steps"][0]["id"] == "plan-0"
        assert result["planning_steps"][0]["title"] == "Investigate: query1"
        assert result["planning_steps"][0]["query"] == "query1"
        assert result["planning_steps"][0]["status"] == "pending"
        assert result["planning_status"] == "auto_approved"

    def test_planning_mode_awaiting_confirmation(self):
        """Test planning_mode sets awaiting_confirmation when required."""
        state = {
            "messages": [{"content": "research"}],
            "search_query": ["query1"],
            "planning_status": None,
        }
        config = RunnableConfig(configurable={"require_planning_confirmation": True})

        result = planning_mode(state, config)

        assert result["planning_status"] == "awaiting_confirmation"
        assert len(result["planning_steps"]) == 1

    def test_planning_mode_end_plan_command(self):
        """Test planning_mode handles /end_plan command."""
        state = {
            "messages": [{"content": "/end_plan"}],
            "search_query": ["query1"],
            "planning_status": None,
        }
        config = RunnableConfig(configurable={"require_planning_confirmation": True})

        result = planning_mode(state, config)

        assert result["planning_steps"] == []
        assert result["planning_status"] == "auto_approved"
        assert "Planning skipped via /end_plan." in result["planning_feedback"]

    def test_planning_mode_idempotent_when_auto_approved(self):
        """Test planning_mode is idempotent when already auto_approved."""
        state = {
            "messages": [{"content": "research"}],
            "search_query": ["query1"],
            "planning_status": "auto_approved",
            "planning_steps": [],
        }
        config = RunnableConfig(configurable={})

        result = planning_mode(state, config)

        assert result["planning_steps"] == []
        assert "Planning skipped." in result["planning_feedback"]

    def test_planning_mode_empty_queries(self):
        """Test planning_mode handles empty queries gracefully."""
        state = {
            "messages": [{"content": "research"}],
            "search_query": [],
            "planning_status": None,
        }
        config = RunnableConfig(configurable={"require_planning_confirmation": False})

        result = planning_mode(state, config)

        assert result["planning_steps"] == []
        assert any("empty plan" in fb.lower() for fb in result["planning_feedback"])


class TestPlanningWait:
    """Test suite for planning_wait node."""

    def test_planning_wait_returns_feedback(self):
        """Test planning_wait returns appropriate feedback."""
        state = {"planning_status": "awaiting_confirmation"}
        result = planning_wait(state)

        assert "planning_feedback" in result
        assert len(result["planning_feedback"]) > 0
        assert "Awaiting user confirmation" in result["planning_feedback"][0]


class TestPlanningRouter:
    """Test suite for planning_router function."""

    def test_planning_router_plan_command(self):
        """Test planning_router handles /plan command."""
        state = {
            "messages": [{"content": "/plan"}],
            "search_query": ["query1"],
            "planning_status": None,
        }
        config = RunnableConfig(configurable={"require_planning_confirmation": True})

        result = planning_router(state, config)

        assert result == "planning_wait"
        assert state["planning_status"] == "awaiting_confirmation"

    def test_planning_router_end_plan_command(self):
        """Test planning_router handles /end_plan command."""
        state = {
            "messages": [{"content": "/end_plan"}],
            "search_query": ["query1"],
            "planning_status": None,
        }
        config = RunnableConfig(configurable={"require_planning_confirmation": True})

        result = planning_router(state, config)

        assert isinstance(result, list)
        assert state["planning_status"] == "auto_approved"

    def test_planning_router_confirm_plan_command(self):
        """Test planning_router handles /confirm_plan command."""
        state = {
            "messages": [{"content": "/confirm_plan"}],
            "search_query": ["query1"],
            "planning_status": "awaiting_confirmation",
        }
        config = RunnableConfig(configurable={"require_planning_confirmation": True})

        result = planning_router(state, config)

        assert isinstance(result, list)
        assert state["planning_status"] == "confirmed"

    def test_planning_router_requires_confirmation(self):
        """Test planning_router waits when confirmation required."""
        state = {
            "messages": [{"content": "research"}],
            "search_query": ["query1"],
            "planning_status": None,
        }
        config = RunnableConfig(configurable={"require_planning_confirmation": True})

        result = planning_router(state, config)

        assert result == "planning_wait"

    def test_planning_router_confirmed_proceeds(self):
        """Test planning_router proceeds when confirmed."""
        state = {
            "messages": [{"content": "research"}],
            "search_query": ["query1"],
            "planning_status": "confirmed",
        }
        config = RunnableConfig(configurable={"require_planning_confirmation": True})

        result = planning_router(state, config)

        assert isinstance(result, list)
        assert len(result) == 1


class TestValidateWebResults:
    """Test suite for validate_web_results node."""

    def test_validate_web_results_keyword_match(self):
        """Test validation passes summaries with keyword matches."""
        state = {
            "search_query": ["quantum computing"],
            "web_research_result": [
                "Quantum computing breakthrough announced",
                "Irrelevant celebrity news",
            ],
        }
        config = RunnableConfig(configurable={})

        result = validate_web_results(state, config)

        assert len(result["validated_web_research_result"]) == 1
        assert "Quantum computing breakthrough" in result["validated_web_research_result"][0]

    def test_validate_web_results_fuzzy_matching(self):
        """Test validation with fuzzy keyword matching."""
        state = {
            "search_query": ["machine learning trends"],
            "web_research_result": [
                "Recent machinelearning developments show promise",
            ],
        }
        config = RunnableConfig(configurable={})

        result = validate_web_results(state, config)

        # Should match due to fuzzy matching
        assert len(result["validated_web_research_result"]) >= 1

    def test_validate_web_results_all_filtered_fallback(self):
        """Test fallback when all summaries filtered."""
        state = {
            "search_query": ["specific technical term"],
            "web_research_result": ["Completely unrelated content"],
        }
        config = RunnableConfig(configurable={})

        result = validate_web_results(state, config)

        # Should retain original to avoid data loss
        assert result["validated_web_research_result"] == ["Completely unrelated content"]
        assert any("All summaries failed" in note for note in result["validation_notes"])

    def test_validate_web_results_empty_summaries(self):
        """Test handling of empty summaries."""
        state = {"search_query": ["query"], "web_research_result": []}
        config = RunnableConfig(configurable={})

        result = validate_web_results(state, config)

        assert result["validated_web_research_result"] == []
        assert "No web research summaries available" in result["validation_notes"][0]

    def test_validate_web_results_no_keywords(self):
        """Test validation with queries that produce no keywords."""
        state = {
            "search_query": ["ai"],  # Too short to generate keywords
            "web_research_result": ["Some research content"],
        }
        config = RunnableConfig(configurable={})

        result = validate_web_results(state, config)

        # Should pass through when no keywords
        assert result["validated_web_research_result"] == ["Some research content"]


class TestReflection:
    """Test suite for reflection node."""

    @patch("agent.nodes.ChatGoogleGenerativeAI")
    @patch("agent.nodes.get_current_date")
    @patch("agent.nodes.get_research_topic")
    def test_reflection_identifies_gap(
        self, mock_get_topic, mock_get_date, mock_llm_class
    ):
        """Test reflection identifies knowledge gaps."""
        mock_get_date.return_value = "January 1, 2024"
        mock_get_topic.return_value = "AI trends"
        
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_result = Mock()
        mock_result.is_sufficient = False
        mock_result.knowledge_gap = "Missing performance data"
        mock_result.follow_up_queries = ["What are AI performance benchmarks?"]
        mock_structured_llm.invoke.return_value = mock_result
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_llm_class.return_value = mock_llm

        state = {
            "messages": [{"content": "Research AI"}],
            "web_research_result": ["Basic AI info"],
            "search_query": ["ai trends"],
            "research_loop_count": 0,
        }
        config = RunnableConfig(configurable={"reflection_model": "gemini-2.5-flash"})

        result = reflection(state, config)

        assert result["is_sufficient"] is False
        assert result["knowledge_gap"] == "Missing performance data"
        assert result["follow_up_queries"] == ["What are AI performance benchmarks?"]
        assert result["research_loop_count"] == 1

    @patch("agent.nodes.ChatGoogleGenerativeAI")
    @patch("agent.nodes.get_current_date")
    @patch("agent.nodes.get_research_topic")
    def test_reflection_sufficient_information(
        self, mock_get_topic, mock_get_date, mock_llm_class
    ):
        """Test reflection when information is sufficient."""
        mock_get_date.return_value = "January 1, 2024"
        mock_get_topic.return_value = "AI"
        
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_result = Mock()
        mock_result.is_sufficient = True
        mock_result.knowledge_gap = ""
        mock_result.follow_up_queries = []
        mock_structured_llm.invoke.return_value = mock_result
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_llm_class.return_value = mock_llm

        state = {
            "messages": [{"content": "Research"}],
            "web_research_result": ["Comprehensive info"],
            "search_query": ["query"],
            "research_loop_count": 2,
        }
        config = RunnableConfig(configurable={})

        result = reflection(state, config)

        assert result["is_sufficient"] is True
        assert result["research_loop_count"] == 3

    @patch("agent.nodes.ChatGoogleGenerativeAI")
    @patch("agent.nodes.get_current_date")
    @patch("agent.nodes.get_research_topic")
    def test_reflection_uses_validated_results(
        self, mock_get_topic, mock_get_date, mock_llm_class
    ):
        """Test reflection prefers validated_web_research_result."""
        mock_get_date.return_value = "January 1, 2024"
        mock_get_topic.return_value = "topic"
        
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_result = Mock()
        mock_result.is_sufficient = True
        mock_result.knowledge_gap = ""
        mock_result.follow_up_queries = []
        mock_structured_llm.invoke.return_value = mock_result
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_llm_class.return_value = mock_llm

        state = {
            "messages": [{"content": "Research"}],
            "web_research_result": ["unvalidated"],
            "validated_web_research_result": ["validated content"],
            "search_query": ["q"],
            "research_loop_count": 0,
        }
        config = RunnableConfig(configurable={})

        reflection(state, config)

        # Verify the prompt included validated results
        call_args = mock_structured_llm.invoke.call_args[0][0]
        assert "validated content" in call_args


class TestEvaluateResearch:
    """Test suite for evaluate_research routing function."""

    def test_evaluate_research_sufficient_routes_to_finalize(self):
        """Test routing to finalize when research is sufficient."""
        state = {
            "is_sufficient": True,
            "research_loop_count": 2,
            "follow_up_queries": [],
        }
        config = RunnableConfig(configurable={"max_research_loops": 5})

        result = evaluate_research(state, config)

        assert result == "finalize_answer"

    def test_evaluate_research_max_loops_reached(self):
        """Test routing to finalize when max loops reached."""
        state = {
            "is_sufficient": False,
            "research_loop_count": 5,
            "follow_up_queries": ["more research"],
        }
        config = RunnableConfig(configurable={"max_research_loops": 5})

        result = evaluate_research(state, config)

        assert result == "finalize_answer"

    def test_evaluate_research_continues_research(self):
        """Test routing continues research when needed."""
        state = {
            "is_sufficient": False,
            "research_loop_count": 2,
            "follow_up_queries": ["query1", "query2"],
            "number_of_ran_queries": 3,
        }
        config = RunnableConfig(configurable={"max_research_loops": 5})

        result = evaluate_research(state, config)

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, Send) for item in result)
        assert result[0].node == "web_research"
        assert result[0].arg["search_query"] == "query1"
        assert result[0].arg["id"] == 3

    def test_evaluate_research_uses_state_max_loops(self):
        """Test that state max_research_loops overrides config."""
        state = {
            "is_sufficient": False,
            "research_loop_count": 7,
            "follow_up_queries": ["query"],
            "max_research_loops": 7,
        }
        config = RunnableConfig(configurable={"max_research_loops": 10})

        result = evaluate_research(state, config)

        # Should use state value (7), so should finalize
        assert result == "finalize_answer"


class TestFinalizeAnswer:
    """Test suite for finalize_answer node."""

    @patch("agent.nodes.ChatGoogleGenerativeAI")
    @patch("agent.nodes.get_current_date")
    @patch("agent.nodes.get_research_topic")
    def test_finalize_answer_generates_response(
        self, mock_get_topic, mock_get_date, mock_llm_class
    ):
        """Test finalize_answer generates final response."""
        mock_get_date.return_value = "January 1, 2024"
        mock_get_topic.return_value = "AI research"
        
        mock_llm = Mock()
        mock_response = AIMessage(content="Final answer with [url1] citation")
        mock_llm.invoke.return_value = mock_response
        mock_llm_class.return_value = mock_llm

        state = {
            "messages": [{"content": "Research AI"}],
            "web_research_result": ["Research findings"],
            "sources_gathered": [
                {"short_url": "[url1]", "value": "https://example.com", "label": "Source 1"}
            ],
        }
        config = RunnableConfig(configurable={"answer_model": "gemini-2.5-pro"})

        result = finalize_answer(state, config)

        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)
        # URL should be replaced
        assert "https://example.com" in result["messages"][0].content
        assert "[url1]" not in result["messages"][0].content

    @patch("agent.nodes.ChatGoogleGenerativeAI")
    @patch("agent.nodes.get_current_date")
    @patch("agent.nodes.get_research_topic")
    def test_finalize_answer_filters_unused_sources(
        self, mock_get_topic, mock_get_date, mock_llm_class
    ):
        """Test that only cited sources are included."""
        mock_get_date.return_value = "January 1, 2024"
        mock_get_topic.return_value = "topic"
        
        mock_llm = Mock()
        mock_response = AIMessage(content="Answer with [url1]")
        mock_llm.invoke.return_value = mock_response
        mock_llm_class.return_value = mock_llm

        state = {
            "messages": [{"content": "Research"}],
            "web_research_result": ["findings"],
            "sources_gathered": [
                {"short_url": "[url1]", "value": "https://used.com", "label": "Used"},
                {"short_url": "[url2]", "value": "https://unused.com", "label": "Unused"},
            ],
        }
        config = RunnableConfig(configurable={})

        result = finalize_answer(state, config)

        # Only url1 should be in sources_gathered
        assert len(result["sources_gathered"]) == 1
        assert result["sources_gathered"][0]["value"] == "https://used.com"

    @patch("agent.nodes.ChatGoogleGenerativeAI")
    @patch("agent.nodes.get_current_date")
    @patch("agent.nodes.get_research_topic")
    def test_finalize_answer_uses_reasoning_model_from_state(
        self, mock_get_topic, mock_get_date, mock_llm_class
    ):
        """Test finalize_answer uses reasoning_model from state."""
        mock_get_date.return_value = "January 1, 2024"
        mock_get_topic.return_value = "topic"
        
        mock_llm = Mock()
        mock_response = AIMessage(content="Final answer")
        mock_llm.invoke.return_value = mock_response
        mock_llm_class.return_value = mock_llm

        state = {
            "messages": [{"content": "Research"}],
            "web_research_result": ["findings"],
            "sources_gathered": [],
            "reasoning_model": "custom-model",
        }
        config = RunnableConfig(configurable={"answer_model": "default-model"})

        finalize_answer(state, config)

        # Should use custom-model from state
        mock_llm_class.assert_called_with(
            model="custom-model", temperature=0, max_retries=2, api_key=None
        )