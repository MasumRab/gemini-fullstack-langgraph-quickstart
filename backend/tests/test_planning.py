import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from agent.graph import planning_mode, planning_router, planning_wait  # noqa: E402


def make_state(**overrides):
    state = {
        "messages": [{"content": "User: research solar"}],
        "search_query": ["solar energy market outlook"],
        "planning_status": None,
        "planning_feedback": [],
    }
    state.update(overrides)
    return state


def test_planning_mode_auto_approves_without_flag():
    result = planning_mode(
        make_state(),
        config={"configurable": {"require_planning_confirmation": False}},
    )
    assert result["planning_status"] == "auto_approved"
    assert len(result["planning_steps"]) == 1


def test_planning_mode_enters_confirmation_on_plan_command():
    state = make_state(messages=[{"content": "/plan"}])
    result = planning_mode(
        state,
        config={"configurable": {"require_planning_confirmation": True}},
    )
    assert result["planning_status"] == "awaiting_confirmation"


def test_planning_mode_skips_on_end_plan():
    state = make_state(messages=[{"content": "/end_plan"}])
    result = planning_mode(
        state,
        config={"configurable": {"require_planning_confirmation": True}},
    )
    assert result["planning_steps"] == []
    assert result["planning_status"] == "auto_approved"


def test_planning_wait_emits_feedback():
    wait_state = planning_wait(make_state())
    assert "Awaiting user confirmation" in wait_state["planning_feedback"][0]


def test_planning_router_handles_plan_and_end_plan_commands():
    plan_state = make_state(messages=[{"content": "/plan"}])
    plan_result = planning_router(
        plan_state,
        config={"configurable": {"require_planning_confirmation": True}},
    )
    assert plan_result == "planning_wait"

    end_state = make_state(messages=[{"content": "/end_plan"}], search_query=["q1"])
    router_result = planning_router(
        end_state,
        config={"configurable": {"require_planning_confirmation": True}},
    )
    # Should return the same structure as continue_to_web_research (list of Send instructions)
    assert isinstance(router_result, list)
    assert router_result[0].node == "web_research"


def test_planning_router_requires_confirmation_when_flag_true():
    state = make_state(planning_status=None)
    result = planning_router(
        state,
        config={"configurable": {"require_planning_confirmation": True}},
    )
    assert result == "planning_wait"


def test_planning_router_bypasses_wait_when_confirmed():
    state = make_state(planning_status="confirmed")
    result = planning_router(
        state,
        config={"configurable": {"require_planning_confirmation": True}},
    )
    assert isinstance(result, list)
    # result[0] is a Send object. It has a .node attribute (not .name)
    assert result[0].node == "web_research"


# Additional comprehensive tests for planning nodes


def test_planning_mode_creates_plan_steps_structure():
    """Test that planning_mode creates properly structured plan steps."""
    state = make_state(search_query=["query1", "query2", "query3"])
    result = planning_mode(
        state,
        config={"configurable": {"require_planning_confirmation": False}},
    )
    
    assert len(result["planning_steps"]) == 3
    
    for idx, step in enumerate(result["planning_steps"]):
        assert "id" in step
        assert "title" in step
        assert "query" in step
        assert "suggested_tool" in step
        assert "status" in step
        assert step["id"] == f"plan-{idx}"
        assert step["suggested_tool"] == "web_research"
        assert step["status"] == "pending"


def test_planning_mode_handles_empty_search_query():
    """Test planning_mode behavior with empty search query list."""
    state = make_state(search_query=[])
    result = planning_mode(
        state,
        config={"configurable": {"require_planning_confirmation": False}},
    )
    
    assert result["planning_steps"] == []
    assert "No queries available" in " ".join(result["planning_feedback"])


def test_planning_mode_with_require_confirmation_flag():
    """Test that require_planning_confirmation flag sets correct status."""
    state = make_state()
    result = planning_mode(
        state,
        config={"configurable": {"require_planning_confirmation": True}},
    )
    
    assert result["planning_status"] == "awaiting_confirmation"


