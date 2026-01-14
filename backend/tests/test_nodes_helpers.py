import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from agent.nodes import _flatten_queries, _keywords_from_queries  # noqa: E402


# Tests for _flatten_queries
def test_flatten_queries_with_flat_list():
    """Test flattening already flat list of queries."""
    queries = ["query1", "query2", "query3"]
    result = _flatten_queries(queries)

    assert result == ["query1", "query2", "query3"]
    assert len(result) == 3


def test_flatten_queries_with_nested_list():
    """Test flattening nested list of queries."""
    queries = ["query1", ["query2", "query3"], "query4"]
    result = _flatten_queries(queries)

    assert result == ["query1", "query2", "query3", "query4"]
    assert len(result) == 4


def test_flatten_queries_with_deeply_nested_list():
    """Test flattening deeply nested list."""
    queries = ["a", ["b", ["c", "d"]], "e"]
    result = _flatten_queries(queries)

    assert result == ["a", "b", "c", "d", "e"]
    assert len(result) == 5


def test_flatten_queries_empty_list():
    """Test flattening empty list."""
    queries = []
    result = _flatten_queries(queries)

    assert result == []


def test_flatten_queries_with_empty_nested_lists():
    """Test flattening list containing empty nested lists."""
    queries = ["query1", [], "query2", []]
    result = _flatten_queries(queries)

    assert result == ["query1", "query2"]


def test_flatten_queries_single_string():
    """Test flattening with single string."""
    queries = ["single"]
    result = _flatten_queries(queries)

    assert result == ["single"]


def test_flatten_queries_mixed_nesting_levels():
    """Test flattening with mixed nesting levels."""
    queries = [
        "top1",
        ["level1a", "level1b"],
        "top2",
        [["level2a", "level2b"], "level1c"]
    ]
    result = _flatten_queries(queries)

    assert "top1" in result
    assert "level1a" in result
    assert "level2a" in result
    assert len(result) == 7


def test_flatten_queries_preserves_order():
    """Test that flattening preserves order of elements."""
    queries = [["a", "b"], "c", ["d"]]
    result = _flatten_queries(queries)

    assert result == ["a", "b", "c", "d"]


# Tests for _keywords_from_queries
def test_keywords_from_queries_basic():
    """Test extracting keywords from simple queries."""
    queries = ["machine learning basics"]
    result = _keywords_from_queries(queries)

    assert "machine" in result
    assert "learning" in result
    assert "basics" in result


def test_keywords_from_queries_filters_short_words():
    """Test that words shorter than 4 characters are filtered out."""
    queries = ["AI is a new era"]
    result = _keywords_from_queries(queries)

    # Should not include "AI", "is", "a", "new" (all < 4 chars)
    # But "era" should not be included either (3 chars)
    assert "AI" not in result
    assert "is" not in result
    assert "a" not in result


def test_keywords_from_queries_lowercase_conversion():
    """Test that keywords are converted to lowercase."""
    queries = ["Python Programming Language"]
    result = _keywords_from_queries(queries)

    assert "python" in result
    assert "programming" in result
    assert "language" in result
    # Should not contain uppercase versions
    assert "Python" not in result


def test_keywords_from_queries_splits_on_special_chars():
    """Test that queries are split on special characters."""
    queries = ["web-development, mobile-apps"]
    result = _keywords_from_queries(queries)

    assert "development" in result
    assert "mobile" in result
    assert "apps" in result


def test_keywords_from_queries_empty_list():
    """Test extracting keywords from empty query list."""
    queries = []
    result = _keywords_from_queries(queries)

    assert result == []


def test_keywords_from_queries_multiple_queries():
    """Test extracting keywords from multiple queries."""
    queries = [
        "quantum computing",
        "neural networks",
        "machine learning"
    ]
    result = _keywords_from_queries(queries)

    assert "quantum" in result
    assert "computing" in result
    assert "neural" in result
    assert "networks" in result
    assert "machine" in result
    assert "learning" in result


def test_keywords_from_queries_handles_duplicates():
    """Test that duplicate keywords are deduplicated."""
    queries = ["learning machine learning"]
    result = _keywords_from_queries(queries)

    # The function uses set() to deduplicate for performance
    assert result.count("learning") == 1
    assert result.count("machine") == 1


def test_keywords_from_queries_handles_numbers():
    """Test handling of numeric tokens."""
    queries = ["Python3 programming 2024"]
    result = _keywords_from_queries(queries)

    assert "python3" in result  # Mixed alphanumeric >= 4 chars
    assert "programming" in result
    assert "2024" in result


def test_keywords_from_queries_ignores_pure_punctuation():
    """Test that pure punctuation tokens are ignored."""
    queries = ["test ... query !!! here"]
    result = _keywords_from_queries(queries)

    assert "test" in result
    assert "query" in result
    assert "here" in result
    # Punctuation-only tokens should not be included
    assert "..." not in result
    assert "!!!" not in result


def test_keywords_from_queries_handles_hyphenated_words():
    """Test handling of hyphenated compound words."""
    queries = ["state-of-the-art technology"]
    result = _keywords_from_queries(queries)

    assert "state" in result
    assert "technology" in result
    # "of", "the", "art" might be filtered depending on length


def test_keywords_from_queries_with_urls():
    """Test handling queries containing URL-like strings."""
    queries = ["visit https://example.com/page"]
    result = _keywords_from_queries(queries)

    assert "visit" in result
    assert "https" in result
    assert "example" in result
    assert "page" in result


def test_keywords_from_queries_length_threshold():
    """Test that exactly 4-character words are included."""
    queries = ["test word four"]
    result = _keywords_from_queries(queries)

    assert "test" in result  # 4 chars - should be included
    assert "word" in result  # 4 chars - should be included
    assert "four" in result  # 4 chars - should be included


def test_keywords_from_queries_unicode_handling():
    """Test handling of queries with unicode characters."""
    queries = ["café résumé naïve"]
    result = _keywords_from_queries(queries)

    # Should handle unicode properly
    assert "café" in result or "caf" in result  # Depending on normalization
    # Length check should still apply


def test_keywords_from_queries_empty_strings():
    """Test handling of empty strings in query list."""
    queries = ["", "valid query", ""]
    result = _keywords_from_queries(queries)

    assert "valid" in result
    assert "query" in result
    # Empty strings should not cause errors


def test_keywords_from_queries_whitespace_only():
    """Test handling queries with only whitespace."""
    queries = ["   ", "real query", "\t\n"]
    result = _keywords_from_queries(queries)

    assert "real" in result
    assert "query" in result


def test_keywords_from_queries_result_is_list():
    """Test that result is always a list."""
    queries = ["test"]
    result = _keywords_from_queries(queries)

    assert isinstance(result, list)
    assert all(isinstance(item, str) for item in result)