"""Unit tests for validate_web_results function.

Tests cover filtering logic, edge cases, and fallback behavior.
"""
import pytest
from langchain_core.runnables import RunnableConfig

from agent.nodes import validate_web_results


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
        config = RunnableConfig(configurable={})

        result = validate_web_results(state, config)

        assert result["validated_web_research_result"] == [
            "Quantum breakthroughs in error correction were announced."
        ]
        # Note should mention the filtered summary
        assert "Result 2 filtered" in " ".join(result["validation_notes"])

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
        config = RunnableConfig(configurable={})

        result = validate_web_results(state, config)

        # All should be kept (contain 'python', 'programming', or 'tutorials')
        assert len(result["validated_web_research_result"]) == 3

    def test_falls_back_when_no_matches(self):
        """Should keep all summaries if none match (fallback)."""
        summaries = ["Generic summary with no overlap."]
        state = {"search_query": ["specific topic"], "web_research_result": summaries}
        config = RunnableConfig(configurable={})

        result = validate_web_results(state, config)

        # Should retain the original if nothing matches (safeguard)
        assert result["validated_web_research_result"] == summaries
        assert any("All summaries failed" in note for note in result["validation_notes"])

    def test_handles_empty_summaries(self):
        """Should handle empty web_research_result gracefully."""
        state = {"search_query": ["ai"], "web_research_result": []}
        config = RunnableConfig(configurable={})

        result = validate_web_results(state, config)

        assert result["validated_web_research_result"] == []
        assert result["validation_notes"] == [
            "No web research summaries available for validation."
        ]

    def test_handles_missing_web_research_key(self):
        """Should handle missing web_research_result key."""
        state = {"search_query": ["test"]}
        config = RunnableConfig(configurable={})

        result = validate_web_results(state, config)

        assert result["validated_web_research_result"] == []
        assert "No web research summaries" in result["validation_notes"][0]

    def test_handles_missing_search_query_key(self):
        """Should handle missing search_query key."""
        state = {"web_research_result": ["Some summary about nothing."]}
        config = RunnableConfig(configurable={})

        result = validate_web_results(state, config)

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
        config = RunnableConfig(configurable={})

        result = validate_web_results(state, config)

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
        config = RunnableConfig(configurable={})

        result = validate_web_results(state, config)

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
        config = RunnableConfig(configurable={})

        result = validate_web_results(state, config)

        # No valid keywords, should fallback to keeping everything (safety net)
        assert len(result["validated_web_research_result"]) == 1
        # When no keywords are extracted, we treat it as "match all" or "don't filter",
        # so we don't expect "All summaries failed" notes because nothing was actually filtered out or failed a check.
        # The logic is: "if match_found or not keywords: validated.append"

    def test_multiple_matching_keywords(self):
        """Summary matching multiple keywords should be kept."""
        state = {
            "search_query": ["machine learning algorithms"],
            "web_research_result": [
                "Machine learning algorithms for classification.",
            ],
        }
        config = RunnableConfig(configurable={})

        result = validate_web_results(state, config)

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
        config = RunnableConfig(configurable={})

        result = validate_web_results(state, config)

        # The filtered summary should be mentioned in notes
        notes_text = " ".join(result["validation_notes"])
        assert "unrelated" in notes_text.lower() or "filtered" in notes_text.lower()


# Additional comprehensive tests from remote branch

def test_validate_web_results_with_fuzzy_matching():
    """Test that fuzzy matching catches similar but not exact keywords."""
    state = {
        "search_query": ["quantm computing"],  # Typo in "quantum"
        "web_research_result": [
            "Latest quantum computing advancements are remarkable."
        ],
    }
    config = RunnableConfig(configurable={})

    result = validate_web_results(state, config)

    # Should match despite typo due to fuzzy matching
    assert len(result["validated_web_research_result"]) > 0


def test_validate_web_results_multiple_summaries_mixed():
    """Test filtering with mix of relevant and irrelevant summaries."""
    state = {
        "search_query": ["artificial intelligence applications"],
        "web_research_result": [
            "AI applications in healthcare are expanding rapidly.",
            "Recipe for chocolate cake with vanilla frosting.",
            "Artificial intelligence transforms various industries.",
            "Sports news from yesterday's games.",
        ],
    }
    config = RunnableConfig(configurable={})

    result = validate_web_results(state, config)

    # Should keep only relevant ones
    validated = result["validated_web_research_result"]
    assert len(validated) == 2
    assert any("AI" in s or "artificial" in s.lower() for s in validated)


def test_validate_web_results_validation_notes_format():
    """Test that validation notes are properly formatted."""
    state = {
        "search_query": ["specific"],
        "web_research_result": [
            "Specific information here.",
            "Unrelated content."
        ],
    }
    config = RunnableConfig(configurable={})

    result = validate_web_results(state, config)

    assert "validation_notes" in result
    assert isinstance(result["validation_notes"], list)
    # Should have at least one note about filtering
    assert len(result["validation_notes"]) > 0


def test_validate_web_results_no_keywords_extracted():
    """Test behavior when no keywords can be extracted from queries."""
    state = {
        "search_query": ["a", "is", "the"],  # All too short
        "web_research_result": [
            "Some summary text."
        ],
    }
    config = RunnableConfig(configurable={})

    result = validate_web_results(state, config)

    # With no keywords, should retain original summaries
    assert result["validated_web_research_result"] == ["Some summary text."]


def test_validate_web_results_all_summaries_relevant():
    """Test when all summaries are relevant (none filtered)."""
    state = {
        "search_query": ["technology"],
        "web_research_result": [
            "Technology advances every year.",
            "New technology breakthroughs announced.",
            "Technology sector grows rapidly."
        ],
    }
    config = RunnableConfig(configurable={})

    result = validate_web_results(state, config)

    assert len(result["validated_web_research_result"]) == 3


def test_validate_web_results_special_characters_in_query():
    """Test handling queries with special characters."""
    state = {
        "search_query": ["machine-learning & deep-learning"],
        "web_research_result": [
            "Machine learning and deep learning are related."
        ],
    }
    config = RunnableConfig(configurable={})

    result = validate_web_results(state, config)

    assert len(result["validated_web_research_result"]) == 1


def test_validate_web_results_long_summaries():
    """Test validation with very long summary text."""
    long_summary = "technology " * 100 + "random content " * 50
    state = {
        "search_query": ["technology"],
        "web_research_result": [long_summary],
    }
    config = RunnableConfig(configurable={})

    result = validate_web_results(state, config)

    assert len(result["validated_web_research_result"]) == 1


def test_validate_web_results_query_as_string_not_list():
    """Test handling when search_query is a string instead of list."""
    state = {
        "search_query": "single query string",
        "web_research_result": [
            "Information about single query topics."
        ],
    }
    config = RunnableConfig(configurable={})

    result = validate_web_results(state, config)

    # Should handle gracefully
    assert "validated_web_research_result" in result


def test_validate_web_results_preserves_order():
    """Test that order of valid summaries is preserved."""
    state = {
        "search_query": ["test"],
        "web_research_result": [
            "First test result.",
            "Second test result.",
            "Third test result."
        ],
    }
    config = RunnableConfig(configurable={})

    result = validate_web_results(state, config)

    validated = result["validated_web_research_result"]
    assert "First" in validated[0]
    assert "Second" in validated[1]
    assert "Third" in validated[2]
