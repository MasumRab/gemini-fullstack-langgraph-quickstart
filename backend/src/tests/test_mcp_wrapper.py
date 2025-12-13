import os
import shutil
import pytest
from agent.mcp_persistence import save_thread_plan, load_thread_plan

TEST_THREAD_ID = "test_mcp_thread_123"

@pytest.fixture(autouse=True)
def cleanup():
    # Setup: Ensure clean state
    """
    Ensure the test plan file for TEST_THREAD_ID is removed before and after tests to provide isolation.
    
    Removes plans/<TEST_THREAD_ID>.json if it exists during setup and again during teardown. Intended for use as a pytest fixture to prevent leftover test artifacts in the plans directory.
    """
    if os.path.exists("plans"):
        # We don't want to delete the whole plans dir if it has other stuff,
        # but for test isolation let's just delete the specific file.
        path = f"plans/{TEST_THREAD_ID}.json"
        if os.path.exists(path):
            os.remove(path)

    yield

    # Teardown
    path = f"plans/{TEST_THREAD_ID}.json"
    if os.path.exists(path):
        os.remove(path)

def test_save_and_load_via_mcp():
    todo_list = [{"id": 1, "task": "test task", "status": "pending"}]
    artifacts = {"doc1": "content"}

    # Test Save
    result = save_thread_plan(TEST_THREAD_ID, todo_list, artifacts)
    assert f"Plan saved successfully for thread {TEST_THREAD_ID}" in result

    # Test Load
    loaded = load_thread_plan(TEST_THREAD_ID)
    assert loaded is not None
    assert loaded["todo_list"] == todo_list
    assert loaded["artifacts"] == artifacts

def test_tools_exposure():
    from agent.tools_and_schemas import get_mcp_tools

    tools = get_mcp_tools()
    assert len(tools) >= 2
    names = [t.name for t in tools]
    assert "load_thread_plan" in names
    assert "save_thread_plan" in names