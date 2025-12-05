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
