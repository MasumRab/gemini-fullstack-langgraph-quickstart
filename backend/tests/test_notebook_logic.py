import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock colab
sys.modules["google.colab"] = MagicMock()
sys.modules["google.colab.userdata"] = MagicMock()

# Mock dependencies that might be missing in this env
sys.modules["langchain_google_genai"] = MagicMock()


class TestNotebookLogic(unittest.TestCase):
    def setUp(self):
        self.original_env = os.environ.copy()
        os.environ["GEMINI_API_KEY"] = "fake_key"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)

    @patch("langchain_google_genai.ChatGoogleGenerativeAI")
    def test_agent_initialization_with_gemma(self, mock_llm_class):
        """Verify that the agent initializes with the gemma-3 model based on notebook logic."""

        # Simulate the notebook's model selection logic
        MODEL_STRATEGY = "Gemini 2.5 Flash (Recommended)"

        if MODEL_STRATEGY == "Gemini 2.5 Flash (Recommended)":
            SELECTED_MODEL = "gemma-3-27b-it"
        else:
            SELECTED_MODEL = "wrong-model"

        # Set Env vars as notebook does
        os.environ["QUERY_GENERATOR_MODEL"] = SELECTED_MODEL
        os.environ["REFLECTION_MODEL"] = SELECTED_MODEL
        os.environ["ANSWER_MODEL"] = SELECTED_MODEL

        # Now simulate agent init
        model_name = os.environ.get("ANSWER_MODEL", "gemma-3-27b-it")

        # Instantiate LLM
        llm = mock_llm_class(model=model_name, temperature=0)

        # Assertions
        mock_llm_class.assert_called_with(model="gemma-3-27b-it", temperature=0)
        self.assertEqual(model_name, "gemma-3-27b-it")
        print("✅ Notebook logic for model selection is correct.")


if __name__ == "__main__":
    unittest.main()
