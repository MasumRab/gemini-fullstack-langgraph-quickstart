import pytest
from unittest.mock import Mock, patch
from agent.nodes import generate_query, web_research, reflection, finalize_answer, load_context
from langchain_core.messages import HumanMessage
from agent.models import TEST_MODEL

TEST_MODEL = "gemma-3-27b-it"

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
        "sources_gathered": []
    }

@pytest.fixture
def mock_config():
    return {"configurable": {
        "query_generator_model": "gemini-2.5-flash",
        "reflection_model": "gemini-2.5-flash",
        "answer_model": "gemini-2.5-flash"
    }}

class TestGraphNodes:

    @patch('agent.nodes.ChatGoogleGenerativeAI')
    def test_generate_query_success(self, MockLLM, mock_state, mock_config):
        # Mock LLM instance and response
        mock_instance = MockLLM.return_value
        mock_instance.with_structured_output.return_value.invoke.return_value = Mock(
            query=["query1", "query2"]
        )

        result = generate_query(mock_state, mock_config)

        assert "search_query" in result
        assert result["search_query"] == ["query1", "query2"]

    @patch('agent.nodes.search_router')
    def test_web_research_success(self, mock_router, mock_state, mock_config):
        # Mock SearchRouter response
        mock_result = Mock()
        mock_result.title = "T1"
        mock_result.url = "u1"
        mock_result.content = "c1"
        
        mock_router.search.return_value = [mock_result]

        state = mock_state.copy()
        state["search_query"] = "test query"

        result = web_research(state, mock_config)

        assert "web_research_result" in result
        # Check that it formats correctly (likely content + citation)
        assert "c1" in result["web_research_result"][0]
        assert "[T1](u1)" in result["web_research_result"][0]
        assert len(result["sources_gathered"]) > 0

    @patch('agent.nodes.ChatGoogleGenerativeAI')
    def test_reflection_sufficient(self, MockLLM, mock_state, mock_config):
        mock_instance = MockLLM.return_value
        mock_instance.with_structured_output.return_value.invoke.return_value = Mock(
            is_sufficient=True,
            knowledge_gap="None",
            follow_up_queries=[]
        )

        result = reflection(mock_state, mock_config)

        assert result["is_sufficient"] is True
        assert result["research_loop_count"] == 1

    @patch('agent.nodes.ChatGoogleGenerativeAI')
    def test_finalize_answer(self, MockLLM, mock_state, mock_config):
        mock_instance = MockLLM.return_value
        mock_instance.invoke.return_value.content = "Final Answer with url: http://short.url"

        state = mock_state.copy()
        state["sources_gathered"] = [{"short_url": "http://short.url", "value": "http://real.url"}]

        result = finalize_answer(state, mock_config)

        assert result["messages"][0].content == "Final Answer with url: http://real.url"

    @patch('agent.nodes.load_plan')
    def test_load_context_success(self, mock_load_plan, mock_state):
        mock_load_plan.return_value = {
            "todo_list": ["item1"],
            "artifacts": {"a": 1}
        }

        config = {"configurable": {"thread_id": "123"}}
        result = load_context(mock_state, config)

        assert result["todo_list"] == ["item1"]
        assert result["artifacts"] == {"a": 1}

    def test_load_context_no_thread(self, mock_state):
        config = {"configurable": {}}
        result = load_context(mock_state, config)
        assert result == {}
