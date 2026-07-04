from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from agent.nodes import flow_update
from agent.state import OverallState


@pytest.fixture
def base_state() -> OverallState:
    return {
        "query": "What is FlowSearch?",
        "plan": [
            {"id": "1", "task": "Search for FlowSearch paper", "status": "in_progress"},
            {"id": "2", "task": "Summarize findings", "status": "pending"},
        ],
        "validated_web_research_result": [
            "FlowSearch is a dynamic DAG expanding framework."
        ],
        "evidence_bank": [],
        "initial_search_query_count": 1,
        "max_research_loops": 3,
        "research_loop_count": 1,
        "reasoning_model": "test-model",
    }


@pytest.fixture
def config():
    return {"configurable": {"thread_id": "test"}}


def test_flow_update_parses_json(base_state, config):
    mock_llm = MagicMock()
    # Mock LLM returning valid JSON
    mock_response = AIMessage(
        content='```json\n{"plan": [{"id": "1", "task": "Search for FlowSearch paper", "status": "done"}, {"id": "2", "task": "Summarize findings", "status": "pending"}, {"id": "3", "task": "Analyze DAG expansion", "status": "pending"}]}\n```'
    )
    mock_llm.invoke.return_value = mock_response

    with patch("agent.nodes.get_cached_llm", return_value=mock_llm):
        with patch(
            "agent.nodes.plan_updater_instructions",
            "{current_date} {research_topic} {current_plan} {research_results}",
        ):
            updated_state = flow_update(base_state, config)

            assert "plan" in updated_state
            assert len(updated_state["plan"]) == 3
            assert updated_state["plan"][0]["status"] == "done"
            assert updated_state["plan"][2]["task"] == "Analyze DAG expansion"


@patch("agent.nodes.get_cached_llm", return_value=MagicMock())
def test_flow_update_empty_plan(mock_llm, config):
    state = {"plan": []}
    result = flow_update(state, config)
    assert result["plan"] == []


@patch("agent.nodes.get_cached_llm", return_value=MagicMock())
def test_flow_update_no_results(mock_llm, config):
    state = {"plan": [{"id": "1", "task": "Task 1", "status": "pending"}]}
    result = flow_update(state, config)
    assert len(result["plan"]) == 1
    assert result["plan"][0]["task"] == "Task 1"
