import pytest
import typing
import json
from pathlib import Path
from agent.state import OverallState, Todo
from agent import persistence
from agent import mcp_persistence
from agent import memory_tools

# We decided not to change `planning_steps` because it's a scratch/telemetry field
# populated at backend/src/agent/nodes.py:238 from a persisted payload, not a Todo collection.

def test_overallstate_todo_list_type_hint():
    """
    1. `typing.get_type_hints(OverallState)["todo_list"]`: assert it is optional,
    that its list argument's origin is `list`, and that its single argument is `agent.state.Todo`.
    """
    hints = typing.get_type_hints(OverallState)
    todo_list_hint = hints["todo_list"]
    
    # Optional[List[Todo]] is Union[List[Todo], NoneType]
    assert typing.get_origin(todo_list_hint) is typing.Union
    
    # The first arg of Union should be List[Todo]
    args = typing.get_args(todo_list_hint)
    list_arg = args[0]
    
    assert typing.get_origin(list_arg) is list
    list_args = typing.get_args(list_arg)
    assert len(list_args) == 1
    assert list_args[0] is Todo


def test_persistence_round_trip(tmp_path, monkeypatch):
    """
    2. `persistence.save_plan` / `load_plan` JSON round-trip of a canonical `Todo`,
    with `persistence.PLAN_DIR` monkeypatched to `tmp_path`.
    """
    monkeypatch.setattr(persistence, "PLAN_DIR", str(tmp_path))
    
    thread_id = "test-thread-1"
    todo_list = [{"id": "1", "task": "do thing", "status": "pending", "result": None}]
    artifacts = {"doc1": {"content": "hello"}}
    
    persistence.save_plan(thread_id, todo_list, artifacts)
    
    loaded = persistence.load_plan(thread_id)
    assert loaded is not None
    assert loaded["todo_list"] == todo_list
    assert loaded["artifacts"] == artifacts


def test_mcp_persistence_round_trip(tmp_path, monkeypatch):
    """
    3. `mcp_persistence.save_thread_plan` / `load_thread_plan` round-trip preserves the `Todo`.
    """
    monkeypatch.setattr(persistence, "PLAN_DIR", str(tmp_path))
    
    thread_id = "test-thread-2"
    todo_list = [{"id": "2", "task": "do thing 2", "status": "done", "result": "success"}]
    artifacts = {}
    
    result = mcp_persistence.save_thread_plan(thread_id, todo_list, artifacts)
    assert "successfully" in result
    
    loaded = mcp_persistence.load_thread_plan(thread_id)
    assert loaded is not None
    assert loaded["todo_list"] == todo_list


def test_memory_tools_round_trip(tmp_path, monkeypatch):
    """
    4. `memory_tools.save_plan_tool` reports success and `load_plan_tool` returns the payload.
    """
    monkeypatch.setattr(persistence, "PLAN_DIR", str(tmp_path))
    
    thread_id = "test-thread-3"
    todo_list = [{"id": "3", "task": "do thing 3", "status": "pending", "result": None}]
    artifacts = {}
    
    save_result = memory_tools.save_plan_tool.invoke({"thread_id": thread_id, "todo_list": todo_list, "artifacts": artifacts})
    assert "successfully" in save_result.lower()
    
    load_result = memory_tools.load_plan_tool.invoke({"thread_id": thread_id})
    assert "Plan loaded" in load_result
    assert "do thing 3" in load_result


def test_canonical_todo_shape():
    """
    5. A canonical-shape test asserting the `Todo` keys are `id`/`task`/`status`/`result`,
    with a note that `agent.tools_and_schemas.Todo` is a different model.
    """
    # agent.state.Todo TypedDict
    annotations = Todo.__annotations__
    expected_keys = {"id", "task", "status", "result"}
    assert set(annotations.keys()) == expected_keys
    
    # We explicitly import agent.tools_and_schemas.Todo here just for the check
    import agent.tools_and_schemas
    other_todo = agent.tools_and_schemas.Todo
    
    # Assert they are not the same
    assert other_todo is not Todo
    assert "title" in other_todo.model_fields
    assert "description" in other_todo.model_fields


def test_legacy_partial_state_serialization(tmp_path, monkeypatch):
    """
    6. A regression test that a legacy partial state `{"todo_list": [...]}` still serializes,
    so the existing `test_state_types.py::test_backward_compatibility_partial` keeps passing.
    """
    monkeypatch.setattr(persistence, "PLAN_DIR", str(tmp_path))
    
    thread_id = "test-thread-legacy"
    legacy_todo_list = [{"task": "old shape task", "status": "pending"}]
    
    # persistence layer should still accept this dict shape just fine,
    # as types are only enforced statically by pyright/mypy, and `Todo` is TypedDict total=False
    persistence.save_plan(thread_id, legacy_todo_list, {})
    
    loaded = persistence.load_plan(thread_id)
    assert loaded["todo_list"] == legacy_todo_list

