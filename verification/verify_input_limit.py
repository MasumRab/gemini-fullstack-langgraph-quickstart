
import unittest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

# Import target function
from agent.nodes import generate_plan
from agent.models import TEST_MODEL

class TestInputLimit(unittest.TestCase):
    @patch("agent.nodes.plan_writer_instructions")
    @patch("agent.nodes.get_context_manager")
    @patch("agent.nodes._get_rate_limited_llm")
    def test_generate_plan_respects_limit(self, mock_get_llm, mock_get_cm, mock_instructions):
        """
        Verify that generate_plan currently accepts large input limits.
        """
        # Setup
        mock_get_cm.return_value.truncate_to_fit.return_value = "Mock Prompt"
        mock_instructions.format.return_value = "Mock Prompt"

        # State with LARGE initial query count
        base_state = {
            "messages": [HumanMessage(content="What is quantum computing?")],
            "initial_search_query_count": 1000  # Attempt DoS
        }

        config = RunnableConfig(
            configurable={
                "model": TEST_MODEL,
                "query_generator_model": TEST_MODEL,
                "max_loops": 3,
                "num_queries": 3,
            }
        )

        # Mock LLM chain
        mock_chain = MagicMock()

        # Mock invoke response for Gemma path
        mock_response = MagicMock()
        mock_response.content = "```json\n{\"tool_calls\": []}\n```"
        mock_chain.invoke.return_value = mock_response

        # Mock structured output for Gemini path
        mock_result = MagicMock()
        mock_result.plan = []
        mock_chain.with_structured_output.return_value.invoke.return_value = mock_result

        mock_get_llm.return_value = mock_chain

        # Execute
        generate_plan(base_state, config)

        # CHECK: Did it try to format the prompt with 1000 queries?
        # We access the call args of mock_instructions.format
        if mock_instructions.format.call_args:
            call_kwargs = mock_instructions.format.call_args.kwargs
            print(f"\nCalled with number_queries: {call_kwargs.get('number_queries')}")

            # In the fixed version, this assertion should equal the CAP (10)
            self.assertEqual(call_kwargs.get("number_queries"), 10)
        else:
            self.fail("plan_writer_instructions.format was not called")

if __name__ == "__main__":
    unittest.main()
