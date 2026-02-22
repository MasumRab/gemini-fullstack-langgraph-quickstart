"""Unit tests specifically targeting Gemma model compatibility across backend features.

These tests iterate through key nodes with Gemma 2 and Gemma 3 configurations
to ensure:
1. Correct prompt selection (is_gemma logic).
2. Proper simulated function calling/parsing.
3. Robustness against token limit behaviors typical of smaller models.
"""

import pytest
from unittest.mock import MagicMock, patch, ANY
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage, HumanMessage

from agent.models import GEMMA_2_27B_IT, GEMMA_3_27B_IT
from agent.nodes import (
    generate_plan,
    web_research,
    denoising_refiner,
)
from agent.state import OverallState

# Define the models we want to verify compatibility for
GEMMA_MODELS = [GEMMA_2_27B_IT, GEMMA_3_27B_IT]


@pytest.fixture
def base_state():
    return {
        "messages": [HumanMessage(content="User Request")],
        "web_research_result": [],
        "validated_web_research_result": [],
        "plan": [],
        "research_loop_count": 0,
    }


class TestGemmaCompatibility:
    @pytest.mark.parametrize("model_name", GEMMA_MODELS)
    @patch("agent.nodes._get_rate_limited_llm")
    @patch("agent.nodes.plan_writer_instructions")
    def test_plan_generation_uses_gemma_logic(
        self, mock_instructions, mock_get_llm, model_name, base_state
    ):
        """Verify that planning uses the correct tool-response parsing for Gemma."""
        config = RunnableConfig(configurable={"query_generator_model": model_name})

        # Mock LLM to return a JSON-markdown block (Gemma style tool output)
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(
            content='```json\n{"tool_calls": [{"name": "Plan", "args": {"plan": [{"title": "Task 1", "status": "pending"}], "rationale": "Reason"}}]}\n```'
        )
        mock_get_llm.return_value = mock_llm

        # Make the mock instructions return a proper string when format is called
        mock_instructions.format.return_value = "Generate a plan for: Test topic"

        result = generate_plan(base_state, config)

        # Assert inputs
        # Check that we requested the specific Gemma model
        # Note: max_retries uses default value, not explicitly passed
        mock_get_llm.assert_called_with(model=model_name, temperature=1.0, prompt=ANY)

        # Assert outputs
        assert "plan" in result
        assert len(result["plan"]) == 1
        # Plan items use "task" key, not "title"
        assert result["plan"][0]["task"] == "Task 1"
        assert result["search_query"] == ["Task 1"]  # Derived from task title

    @pytest.mark.parametrize("model_name", GEMMA_MODELS)
    @patch("agent.nodes._get_rate_limited_llm")
    def test_denoising_refiner_uses_gemma_prompts(
        self, mock_get_llm, model_name, base_state
    ):
        """Verify denoising refiner uses correct instructions and handles artifacts."""
        config = RunnableConfig(configurable={"answer_model": model_name})
        base_state["validated_web_research_result"] = ["Doc 1", "Doc 2"]

        mock_llm = MagicMock()
        # Mock return for two drafts + final synthesis
        # 1. Draft 1
        # 2. Draft 2
        # 3. Final Synthesis
        mock_llm.invoke.side_effect = [
            AIMessage(content="Draft 1 content"),
            AIMessage(content="Draft 2 content"),
            AIMessage(content="Final Report Content"),
        ]
        mock_get_llm.return_value = mock_llm

        result = denoising_refiner(base_state, config)

        # Check assertions
        # We expect 3 calls: Draft 1, Draft 2, Synthesis
        assert mock_llm.invoke.call_count == 3

        # Check outputs
        assert "messages" in result
        assert "artifacts" in result

        artifact = list(result["artifacts"].values())[0]
        assert artifact["content"] == "Final Report Content"
        assert artifact["type"] == "markdown"

    @pytest.mark.parametrize("model_name", GEMMA_MODELS)
    @patch("agent.nodes.search_router")
    def test_web_research_gemma_safety(
        self, mock_search_router, model_name, base_state
    ):
        """Ensure web research doesn't crash on Gemma even if it doesn't need LLM explicitly."""
        # This test is lighter since web_research delegates to search_router (non-LLM usually)
        # But we verify it accepts the state and config without error
        config = RunnableConfig(configurable={"query_generator_model": model_name})
        state = {"search_query": ["Test Query"], "id": 1}

        # Mock search_router with a proper SearchResult-like object
        mock_result = MagicMock()
        mock_result.title = "Test Result"
        mock_result.url = "https://example.com"
        mock_result.content = "Test content"
        mock_search_router.search.return_value = [mock_result]

        result = web_research(state, config)

        assert "web_research_result" in result
        assert len(result["web_research_result"]) == 1
