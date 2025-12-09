import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from agent.nodes import planning_mode, planning_router, planning_wait  # noqa: E402


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
    assert result[0].node == "web_research"

    def test_planning_mode_with_skip_planning_status(self):
        """Test that skip_planning status auto-approves immediately."""
        state = {
            "search_query": ["query1", "query2"],
            "messages": [{"content": "test"}],
            "planning_status": "skip_planning"
        }
        config = {"configurable": {}}
        
        result = planning_mode(state, config)
        
        self.assertEqual(result["planning_status"], "auto_approved")
        self.assertIn("Planning skipped", result["planning_feedback"][0])

    def test_planning_mode_with_end_plan_command(self):
        """Test /end_plan command disables planning."""
        state = {
            "search_query": ["query1"],
            "messages": [{"content": "/end_plan"}]
        }
        config = {"configurable": {}}
        
        result = planning_mode(state, config)
        
        self.assertEqual(result["planning_status"], "auto_approved")
        self.assertIn("Planning disabled", result["planning_feedback"][0])

    def test_planning_mode_with_plan_command(self):
        """Test /plan command triggers confirmation."""
        from types import SimpleNamespace
        state = {
            "search_query": ["query1"],
            "messages": [SimpleNamespace(content="/plan")]
        }
        config = {"configurable": {}}
        
        result = planning_mode(state, config)
        
        self.assertEqual(result["planning_status"], "awaiting_confirmation")

    def test_planning_mode_creates_steps_from_queries(self):
        """Test that planning mode creates proper step objects."""
        state = {
            "search_query": ["AI fundamentals", "ML algorithms", "Deep learning"],
            "messages": [{"content": "test"}]
        }
        config = {"configurable": {}}
        
        result = planning_mode(state, config)
        
        steps = result["planning_steps"]
        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[0]["query"], "AI fundamentals")
        self.assertEqual(steps[1]["query"], "ML algorithms")
        self.assertEqual(steps[2]["query"], "Deep learning")
        self.assertEqual(steps[0]["suggested_tool"], "web_research")

    def test_planning_mode_empty_queries(self):
        """Test planning mode with no queries."""
        state = {
            "search_query": [],
            "messages": [{"content": "test"}]
        }
        config = {"configurable": {}}
        
        result = planning_mode(state, config)
        
        self.assertEqual(len(result["planning_steps"]), 0)
        self.assertIn("empty plan", result["planning_feedback"][0])

    def test_planning_mode_requires_confirmation(self):
        """Test planning mode with require_planning_confirmation."""
        from types import SimpleNamespace
        from agent.configuration import Configuration
        
        state = {
            "search_query": ["query1"],
            "messages": [{"content": "test"}]
        }
        # Create config with require_planning_confirmation=True
        configurable = SimpleNamespace(require_planning_confirmation=True)
        config = {"configurable": {}}
        
        # Mock Configuration.from_runnable_config
        import agent.nodes as nodes_module
        original_config = nodes_module.Configuration.from_runnable_config
        nodes_module.Configuration.from_runnable_config = lambda x: configurable
        
        try:
            result = planning_mode(state, config)
            self.assertEqual(result.get("planning_status", "auto_approved"), "awaiting_confirmation")
        finally:
            nodes_module.Configuration.from_runnable_config = original_config

    def test_planning_wait_returns_feedback(self):
        """Test that planning_wait returns appropriate feedback."""
        state = {"planning_status": "awaiting_confirmation"}
        
        result = planning_wait(state)
        
        self.assertIn("planning_feedback", result)
        self.assertIn("Awaiting user confirmation", result["planning_feedback"][0])

    def test_planning_router_with_plan_command(self):
        """Test planning_router directs to planning_wait on /plan."""
        state = {
            "search_query": ["query1"],
            "messages": [{"content": "/plan"}]
        }
        config = {"configurable": {}}
        
        result = planning_router(state, config)
        
        self.assertEqual(result, "planning_wait")

    def test_planning_router_with_end_plan_command(self):
        """Test planning_router continues to research on /end_plan."""
        state = {
            "search_query": ["query1", "query2"],
            "messages": [{"content": "/end_plan"}]
        }
        config = {"configurable": {}}
        
        result = planning_router(state, config)
        
        # Should return list of Send objects
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

    def test_planning_router_with_confirm_plan_command(self):
        """Test planning_router continues to research on /confirm_plan."""
        state = {
            "search_query": ["query1"],
            "messages": [{"content": "/confirm_plan"}]
        }
        config = {"configurable": {}}
        
        result = planning_router(state, config)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

    def test_planning_router_auto_approved(self):
        """Test planning_router with auto-approved status."""
        state = {
            "search_query": ["query1"],
            "messages": [{"content": "regular message"}],
            "planning_status": "confirmed"
        }
        config = {"configurable": {}}
        
        result = planning_router(state, config)
        
        self.assertIsInstance(result, list)

    def test_flatten_queries_flat_list(self):
        """Test _flatten_queries with already flat list."""
        from agent.nodes import _flatten_queries
        queries = ["query1", "query2", "query3"]
        result = _flatten_queries(queries)
        self.assertEqual(result, ["query1", "query2", "query3"])

    def test_flatten_queries_nested_list(self):
        """Test _flatten_queries with nested lists."""
        from agent.nodes import _flatten_queries
        queries = ["query1", ["query2", "query3"], "query4"]
        result = _flatten_queries(queries)
        self.assertEqual(result, ["query1", "query2", "query3", "query4"])

    def test_flatten_queries_deeply_nested(self):
        """Test _flatten_queries with deeply nested structure."""
        from agent.nodes import _flatten_queries
        queries = ["q1", ["q2", ["q3", "q4"]], "q5"]
        result = _flatten_queries(queries)
        self.assertEqual(result, ["q1", "q2", "q3", "q4", "q5"])

    def test_flatten_queries_empty_list(self):
        """Test _flatten_queries with empty list."""
        from agent.nodes import _flatten_queries
        result = _flatten_queries([])
        self.assertEqual(result, [])

    def test_keywords_from_queries_basic(self):
        """Test _keywords_from_queries extracts words >= 4 chars."""
        from agent.nodes import _keywords_from_queries
        queries = ["artificial intelligence", "machine learning"]
        result = _keywords_from_queries(queries)
        self.assertIn("artificial", result)
        self.assertIn("intelligence", result)
        self.assertIn("machine", result)
        self.assertIn("learning", result)

    def test_keywords_from_queries_filters_short_words(self):
        """Test that words < 4 chars are filtered out."""
        from agent.nodes import _keywords_from_queries
        queries = ["a big cat ran"]
        result = _keywords_from_queries(queries)
        # Only "big" and "cat" and "ran" should be excluded (< 4 chars)
        self.assertNotIn("big", result)
        self.assertNotIn("cat", result)
        self.assertNotIn("ran", result)

    def test_keywords_from_queries_case_insensitive(self):
        """Test that keywords are lowercased."""
        from agent.nodes import _keywords_from_queries
        queries = ["Python Programming"]
        result = _keywords_from_queries(queries)
        self.assertIn("python", result)
        self.assertIn("programming", result)

    def test_keywords_from_queries_special_characters(self):
        """Test keyword extraction with special characters."""
        from agent.nodes import _keywords_from_queries
        queries = ["C++ programming, Python & Java"]
        result = _keywords_from_queries(queries)
        self.assertIn("programming", result)
        self.assertIn("python", result)
        self.assertIn("java", result)

    def test_keywords_from_queries_empty(self):
        """Test with empty queries list."""
        from agent.nodes import _keywords_from_queries
        result = _keywords_from_queries([])
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
