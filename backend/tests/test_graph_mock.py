import pytest
from unittest.mock import Mock, patch
from agent.nodes import generate_query, web_research, reflection, finalize_answer, load_context
from langchain_core.messages import HumanMessage
from agent.models import TEST_MODEL

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
    """Fixture for test configuration."""
    return {
        "configurable": {
            "thread_id": "test-thread",
            "checkpoint_ns": "",
            "checkpoint_id": "",
        },
        "query_generator_model": TEST_MODEL,
        "reflection_model": TEST_MODEL,
        "answer_model": TEST_MODEL
    }

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
    def test_web_research_google_success(self, mock_search_router, mock_state, mock_config):
        # Mock SearchRouter response
        mock_result = Mock()
        mock_result.title = "Search content"
        mock_result.url = "http://google.com"
        mock_result.content = "Search content"
        mock_result.raw_content = None

        mock_search_router.search.return_value = [mock_result]

        state = mock_state.copy()
        state["search_query"] = "test query"

        result = web_research(state, mock_config)

        assert "web_research_result" in result
        assert "Search content [Search content](http://google.com)" in result["web_research_result"][0]

    @patch('agent.nodes.search_router')
    def test_web_research_tavily_success(self, mock_search_router, mock_state, mock_config):
        # Mock SearchRouter response to simulate Tavily-like results
        r1 = Mock(title="T1", url="u1", content="c1", raw_content=None)
        r2 = Mock(title="T2", url="u2", content="c2", raw_content=None)

        mock_search_router.search.return_value = [r1, r2]

        state = mock_state.copy()
        state["search_query"] = "test query"

        result = web_research(state, mock_config)

        assert len(result["web_research_result"]) > 0
        assert "c1 [T1](u1)" in result["web_research_result"][0]

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
