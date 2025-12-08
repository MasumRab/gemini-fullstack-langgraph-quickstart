"""Unit tests for planning mode functions.

Tests cover planning_mode, planning_router, and planning_wait with various
state configurations and flags.
"""
import pytest
from agent.nodes import planning_mode, planning_router, planning_wait


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def base_planning_state():
    """Base state for planning tests."""
    return {
        "messages": [{"content": "User: research solar energy"}],
        "search_query": ["solar energy market outlook"],
        "planning_status": None,
        "planning_feedback": [],
    }


@pytest.fixture
def no_confirmation_config():
    """Config that does not require planning confirmation."""
    return {"configurable": {"require_planning_confirmation": False}}


@pytest.fixture
def confirmation_required_config():
    """Config that requires planning confirmation."""
    return {"configurable": {"require_planning_confirmation": True}}


# =============================================================================
# Tests for planning_mode
# =============================================================================

class TestPlanningMode:
    """Tests for the planning_mode function."""

    def test_auto_approves_without_confirmation_flag(self, base_planning_state, no_confirmation_config):
        """Should auto-approve when require_planning_confirmation is False."""
        result = planning_mode(base_planning_state, config=no_confirmation_config)
        
        assert result["planning_status"] == "auto_approved"
        assert len(result["planning_steps"]) == 1

    def test_creates_plan_steps_from_queries(self, base_planning_state, no_confirmation_config):
        """Should create plan steps from search queries."""
        base_planning_state["search_query"] = ["query1", "query2", "query3"]
        
        result = planning_mode(base_planning_state, config=no_confirmation_config)
        
        assert len(result["planning_steps"]) == 3
        assert result["planning_steps"][0]["query"] == "query1"
        assert result["planning_steps"][1]["query"] == "query2"

    def test_enters_confirmation_on_plan_command(self, base_planning_state, confirmation_required_config):
        """Should enter awaiting_confirmation when /plan command is used."""
        base_planning_state["messages"] = [{"content": "/plan"}]
        
        result = planning_mode(base_planning_state, config=confirmation_required_config)
        
        assert result["planning_status"] == "awaiting_confirmation"

    def test_skips_planning_on_end_plan_command(self, base_planning_state, confirmation_required_config):
        """Should skip planning entirely with /end_plan command."""
        base_planning_state["messages"] = [{"content": "/end_plan"}]
        
        result = planning_mode(base_planning_state, config=confirmation_required_config)
        
        assert result["planning_steps"] == []
        assert result["planning_status"] == "auto_approved"

    def test_plan_command_case_insensitive(self, base_planning_state, confirmation_required_config):
        """Plan commands should be case-insensitive."""
        base_planning_state["messages"] = [{"content": "/PLAN"}]
        
        result = planning_mode(base_planning_state, config=confirmation_required_config)
        
        assert result["planning_status"] == "awaiting_confirmation"

    def test_empty_queries_produces_empty_plan(self, base_planning_state, no_confirmation_config):
        """Empty search queries should produce empty plan steps."""
        base_planning_state["search_query"] = []
        
        result = planning_mode(base_planning_state, config=no_confirmation_config)
        
        assert result["planning_steps"] == []
        assert "empty plan" in " ".join(result["planning_feedback"]).lower()

    def test_generates_feedback_message(self, base_planning_state, no_confirmation_config):
        """Should generate feedback about the number of steps."""
        base_planning_state["search_query"] = ["q1", "q2"]
        
        result = planning_mode(base_planning_state, config=no_confirmation_config)
        
        assert any("2 plan steps" in fb for fb in result["planning_feedback"])

    def test_plan_step_structure(self, base_planning_state, no_confirmation_config):
        """Plan steps should have required fields."""
        result = planning_mode(base_planning_state, config=no_confirmation_config)
        
        step = result["planning_steps"][0]
        assert "id" in step
        assert "title" in step
        assert "query" in step
        assert "suggested_tool" in step
        assert "status" in step
        assert step["suggested_tool"] == "web_research"
        assert step["status"] == "pending"


