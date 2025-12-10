import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from agent.nodes import continue_to_web_research, evaluate_research  # noqa: E402


# Tests for continue_to_web_research
def test_continue_to_web_research_single_query():
    """Test routing a single search query to web research."""
    state = {
        "search_query": ["single query"]
    }

    result = continue_to_web_research(state)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].node == "web_research"
    assert result[0].arg["search_query"] == "single query"
    assert result[0].arg["id"] == 0


def test_continue_to_web_research_multiple_queries():
    """Test routing multiple search queries to web research."""
    state = {
        "search_query": ["query1", "query2", "query3"]
    }

    result = continue_to_web_research(state)

    assert isinstance(result, list)
    assert len(result) == 3

    for idx, send_obj in enumerate(result):
        assert send_obj.node == "web_research"
        assert send_obj.arg["search_query"] == f"query{idx + 1}"
        assert send_obj.arg["id"] == idx


def test_continue_to_web_research_empty_queries():
    """Test behavior with empty query list."""
    state = {
        "search_query": []
    }

    result = continue_to_web_research(state)

    assert isinstance(result, list)
    assert len(result) == 0


def test_continue_to_web_research_preserves_query_order():
    """Test that query order is preserved in Send objects."""
    state = {
        "search_query": ["first", "second", "third"]
    }

    result = continue_to_web_research(state)

    assert result[0].arg["search_query"] == "first"
    assert result[1].arg["search_query"] == "second"
    assert result[2].arg["search_query"] == "third"


def test_continue_to_web_research_ids_increment():
    """Test that IDs increment correctly."""
    state = {
        "search_query": ["q1", "q2", "q3", "q4", "q5"]
    }

    result = continue_to_web_research(state)

    for idx, send_obj in enumerate(result):
        assert send_obj.arg["id"] == idx


# Tests for evaluate_research
def test_evaluate_research_sufficient_knowledge():
    """Test routing to finalize_answer when knowledge is sufficient."""
    state = {
        "is_sufficient": True,
        "research_loop_count": 1,
        "max_research_loops": 5,
        "follow_up_queries": ["query1"]
    }
    config = {"configurable": {}}

    result = evaluate_research(state, config)

    assert result == "finalize_answer"


def test_evaluate_research_max_loops_reached():
    """Test routing to finalize_answer when max loops reached."""
    state = {
        "is_sufficient": False,
        "research_loop_count": 5,
        "max_research_loops": 5,
        "follow_up_queries": ["query1"]
    }
    config = {"configurable": {}}

    result = evaluate_research(state, config)

    assert result == "finalize_answer"


def test_evaluate_research_continues_with_follow_ups():
    """Test continuing research with follow-up queries."""
    state = {
        "is_sufficient": False,
        "research_loop_count": 2,
        "max_research_loops": 5,
        "follow_up_queries": ["follow_up1", "follow_up2"],
        "number_of_ran_queries": 3
    }
    config = {"configurable": {}}

    result = evaluate_research(state, config)

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(item.node == "web_research" for item in result)


def test_evaluate_research_follow_up_query_ids():
    """Test that follow-up queries get correct IDs."""
    state = {
        "is_sufficient": False,
        "research_loop_count": 1,
        "max_research_loops": 5,
        "follow_up_queries": ["q1", "q2", "q3"],
        "number_of_ran_queries": 5
    }
    config = {"configurable": {}}

    result = evaluate_research(state, config)

    assert result[0].arg["id"] == 5
    assert result[1].arg["id"] == 6
    assert result[2].arg["id"] == 7


def test_evaluate_research_uses_state_max_loops():
    """Test that state max_research_loops takes precedence."""
    state = {
        "is_sufficient": False,
        "research_loop_count": 3,
        "max_research_loops": 3,  # From state
        "follow_up_queries": ["query"]
    }
    config = {
        "configurable": {
            "max_research_loops": 10  # Config value should be ignored
        }
    }

    result = evaluate_research(state, config)

    # Should finalize because state's max_research_loops is reached
    assert result == "finalize_answer"


def test_evaluate_research_uses_config_when_state_missing():
    """Test that config is used when state doesn't have max_research_loops."""
    state = {
        "is_sufficient": False,
        "research_loop_count": 1,
        # max_research_loops not in state
        "follow_up_queries": ["query"],
        "number_of_ran_queries": 1
    }
    config = {
        "configurable": {
            "max_research_loops": 2
        }
    }

    result = evaluate_research(state, config)

    # Should continue because loop count (1) < config max (2)
    assert isinstance(result, list)


def test_evaluate_research_empty_follow_up_queries():
    """Test behavior when follow-up queries list is empty."""
    state = {
        "is_sufficient": False,
        "research_loop_count": 1,
        "max_research_loops": 5,
        "follow_up_queries": [],
        "number_of_ran_queries": 2
    }
    config = {"configurable": {}}

    result = evaluate_research(state, config)

    assert isinstance(result, list)
    assert len(result) == 0


def test_evaluate_research_single_follow_up():
    """Test evaluation with single follow-up query."""
    state = {
        "is_sufficient": False,
        "research_loop_count": 1,
        "max_research_loops": 3,
        "follow_up_queries": ["single_follow_up"],
        "number_of_ran_queries": 1
    }
    config = {"configurable": {}}

    result = evaluate_research(state, config)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].arg["search_query"] == "single_follow_up"


def test_evaluate_research_boundary_condition():
    """Test boundary condition where loop count equals max loops."""
    state = {
        "is_sufficient": False,
        "research_loop_count": 5,
        "max_research_loops": 5,
        "follow_up_queries": ["query"],
        "number_of_ran_queries": 10
    }
    config = {"configurable": {}}

    result = evaluate_research(state, config)

    # Should finalize at boundary
    assert result == "finalize_answer"


def test_evaluate_research_one_below_max():
    """Test that research continues when one loop below max."""
    state = {
        "is_sufficient": False,
        "research_loop_count": 4,
        "max_research_loops": 5,
        "follow_up_queries": ["query"],
        "number_of_ran_queries": 8
    }
    config = {"configurable": {}}

    result = evaluate_research(state, config)

    # Should continue
    assert isinstance(result, list)
    assert len(result) == 1