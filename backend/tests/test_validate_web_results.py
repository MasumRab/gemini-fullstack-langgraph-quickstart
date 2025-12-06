import pathlib
import sys

import pytest
from langchain_core.runnables import RunnableConfig

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
    config = RunnableConfig(configurable={})

    result = validate_web_results(state, config)

    assert result["validated_web_research_result"] == [
        "Quantum breakthroughs in error correction were announced."
    ]
    # The note usually says "Result X filtered..."
    assert "Result 2 filtered" in " ".join(result["validation_notes"])


def test_validate_web_results_falls_back_when_no_matches():
    summaries = ["Generic summary with no overlap."]
    # Provide a query that definitely doesn't match the summary
    state = {"search_query": ["specific topic"], "web_research_result": summaries}
    config = RunnableConfig(configurable={})

    result = validate_web_results(state, config)

    # Should retain the original if nothing matches (safeguard)
    assert result["validated_web_research_result"] == summaries
    assert any("All summaries failed" in note for note in result["validation_notes"])


def test_validate_web_results_handles_missing_summaries():
    state = {"search_query": ["ai"], "web_research_result": []}
    config = RunnableConfig(configurable={})

    result = validate_web_results(state, config)

    assert result["validated_web_research_result"] == []
    assert result["validation_notes"] == [
        "No web research summaries available for validation."
    ]


# Additional comprehensive tests for validate_web_results


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


def test_validate_web_results_case_insensitive_matching():
    """Test that matching is case-insensitive."""
    state = {
        "search_query": ["PYTHON programming"],
        "web_research_result": [
            "Python is a versatile programming language."
        ],
    }
    config = RunnableConfig(configurable={})
    
    result = validate_web_results(state, config)
    
    assert len(result["validated_web_research_result"]) == 1


def test_validate_web_results_partial_keyword_match():
    """Test matching with partial keyword overlap."""
    state = {
        "search_query": ["machine learning algorithms"],
        "web_research_result": [
            "Machine learning is transforming AI."  # Has "machine" and "learning"
        ],
    }
    config = RunnableConfig(configurable={})
    
    result = validate_web_results(state, config)
    
    assert len(result["validated_web_research_result"]) == 1


def test_validate_web_results_with_nested_query_list():
    """Test handling of nested query lists."""
    state = {
        "search_query": [["quantum", "computing"], "applications"],
        "web_research_result": [
            "Quantum computing applications in cryptography."
        ],
    }
    config = RunnableConfig(configurable={})
    
    result = validate_web_results(state, config)
    
    assert len(result["validated_web_research_result"]) == 1


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


def test_validate_web_results_numeric_queries():
    """Test handling queries with numeric content."""
    state = {
        "search_query": ["2024 trends"],
        "web_research_result": [
            "Top trends for 2024 include AI and automation."
        ],
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


def test_validate_web_results_single_summary():
    """Test validation with single summary."""
    state = {
        "search_query": ["important topic"],
        "web_research_result": [
            "Important information about the topic."
        ],
    }
    config = RunnableConfig(configurable={})
    
    result = validate_web_results(state, config)
    
    assert len(result["validated_web_research_result"]) == 1


def test_validate_web_results_whitespace_in_summaries():
    """Test handling summaries with excessive whitespace."""
    state = {
        "search_query": ["data"],
        "web_research_result": [
            "  Data   analysis   with   extra   spaces  "
        ],
    }
    config = RunnableConfig(configurable={})
    
    result = validate_web_results(state, config)
    
    assert len(result["validated_web_research_result"]) == 1
