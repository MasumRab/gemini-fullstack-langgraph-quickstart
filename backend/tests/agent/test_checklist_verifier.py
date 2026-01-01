
import unittest
from unittest.mock import MagicMock, patch
from agent.nodes import checklist_verifier
from agent.state import OverallState

class TestChecklistVerifier(unittest.TestCase):
    def setUp(self):
        self.mock_config = {"configurable": {"thread_id": "1", "answer_model": "test-model"}}
        self.mock_outline = {
            "title": "Test Report",
            "sections": [
                {
                    "title": "Section 1",
                    "subsections": [{"title": "Sub 1", "description": "Desc 1"}]
                }
            ]
        }
        self.mock_evidence_bank = [
            {
                "claim": "Claim 1",
                "source_url": "http://example.com",
                "context_snippet": "Context 1"
            }
        ]
        self.mock_research_results = ["Summary 1"]

    @patch("agent.nodes._get_rate_limited_llm")
    @patch("agent.nodes.Configuration.from_runnable_config")
    def test_checklist_verifier_with_evidence_bank(self, mock_config_cls, mock_get_llm):
        # Setup mocks
        mock_config_instance = MagicMock()
        mock_config_instance.answer_model = "test-model"
        mock_config_cls.return_value = mock_config_instance

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "## Verification Report\n\n✅ Section 1"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        state: OverallState = {
            "outline": self.mock_outline,
            "evidence_bank": self.mock_evidence_bank,
            "validated_web_research_result": [],
            "web_research_result": []
        }

        result = checklist_verifier(state, self.mock_config)

        self.assertIn("validation_notes", result)
        self.assertIn("## Verification Report", result["validation_notes"][0])

        # Verify prompt construction
        args, _ = mock_llm.invoke.call_args
        prompt = args[0]
        self.assertIn("Section 1", prompt)
        self.assertIn("Claim 1", prompt)

    @patch("agent.nodes._get_rate_limited_llm")
    @patch("agent.nodes.Configuration.from_runnable_config")
    def test_checklist_verifier_fallback_to_summaries(self, mock_config_cls, mock_get_llm):
        # Setup mocks
        mock_config_instance = MagicMock()
        mock_config_instance.answer_model = "test-model"
        mock_config_cls.return_value = mock_config_instance

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Report from summaries"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        state: OverallState = {
            "outline": self.mock_outline,
            "evidence_bank": [],
            "validated_web_research_result": ["Detailed Summary of Topic"],
            "web_research_result": []
        }

        result = checklist_verifier(state, self.mock_config)
        self.assertIn("Report from summaries", result["validation_notes"][0])

    def test_checklist_verifier_no_outline(self):
        state: OverallState = {
            "outline": None,
            "evidence_bank": self.mock_evidence_bank
        }
        result = checklist_verifier(state, self.mock_config)
        self.assertIn("Skipped Checklist Verification: No outline available.", result["validation_notes"])

    def test_checklist_verifier_no_evidence(self):
        state: OverallState = {
            "outline": self.mock_outline,
            "evidence_bank": [],
            "validated_web_research_result": [],
            "web_research_result": []
        }
        result = checklist_verifier(state, self.mock_config)
        self.assertIn("Skipped Checklist Verification: No evidence gathered.", result["validation_notes"])

if __name__ == "__main__":
    unittest.main()