# =============================================================================
# Tests for planning_wait
# =============================================================================

class TestPlanningWait:
    """Tests for the planning_wait function."""

    def test_emits_awaiting_feedback(self, base_planning_state):
        """Should emit feedback indicating awaiting confirmation."""
        result = planning_wait(base_planning_state)
        
        assert len(result["planning_feedback"]) == 1
        assert "Awaiting user confirmation" in result["planning_feedback"][0]

    def test_feedback_contains_instructions(self, base_planning_state):
        """Feedback should contain instructions for the user."""
        result = planning_wait(base_planning_state)
        
        feedback = result["planning_feedback"][0]
        assert "confirmed" in feedback.lower()


# =============================================================================
# Tests for planning_router
# =============================================================================

class TestPlanningRouter:
    """Tests for the planning_router function."""

    def test_routes_to_wait_on_plan_command(self, base_planning_state, confirmation_required_config):
        """Should route to planning_wait when /plan command is used."""
        base_planning_state["messages"] = [{"content": "/plan"}]
        
        result = planning_router(base_planning_state, config=confirmation_required_config)
        
        assert result == "planning_wait"

    def test_routes_to_web_research_on_end_plan(self, base_planning_state, confirmation_required_config):
        """Should route to web_research when /end_plan is used."""
        base_planning_state["messages"] = [{"content": "/end_plan"}]
        base_planning_state["search_query"] = ["query1"]
        
        result = planning_router(base_planning_state, config=confirmation_required_config)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0].node == "web_research"

    def test_routes_to_web_research_on_confirm_plan(self, base_planning_state, confirmation_required_config):
        """Should route to web_research when /confirm_plan is used."""
        base_planning_state["messages"] = [{"content": "/confirm_plan"}]
        base_planning_state["search_query"] = ["query1"]
        
        result = planning_router(base_planning_state, config=confirmation_required_config)
        
        assert isinstance(result, list)
        assert result[0].node == "web_research"

    def test_requires_confirmation_when_flag_true_and_not_confirmed(self, base_planning_state, confirmation_required_config):
        """Should wait when confirmation is required and not yet confirmed."""
        base_planning_state["planning_status"] = None
        
        result = planning_router(base_planning_state, config=confirmation_required_config)
        
        assert result == "planning_wait"

    def test_bypasses_wait_when_confirmed(self, base_planning_state, confirmation_required_config):
        """Should proceed to web_research when planning_status is 'confirmed'."""
        base_planning_state["planning_status"] = "confirmed"
        base_planning_state["search_query"] = ["query1"]
        
        result = planning_router(base_planning_state, config=confirmation_required_config)
        
        assert isinstance(result, list)
        assert result[0].node == "web_research"

    def test_bypasses_wait_when_flag_false(self, base_planning_state, no_confirmation_config):
        """Should proceed directly when require_planning_confirmation is False."""
        base_planning_state["search_query"] = ["query1"]
        
        result = planning_router(base_planning_state, config=no_confirmation_config)
        
        assert isinstance(result, list)
        assert result[0].node == "web_research"

    def test_handles_empty_search_query(self, base_planning_state, no_confirmation_config):
        """Should handle empty search_query gracefully."""
        base_planning_state["search_query"] = []
        
        result = planning_router(base_planning_state, config=no_confirmation_config)
        
        # Should return empty list, not crash
        assert isinstance(result, list)
        assert len(result) == 0

    def test_handles_missing_search_query(self, confirmation_required_config):
        """Should handle missing search_query gracefully."""
        state = {
            "messages": [{"content": "/end_plan"}],
            "planning_status": "confirmed",
        }
        
        result = planning_router(state, config=confirmation_required_config)
        
        assert isinstance(result, list)
        assert len(result) == 0

    def test_multiple_queries_create_multiple_sends(self, base_planning_state, no_confirmation_config):
        """Should create a Send for each query."""
        base_planning_state["search_query"] = ["q1", "q2", "q3"]
        
        result = planning_router(base_planning_state, config=no_confirmation_config)
        
        assert len(result) == 3
        for send in result:
            assert send.node == "web_research"
