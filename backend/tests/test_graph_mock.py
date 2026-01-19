from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent.models import TEST_MODEL
from agent.nodes import (
    denoising_refiner,
    generate_plan,
    load_context,
    reflection,
    web_research,
)

TEST_MODEL = "gemma-3-27b-it"


@pytest.fixture
def mock_state():
    return {
        "messages": [HumanMessage(content="Test user query")],
        "initial_search_query_count": 2,
        "max_research_loops": 1,
        "research_loop_count": 0,
        "search_query": "previous query",
        "web_research_result": [],
        "sources_gathered": [],
    }


@pytest.fixture
def mock_config():
    return {
        "configurable": {
            "query_generator_model": "gemini-2.5-flash",
            "reflection_model": "gemini-2.5-flash",
            "answer_model": "gemini-2.5-flash",
        }
    }


class TestGraphNodes:
    @patch("agent.nodes.ChatGoogleGenerativeAI")
    @patch("agent.nodes.get_context_manager")
    @patch("agent.nodes.plan_writer_instructions")
    def test_generate_plan_success(
        self, mock_instructions, mock_get_cm, MockLLM, mock_state, mock_config
    ):
        # Mock prompts
        mock_get_cm.return_value.truncate_to_fit.return_value = "Mock Prompt"
        mock_instructions.format.return_value = "Mock Prompt"

        # Mock LLM instance and response
        mock_instance = MockLLM.return_value
        mock_instance.with_structured_output.return_value.invoke.return_value = Mock(
            plan=[
                Mock(title="query1", description="desc", status="pending"),
                Mock(title="query2", description="desc", status="pending"),
            ],
            rationale="rationale",
        )
        # Mock raw invoke too in case it falls back
        mock_instance.invoke.return_value = AIMessage(content="Raw plan")

        with patch("agent.nodes._get_rate_limited_llm") as mock_get_llm:
            mock_get_llm.return_value = mock_instance
            result = generate_plan(mock_state, mock_config)

        assert "plan" in result
        assert "search_query" in result
        assert result["search_query"] == ["query1", "query2"]

    @patch("agent.nodes.search_router")
    def test_web_research_success(self, mock_router, mock_state, mock_config):
        # Mock SearchRouter response
        mock_result = Mock()
        mock_result.title = "Test Page"
        mock_result.url = "http://test.com"
        mock_result.content = "Test content"
        mock_result.raw_content = None

        mock_router.search.return_value = [mock_result]

        state = mock_state.copy()
        state["search_query"] = "test query"

        result = web_research(state, mock_config)

        assert "web_research_result" in result
        assert (
            "Test content [Test Page](http://test.com)"
            in result["web_research_result"][0]
        )
        assert len(result["sources_gathered"]) == 1
        assert result["sources_gathered"][0]["label"] == "Test Page"

    @patch("agent.nodes.search_router")
    def test_web_research_failure(self, mock_router, mock_state, mock_config):
        # Mock SearchRouter failure
        mock_router.search.side_effect = Exception("Search failed")

        state = mock_state.copy()
        state["search_query"] = "test query"

        result = web_research(state, mock_config)

        assert result["web_research_result"] == []
        assert "Search failed for query 'test query'" in result["validation_notes"][0]

    @patch("agent.nodes.ChatGoogleGenerativeAI")
    def test_reflection_sufficient(self, MockLLM, mock_state, mock_config):
        mock_instance = MockLLM.return_value
        mock_instance.with_structured_output.return_value.invoke.return_value = Mock(
            is_sufficient=True, knowledge_gap="None", follow_up_queries=[]
        )

        with patch("agent.nodes._get_rate_limited_llm") as mock_get_llm:
            mock_get_llm.return_value = mock_instance
            result = reflection(mock_state, mock_config)

        assert result["is_sufficient"] is True
        assert result["research_loop_count"] == 1

    @patch("agent.nodes.ChatGoogleGenerativeAI")
    def test_denoising_refiner(self, MockLLM, mock_state, mock_config):
        # denoising_refiner makes 3 calls: Draft 1, Draft 2, Refine
        mock_instance = MockLLM.return_value
        mock_instance.invoke.side_effect = [
            AIMessage(content="Draft 1"),
            AIMessage(content="Draft 2"),
            AIMessage(content="Final Answer with url: http://short.url"),
        ]

        state = mock_state.copy()
        state["sources_gathered"] = [
            {"short_url": "http://short.url", "value": "http://real.url"}
        ]
        state["validated_web_research_result"] = ["Some context"]

        with patch("agent.nodes._get_rate_limited_llm") as mock_get_llm:
            mock_get_llm.return_value = mock_instance
            result = denoising_refiner(state, mock_config)

        # It returns messages list where first item is AIMessage
        assert "messages" in result
        assert "Final Answer with url: http://real.url" in result["messages"][0].content
        assert "artifacts" in result

    @patch("agent.nodes.load_plan")
    def test_load_context_success(self, mock_load_plan, mock_state):
        mock_load_plan.return_value = {"todo_list": ["item1"], "artifacts": {"a": 1}}

        config = {"configurable": {"thread_id": "123"}}
        result = load_context(mock_state, config)

        assert result["todo_list"] == ["item1"]
        assert result["artifacts"] == {"a": 1}

    def test_load_context_no_thread(self, mock_state):
        config = {"configurable": {}}
        result = load_context(mock_state, config)
        assert result == {}
