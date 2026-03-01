"""Unit tests for agent utility functions.

Tests cover edge cases, error handling, and typical usage patterns.
All tests are designed to be path-insensitive and robust to minor changes.
"""
import pytest
from typing import List

from tests.helpers import (
    MockSegment, MockChunk, MockSupport, MockCandidate, MockResponse, MockSite
)
from langchain_core.messages import HumanMessage, AIMessage

def make_human_message(content):
    return HumanMessage(content=content)

def make_ai_message(content):
    return AIMessage(content=content)
from agent.utils import (
    get_research_topic,
    resolve_urls,
    insert_citation_markers,
    get_citations,
)


# =============================================================================
# Tests for get_research_topic
# =============================================================================

class TestGetResearchTopic:
    """Tests for the get_research_topic function."""

    def test_single_message_returns_content_directly(self):
        """Single message should return the content as-is."""
        messages = [make_human_message("Research AI advancements")]
        topic = get_research_topic(messages)
        assert topic == "Research AI advancements"

    def test_multiple_messages_combines_with_labels(self):
        """Multiple messages should be combined with User/Assistant labels."""
        messages = [
            make_human_message("First query"),
            make_ai_message("Answer"),
            make_human_message("Second query"),
        ]
        topic = get_research_topic(messages)
        expected = "User: First query\nAssistant: Answer\nUser: Second query\n"
        assert topic == expected

    def test_two_messages_combines_with_labels(self):
        """Two messages should also combine with labels."""
        messages = [
            make_human_message("Question"),
            make_ai_message("Response"),
        ]
        topic = get_research_topic(messages)
        assert "User: Question" in topic
        assert "Assistant: Response" in topic

    def test_empty_content_message(self):
        """Message with empty content should work."""
        messages = [make_human_message("")]
        topic = get_research_topic(messages)
        assert topic == ""

    def test_message_with_special_characters(self):
        """Messages with special characters should be preserved."""
        messages = [make_human_message("What's the price of $AAPL & $MSFT?")]
        topic = get_research_topic(messages)
        assert "$AAPL" in topic
        assert "$MSFT" in topic


# =============================================================================
# Tests for resolve_urls
# =============================================================================

class TestResolveUrls:
    """Tests for the resolve_urls function."""

    def test_basic_url_resolution(self):
        """Basic URLs should be resolved to short form."""
        urls = [MockSite("http://example.com/a"), MockSite("http://example.com/b")]
        result = resolve_urls(urls, id=5)

        assert result["http://example.com/a"] == "https://vertexaisearch.cloud.google.com/id/5-0"
        assert result["http://example.com/b"] == "https://vertexaisearch.cloud.google.com/id/5-1"

    def test_duplicate_urls_get_same_short_url(self):
        """Duplicate URLs should map to the same short URL."""
        urls = [
            MockSite("http://example.com/page"),
            MockSite("http://example.com/page"),
            MockSite("http://other.com/page"),
        ]
        result = resolve_urls(urls, id=1)

        # First occurrence determines the index
        assert result["http://example.com/page"] == "https://vertexaisearch.cloud.google.com/id/1-0"
        assert result["http://other.com/page"] == "https://vertexaisearch.cloud.google.com/id/1-2"

    def test_empty_urls_returns_empty_dict(self):
        """Empty URL list should return empty dict."""
        result = resolve_urls([], id=0)
        assert result == {}

    def test_large_id_value(self):
        """Large ID values should work correctly."""
        urls = [MockSite("http://example.com/doc")]
        result = resolve_urls(urls, id=999999)
        assert "999999-0" in result["http://example.com/doc"]


# =============================================================================
# Tests for insert_citation_markers
# =============================================================================

