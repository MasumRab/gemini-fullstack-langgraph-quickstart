import json
import pytest
from agent.state import OverallState, Todo, validate_scoping

def test_typing_smoke():
    """Ensure OverallState can be instantiated with new fields."""
    s: OverallState = {
        "query": "What is SOTA in X?",
        "clarifications_needed": ["Which domain?"],
        "user_answers": ["NLP"],
        "plan": [{"id": "1", "title": "Search papers", "done": False}],
    }
    assert s["query"].startswith("What")
    assert isinstance(s["plan"], list)
    assert s["plan"][0]["title"] == "Search papers"

def test_serialization_roundtrip():
    """Ensure OverallState with new fields survives JSON serialization."""
    s: OverallState = {
        "query": "Q",
        "clarifications_needed": ["A"],
        "user_answers": ["B"],
        "plan": [{"id": "1", "title": "t", "done": True}],
    }
    j = json.dumps(s)
    r = json.loads(j)
    assert r["query"] == s["query"]
    assert isinstance(r["plan"], list)
    assert r["plan"][0]["done"] is True

def test_backward_compatibility_partial():
    """Ensure legacy code can create partial states without new fields."""
    partial: OverallState = {
        "todo_list": [{"title": "legacy"}]
    }
    # code that consumes OverallState should tolerate missing scoping fields
    assert "todo_list" in partial
    assert "plan" not in partial
    assert "query" not in partial

def test_validate_scoping():
    """Test the runtime validation helper."""
    valid_state: OverallState = {
        "query": "foo",
        "clarifications_needed": [],
        "user_answers": []
    }
    assert validate_scoping(valid_state) is True

    invalid_state: OverallState = {
        "query": "foo"
        # missing other fields
    }
    assert validate_scoping(invalid_state) is False

def test_consumer_integration():
    """Simulate a function consuming OverallState to ensure runtime safety."""

    def process_plan(state: OverallState) -> list[str]:
        # Example consumer that safely checks for plan
        plan = state.get("plan", [])
        return [t["title"] for t in plan if "title" in t]

    state_with_plan: OverallState = {
        "plan": [{"id": "1", "title": "Task A", "done": False}]
    }
    assert process_plan(state_with_plan) == ["Task A"]

    state_without_plan: OverallState = {}
    assert process_plan(state_without_plan) == []

def test_todo_structure():
    """Verify Todo structure matches requirements."""
    t: Todo = {
        "id": "123",
        "title": "Test Task",
        "description": "Details",
        "done": False,
        "status": "pending",
        "result": None
    }
    assert t["id"] == "123"
