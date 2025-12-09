import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from agent.nodes import validate_web_results  # noqa: E402


def test_validate_web_results_filters_irrelevant_summary():
    state = {
        "search_query": ["quantum computing advancements"],
        "web_research_result": [
            "Quantum breakthroughs in error correction were announced.",
            "Celebrity gossip unrelated to science.",
        ],
    }

    result = validate_web_results(state)

    assert result["validated_web_research_result"] == [
        "Quantum breakthroughs in error correction were announced."
    ]
    assert "Celebrity" in " ".join(result["validation_notes"])


def test_validate_web_results_falls_back_when_no_matches():
    summaries = ["Generic summary with no overlap."]
    state = {"search_query": [], "web_research_result": summaries}

    result = validate_web_results(state)

    assert result["validated_web_research_result"] == summaries
    assert any("All summaries failed" in note for note in result["validation_notes"])


def test_validate_web_results_handles_missing_summaries():
    state = {"search_query": ["ai"], "web_research_result": []}

    result = validate_web_results(state)

    assert result["validated_web_research_result"] == []
    assert result["validation_notes"] == [
        "No web research summaries available for validation."
    ]

    def test_validate_with_unicode_content(self):
        """Test validation with unicode characters in summaries."""
        state = {
            "search_query": ["测试"],
            "web_research_result": ["这是一个测试文本，包含测试关键字"]
        }
        
        result = validate_web_results(state)
        
        self.assertEqual(len(result["validated_web_research_result"]), 1)

    def test_validate_with_multiple_keywords_match(self):
        """Test that summary matching multiple keywords is validated."""
        state = {
            "search_query": ["python programming language"],
            "web_research_result": [
                "Python is a programming language used for development"
            ]
        }
        
        result = validate_web_results(state)
        
        self.assertEqual(len(result["validated_web_research_result"]), 1)

    def test_validate_keyword_partial_match(self):
        """Test that partial keyword matches work."""
        state = {
            "search_query": ["testing"],
            "web_research_result": [
                "This text contains the word test inside"
            ]
        }
        
        result = validate_web_results(state)
        
        # "test" is extracted from "testing" and should match "test" in content
        self.assertEqual(len(result["validated_web_research_result"]), 1)

    def test_validate_case_insensitive_matching(self):
        """Test that keyword matching is case insensitive."""
        state = {
            "search_query": ["Python"],
            "web_research_result": [
                "PYTHON is a great programming language"
            ]
        }
        
        result = validate_web_results(state)
        
        self.assertEqual(len(result["validated_web_research_result"]), 1)

    def test_validate_with_nested_query_lists(self):
        """Test validation with nested query structure."""
        state = {
            "search_query": [["nested", "query"], "flat"],
            "web_research_result": [
                "This is about nested structures",
                "This is a flat list"
            ]
        }
        
        result = validate_web_results(state)
        
        # Both should be validated
        self.assertGreaterEqual(len(result["validated_web_research_result"]), 1)

    def test_validate_all_filtered_retains_originals(self):
        """Test that when all summaries fail, originals are retained."""
        state = {
            "search_query": ["completely unrelated topic"],
            "web_research_result": [
                "This text has nothing to do with the query",
                "Neither does this one"
            ]
        }
        
        result = validate_web_results(state)
        
        # Should retain all originals when everything fails
        self.assertEqual(len(result["validated_web_research_result"]), 2)
        self.assertIn("retaining originals", result["validation_notes"][-1])

    def test_validate_query_with_special_chars(self):
        """Test validation with special characters in query."""
        state = {
            "search_query": ["C++ programming"],
            "web_research_result": [
                "This is about programming in general"
            ]
        }
        
        result = validate_web_results(state)
        
        # Should match on "programming"
        self.assertEqual(len(result["validated_web_research_result"]), 1)

    def test_validate_very_long_summary(self):
        """Test validation with very long summary text."""
        long_summary = "A" * 1000 + " python " + "B" * 1000
        state = {
            "search_query": ["python"],
            "web_research_result": [long_summary]
        }
        
        result = validate_web_results(state)
        
        self.assertEqual(len(result["validated_web_research_result"]), 1)

    def test_validate_notes_format(self):
        """Test that validation notes are properly formatted."""
        state = {
            "search_query": ["specific_topic"],
            "web_research_result": [
                "Unrelated content here",
                "Also unrelated"
            ]
        }
        
        result = validate_web_results(state)
        
        notes = result["validation_notes"]
        self.assertTrue(any("filtered" in note for note in notes))

    def test_validate_empty_string_query(self):
        """Test validation with empty string in query."""
        state = {
            "search_query": [""],
            "web_research_result": ["Some content here"]
        }
        
        result = validate_web_results(state)
        
        # Should still process but might retain originals
        self.assertIn("validated_web_research_result", result)

    def test_validate_single_char_query_filtered(self):
        """Test that very short query terms (< 4 chars) are filtered."""
        state = {
            "search_query": ["a b c"],  # All too short
            "web_research_result": ["Content with words a b c"]
        }
        
        result = validate_web_results(state)
        
        # Since no keywords >= 4 chars, should retain originals
        self.assertEqual(len(result["validated_web_research_result"]), 1)


if __name__ == "__main__":
    unittest.main()