class TestInsertCitationMarkers:
    """Tests for the insert_citation_markers function."""

    def test_single_citation_at_word_end(self):
        """Citation should be inserted after specified index."""
        text = "Hello world"
        citations = [{
            "end_index": 5,
            "segments": [{"label": "ref1", "short_url": "url1"}]
        }]
        result = insert_citation_markers(text, citations)
        assert result == "Hello [ref1](url1) world"

    def test_multiple_segments_in_one_citation(self):
        """Multiple segments should be joined."""
        text = "Hello world"
        citations = [{
            "end_index": 5,
            "segments": [
                {"label": "ref1", "short_url": "url1"},
                {"label": "ref2", "short_url": "url2"},
            ]
        }]
        result = insert_citation_markers(text, citations)
        assert "[ref1](url1)" in result
        assert "[ref2](url2)" in result

    def test_multiple_citations_at_different_positions(self):
        """Multiple citations at different positions."""
        text = "Hello beautiful world"
        citations = [
            {"end_index": 5, "segments": [{"label": "a", "short_url": "url_a"}]},
            {"end_index": 15, "segments": [{"label": "b", "short_url": "url_b"}]},
        ]
        result = insert_citation_markers(text, citations)
        assert "[a](url_a)" in result
        assert "[b](url_b)" in result

    def test_empty_citations_list(self):
        """Empty citations should return original text."""
        text = "Original text"
        result = insert_citation_markers(text, [])
        assert result == text

    def test_citation_without_start_index(self):
        """Citation missing start_index should still work (uses default 0)."""
        text = "Test text"
        citations = [{
            "end_index": 4,
            "segments": [{"label": "x", "short_url": "y"}]
        }]
        result = insert_citation_markers(text, citations)
        assert "[x](y)" in result

    def test_citation_with_empty_segments(self):
        """Citation with empty segments should not add markers."""
        text = "Test text"
        citations = [{"end_index": 4, "segments": []}]
        result = insert_citation_markers(text, citations)
        assert result == text

    def test_citation_at_end_of_text(self):
        """Citation at the very end of text."""
        text = "End"
        citations = [{"end_index": 3, "segments": [{"label": "x", "short_url": "y"}]}]
        result = insert_citation_markers(text, citations)
        assert result == "End [x](y)"


# =============================================================================
# Tests for get_citations
# =============================================================================