def test_planning_mode_idempotent_when_already_approved():
    """Test that planning_mode is idempotent when status is already auto_approved."""
    state = make_state(planning_status="auto_approved", search_query=[])
    result = planning_mode(
        state,
        config={"configurable": {"require_planning_confirmation": False}},
    )
    
    assert result["planning_steps"] == []
    assert "Planning skipped" in " ".join(result["planning_feedback"])


def test_planning_mode_generates_feedback_message():
    """Test that planning_mode generates appropriate feedback messages."""
    state = make_state(search_query=["query1", "query2"])
    result = planning_mode(
        state,
        config={"configurable": {"require_planning_confirmation": False}},
    )
    
    assert "planning_feedback" in result
    assert len(result["planning_feedback"]) > 0
    assert "Generated 2 plan steps" in result["planning_feedback"][0]


def test_planning_router_confirm_plan_command():
    """Test planning_router handles /confirm_plan command."""
    state = make_state(
        messages=[{"content": "/confirm_plan"}],
        search_query=["q1", "q2"]
    )
    result = planning_router(
        state,
        config={"configurable": {"require_planning_confirmation": True}},
    )
    
    # Should route to web_research
    assert isinstance(result, list)
    assert len(result) == 2  # Two queries
    assert all(item.node == "web_research" for item in result)
    # State should be updated
    assert state["planning_status"] == "confirmed"


def test_planning_router_without_confirmation_required():
    """Test planning_router when confirmation is not required."""
    state = make_state(search_query=["query1"])
    result = planning_router(
        state,
        config={"configurable": {"require_planning_confirmation": False}},
    )
    
    # Should directly route to web_research
    assert isinstance(result, list)
    assert result[0].node == "web_research"


def test_planning_router_case_insensitive_commands():
    """Test that planning_router handles commands case-insensitively."""
    state = make_state(messages=[{"content": "/PLAN"}])
    result = planning_router(
        state,
        config={"configurable": {"require_planning_confirmation": True}},
    )
    
    assert result == "planning_wait"


def test_planning_router_with_whitespace_in_command():
    """Test that planning_router handles commands with whitespace."""
    state = make_state(messages=[{"content": "  /plan  "}])
    result = planning_router(
        state,
        config={"configurable": {"require_planning_confirmation": True}},
    )
    
    assert result == "planning_wait"


def test_planning_wait_returns_feedback():
    """Test that planning_wait returns proper feedback structure."""
    state = make_state()
    result = planning_wait(state)
    
    assert "planning_feedback" in result
    assert isinstance(result["planning_feedback"], list)
    assert len(result["planning_feedback"]) > 0


def test_planning_mode_handles_string_queries():
    """Test planning_mode correctly handles string queries."""
    state = make_state(search_query=["string query"])
    result = planning_mode(
        state,
        config={"configurable": {"require_planning_confirmation": False}},
    )
    
    assert result["planning_steps"][0]["title"] == "Investigate: string query"
    assert result["planning_steps"][0]["query"] == "string query"


def test_planning_router_handles_confirmed_status_bypass():
    """Test that router bypasses wait when status is already confirmed."""
    state = make_state(
        planning_status="confirmed",
        search_query=["q1"]
    )
    result = planning_router(
        state,
        config={"configurable": {"require_planning_confirmation": True}},
    )
    
    # Should go directly to web_research, not planning_wait
    assert isinstance(result, list)
    assert result[0].node == "web_research"


def test_planning_mode_feedback_structure():
    """Test that planning feedback is properly structured as a list."""
    state = make_state()
    result = planning_mode(
        state,
        config={"configurable": {"require_planning_confirmation": False}},
    )
    
    assert isinstance(result["planning_feedback"], list)
    for feedback in result["planning_feedback"]:
        assert isinstance(feedback, str)


def test_planning_router_multiple_queries_fan_out():
    """Test that planning_router creates multiple Send objects for multiple queries."""
    state = make_state(
        planning_status="confirmed",
        search_query=["q1", "q2", "q3"]
    )
    result = planning_router(
        state,
        config={"configurable": {"require_planning_confirmation": False}},
    )
    
    assert isinstance(result, list)
    assert len(result) == 3
    for item in result:
        assert item.node == "web_research"
