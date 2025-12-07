"""Unit tests for validate_web_results function.

Tests cover filtering logic, edge cases, and fallback behavior.
"""
import pytest

from agent.graph import validate_web_results


# =============================================================================
# Tests for validate_web_results
# =============================================================================

class TestValidateWebResults:
    """Tests for the validate_web_results function."""

    def test_filters_irrelevant_summaries(self):
        """Should filter summaries that don't overlap with query keywords."""
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
        # Note should mention the filtered summary
        assert any("Celebrity" in note for note in result["validation_notes"])

    def test_keeps_relevant_summaries(self):
        """Should keep all summaries that contain query keywords."""
        state = {
            "search_query": ["python programming tutorials"],
            "web_research_result": [
                "Learn Python programming from scratch.",
                "Advanced Python tutorials for developers.",
                "Python programming best practices.",
            ],
        }
        
        result = validate_web_results(state)
        
        # All should be kept (contain 'python', 'programming', or 'tutorials')
        assert len(result["validated_web_research_result"]) == 3

    def test_falls_back_when_no_matches(self):
        """Should keep all summaries if none match (fallback)."""
        state = {
            "search_query": [],
            "web_research_result": ["Generic summary with no overlap."],
        }
        
        result = validate_web_results(state)
        
        assert result["validated_web_research_result"] == ["Generic summary with no overlap."]
        assert any("All summaries failed" in note for note in result["validation_notes"])

    def test_handles_empty_summaries(self):
        """Should handle empty web_research_result gracefully."""
        state = {"search_query": ["ai"], "web_research_result": []}
        
        result = validate_web_results(state)
        
        assert result["validated_web_research_result"] == []
        assert result["validation_notes"] == [
            "No web research summaries available for validation."
        ]

    def test_handles_missing_web_research_key(self):
        """Should handle missing web_research_result key."""
        state = {"search_query": ["test"]}
        
        result = validate_web_results(state)
        
        assert result["validated_web_research_result"] == []
        assert "No web research summaries" in result["validation_notes"][0]

    def test_handles_missing_search_query_key(self):
        """Should handle missing search_query key."""
        state = {"web_research_result": ["Some summary about nothing."]}
        
        result = validate_web_results(state)
        
        # With no keywords, should fallback to keeping all
        assert result["validated_web_research_result"] == ["Some summary about nothing."]

    def test_case_insensitive_matching(self):
        """Keyword matching should be case-insensitive."""
        state = {
            "search_query": ["PYTHON programming"],
            "web_research_result": [
                "python is great for beginners.",
                "JavaScript is also popular.",
            ],
        }
        
        result = validate_web_results(state)
        
        assert "python is great for beginners." in result["validated_web_research_result"]

    def test_nested_query_lists_are_flattened(self):
        """Nested query lists should be flattened before processing."""
        state = {
            "search_query": [["nested query"], "flat query"],
            "web_research_result": [
                "This mentions nested topics.",
                "And also flat topics.",
            ],
        }
        
        result = validate_web_results(state)
        
        # Both should match based on keywords
        assert len(result["validated_web_research_result"]) >= 1

    def test_short_keywords_are_ignored(self):
        """Keywords shorter than 4 characters should be ignored."""
        state = {
            "search_query": ["AI ML"],  # 'AI' and 'ML' are too short
            "web_research_result": [
                "AI and ML are transforming industries.",
            ],
        }
        
        result = validate_web_results(state)
        
        # No valid keywords, should fallback
        assert len(result["validated_web_research_result"]) == 1
        assert any("All summaries failed" in note for note in result["validation_notes"])

    def test_multiple_matching_keywords(self):
        """Summary matching multiple keywords should be kept."""
        state = {
            "search_query": ["machine learning algorithms"],
            "web_research_result": [
                "Machine learning algorithms for classification.",
            ],
        }
        
        result = validate_web_results(state)
        
        assert len(result["validated_web_research_result"]) == 1

    def test_validation_notes_contain_filtered_content(self):
        """Validation notes should include information about filtered summaries."""
        state = {
            "search_query": ["specific topic"],
            "web_research_result": [
                "Relevant to specific topic.",
                "Completely unrelated content here.",
            ],
        }
        
        result = validate_web_results(state)
        
        # The filtered summary should be mentioned in notes
        notes_text = " ".join(result["validation_notes"])
        assert "unrelated" in notes_text.lower() or "filtered" in notes_text.lower()