class TestGetCitations:
    """Tests for the get_citations function."""

    def test_full_citation_extraction(self):
        """Full flow: extract citations from mock response."""
        segment = MockSegment(start_index=0, end_index=5)
        support = MockSupport(segment=segment, grounding_chunk_indices=[0])
        chunk = MockChunk(uri="http://example.com/doc", title="Doc.Title.pdf")
        candidate = MockCandidate(grounding_supports=[support], grounding_chunks=[chunk])
        response = MockResponse(candidates=[candidate])
        resolved_map = {"http://example.com/doc": "short_url"}

        citations = get_citations(response, resolved_map)

        assert len(citations) == 1
        cit = citations[0]
        assert cit["start_index"] == 0
        assert cit["end_index"] == 5
        assert cit["segments"][0]["label"] == "Doc"
        assert cit["segments"][0]["short_url"] == "short_url"

    def test_empty_response_returns_empty_list(self):
        """Null/empty response should return empty list."""
        assert get_citations(None, {}) == []
        assert get_citations(MockResponse(candidates=[]), {}) == []

    def test_missing_grounding_metadata_returns_empty(self):
        """Candidate without grounding metadata returns empty list."""
        candidate = type("Candidate", (), {})()  # No grounding_metadata
        response = MockResponse(candidates=[candidate])
        assert get_citations(response, {}) == []

    def test_missing_segment_skips_support(self):
        """Support without segment should be skipped."""
        support = MockSupport(segment=None, grounding_chunk_indices=[0])
        chunk = MockChunk(uri="http://x.com", title="X")
        candidate = MockCandidate(grounding_supports=[support], grounding_chunks=[chunk])
        response = MockResponse(candidates=[candidate])

        citations = get_citations(response, {"http://x.com": "short"})
        assert citations == []

    def test_missing_end_index_skips_support(self):
        """Segment without end_index should be skipped."""
        segment = MockSegment(start_index=0, end_index=None)
        support = MockSupport(segment=segment, grounding_chunk_indices=[0])
        chunk = MockChunk(uri="http://x.com", title="X")
        candidate = MockCandidate(grounding_supports=[support], grounding_chunks=[chunk])
        response = MockResponse(candidates=[candidate])

        citations = get_citations(response, {"http://x.com": "short"})
        assert citations == []

    def test_start_index_defaults_to_zero(self):
        """Missing start_index should default to 0."""
        segment = MockSegment(start_index=None, end_index=10)
        support = MockSupport(segment=segment, grounding_chunk_indices=[0])
        chunk = MockChunk(uri="http://x.com", title="X.pdf")
        candidate = MockCandidate(grounding_supports=[support], grounding_chunks=[chunk])
        response = MockResponse(candidates=[candidate])

        citations = get_citations(response, {"http://x.com": "short"})
        assert len(citations) == 1
        assert citations[0]["start_index"] == 0

    def test_invalid_chunk_index_gracefully_handled(self):
        """Invalid chunk index should be skipped without error."""
        segment = MockSegment(start_index=0, end_index=5)
        support = MockSupport(segment=segment, grounding_chunk_indices=[99])  # Invalid
        chunk = MockChunk(uri="http://x.com", title="X")
        candidate = MockCandidate(grounding_supports=[support], grounding_chunks=[chunk])
        response = MockResponse(candidates=[candidate])

        citations = get_citations(response, {"http://x.com": "short"})
        # Citation should exist but with empty segments
        assert len(citations) == 1
        assert citations[0]["segments"] == []

    def test_url_not_in_resolved_map(self):
        """URL not in resolved map should still produce a segment with None short_url."""
        segment = MockSegment(start_index=0, end_index=5)
        support = MockSupport(segment=segment, grounding_chunk_indices=[0])
        chunk = MockChunk(uri="http://unknown.com", title="Unknown.pdf")
        candidate = MockCandidate(grounding_supports=[support], grounding_chunks=[chunk])
        response = MockResponse(candidates=[candidate])

        citations = get_citations(response, {})
        assert len(citations) == 1
        assert citations[0]["segments"][0]["short_url"] is None

    def test_multiple_supports_produce_multiple_citations(self):
        """Multiple supports should produce multiple citations."""
        segment1 = MockSegment(start_index=0, end_index=5)
        segment2 = MockSegment(start_index=10, end_index=15)
        support1 = MockSupport(segment=segment1, grounding_chunk_indices=[0])
        support2 = MockSupport(segment=segment2, grounding_chunk_indices=[0])
        chunk = MockChunk(uri="http://x.com", title="X.pdf")
        candidate = MockCandidate(grounding_supports=[support1, support2], grounding_chunks=[chunk])
        response = MockResponse(candidates=[candidate])

        citations = get_citations(response, {"http://x.com": "short"})
        assert len(citations) == 2

    def test_citations_handle_titles_without_dots(self):
        """Titles without dots should be preserved (no IndexError)."""
        segment = MockSegment(start_index=0, end_index=5)
        support = MockSupport(segment=segment, grounding_chunk_indices=[0])
        chunk = MockChunk(uri="http://google.com", title="Google")
        candidate = MockCandidate(grounding_supports=[support], grounding_chunks=[chunk])
        response = MockResponse(candidates=[candidate])
        resolved_map = {"http://google.com": "short_url"}

        citations = get_citations(response, resolved_map)
        assert len(citations) == 1
        assert citations[0]["segments"][0]["label"] == "Google"

# =============================================================================
# Tests for join_and_truncate
# =============================================================================

from agent.utils import join_and_truncate

