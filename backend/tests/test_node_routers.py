import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from agent.nodes import continue_to_web_research  # noqa: E402


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


