"""Regression tests for the input fan-out caps in ``agent.nodes``.

An attacker could previously supply an arbitrary ``initial_search_query_count``
or ``max_research_loops`` in the request state and force the agent to generate
thousands of queries or loop indefinitely (DoS amplification).
"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from agent.models import TEST_MODEL
from agent.nodes import evaluate_research, generate_plan


class TestInputLimit:
    @patch("agent.nodes.plan_writer_instructions")
    @patch("agent.nodes.get_context_manager")
    @patch("agent.nodes._get_rate_limited_llm")
    def test_generate_plan_clamps_query_count(
        self, mock_get_llm, mock_get_cm, mock_instructions
    ):
        """A request asking for 1000 queries is clamped before the prompt is built."""
        mock_get_cm.return_value.truncate_to_fit.return_value = "Mock Prompt"
        mock_instructions.format.return_value = "Mock Prompt"

        base_state = {
            "messages": [HumanMessage(content="What is quantum computing?")],
            "initial_search_query_count": 1000,
        }
        config = RunnableConfig(
            configurable={
                "model": TEST_MODEL,
                "query_generator_model": TEST_MODEL,
                "max_loops": 3,
                "num_queries": 3,
            }
        )

        mock_chain = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '```json\n{"tool_calls": []}\n```'
        mock_chain.invoke.return_value = mock_response
        mock_result = MagicMock()
        mock_result.plan = []
        mock_chain.with_structured_output.return_value.invoke.return_value = mock_result
        mock_get_llm.return_value = mock_chain

        generate_plan(base_state, config)

        if not mock_instructions.format.call_args:
            pytest.fail("plan_writer_instructions.format was not called")
        call_kwargs = mock_instructions.format.call_args.kwargs
        assert call_kwargs.get("number_queries") == 10


class TestLoopLimit:
    def test_evaluate_research_clamps_loop_count(self):
        """A request asking for 1000 loops fails over to finalize at the cap."""
        state = {"research_loop_count": 6, "max_research_loops": 1000}

        assert evaluate_research(state) == "finalize_answer"