class TestJoinAndTruncate:
    """Tests for the join_and_truncate function."""

    def test_empty_list(self):
        """Empty list should return empty string."""
        assert join_and_truncate([], 100) == ""

    def test_single_string_within_limit(self):
        """Single string smaller than limit."""
        assert join_and_truncate(["hello"], 10) == "hello"

    def test_single_string_exceeds_limit(self):
        """Single string larger than limit should be truncated."""
        assert join_and_truncate(["hello world"], 5) == "hello"

    def test_multiple_strings_within_limit(self):
        """Multiple strings fitting within limit."""
        assert join_and_truncate(["a", "b"], 10, separator=",") == "a,b"

    def test_multiple_strings_exceeds_limit(self):
        """Truncate when combined length exceeds limit."""
        # "hello" (5) + "," (1) + "world" (5) = 11
        # Limit 8 -> "hello,wo"
        assert join_and_truncate(["hello", "world"], 8, separator=",") == "hello,wo"

    def test_limit_equals_exact_length(self):
        """Exact match of length."""
        assert join_and_truncate(["a", "b"], 3, separator=",") == "a,b"

    def test_limit_cuts_at_separator(self):
        """Limit falls exactly after the first string but before full separator?
        Actually separator is added if there is a next string.
        "a" (1) + "," (1) + "b" (1). Limit 1.
        Result should be "a".
        """
        assert join_and_truncate(["a", "b"], 1, separator=",") == "a"

    def test_limit_allows_partial_separator(self):
        """Logic check: if limit allows part of separator but not full?
        The implementation assumes separator is all or nothing logic-wise for the next chunk.
        "a" (1), limit 2, sep "," (1).
        overhead = 1. cur = 1. 1+1+1 = 3 > 2.
        remaining = 2 - (1 + 1) = 0.
        remaining is not > 0, so we break.
        Result "a".
        This is preferred behavior: do not include separator if no content from next string can be added.
        """
        assert join_and_truncate(["a", "b"], 2, separator=",") == "a"

    def test_limit_cuts_separator_completely(self):
        """
        "a", "b", sep=",". limit 1.
        cur=1. overhead=1. 1+1+1 = 3 > 1.
        remaining = 1 - (1+1) = -1.
        remaining <= 0 check logic?

        Code:
            remaining = max_length - (current_length + overhead)
            if remaining > 0:
                 result_parts.append(s[:remaining])
            break

        remaining = 1 - 2 = -1. Not > 0.
        Break. parts=["a"]. Result "a". Correct.
        """
        assert join_and_truncate(["a", "b"], 1, separator=",") == "a"


# =============================================================================
# Tests for has_fuzzy_match
# =============================================================================

from agent.utils import has_fuzzy_match

class TestHasFuzzyMatch:
    """Tests for the has_fuzzy_match function."""

    def test_exact_match(self):
        """Exact match should return True."""
        assert has_fuzzy_match("apple", ["apple", "banana"]) is True

    def test_fuzzy_match_above_cutoff(self):
        """Fuzzy match above cutoff should return True."""
        # "aple" vs "apple" is very similar
        assert has_fuzzy_match("aple", ["apple", "banana"], cutoff=0.8) is True

    def test_no_match(self):
        """No match should return False."""
        assert has_fuzzy_match("xyz", ["apple", "banana"], cutoff=0.8) is False

    def test_empty_candidates(self):
        """Empty candidates list should return False."""
        assert has_fuzzy_match("apple", []) is False

    def test_custom_cutoff(self):
        """Custom cutoff should be respected."""
        # "apple" vs "apply" -> ratio is 0.8.
        assert has_fuzzy_match("apple", ["apply"], cutoff=0.9) is False
        assert has_fuzzy_match("apple", ["apply"], cutoff=0.7) is True

    def test_length_optimization(self):
        """Test that length-based optimization works correctly."""
        # Valid match with different lengths: "apple" (5) vs "apples" (6)
        # Ratio: 2*5 / 11 = 0.909 >= 0.8.
        # Bounds check:
        # Upper for 5, cutoff 0.8: 5 * 1.5 = 7.5. 6 <= 7.5. OK.
        # Lower for 5, cutoff 0.8: 5 * 0.66 = 3.33. 6 >= 3.33. OK.
        assert has_fuzzy_match("apple", ["apples"], cutoff=0.8) is True

        # Vastly different lengths should be skipped/fail
        # "a" (1) vs "aaaaa" (5). Ratio 2/6 = 0.33. Cutoff 0.8.
        # Bounds check: Upper for 1: 1.5. 5 > 1.5. Skipped.
        assert has_fuzzy_match("a", ["aaaaa"], cutoff=0.8) is False

        # Edge case: cutoff 1.0 (Exact length required)
        # Upper: kw_len * 1 / 1 = kw_len.
        # Lower: kw_len * 1 / 1 = kw_len.
        # So must be exact length.
        assert has_fuzzy_match("abc", ["abcd"], cutoff=1.0) is False
        assert has_fuzzy_match("abc", ["abc"], cutoff=1.0) is True
