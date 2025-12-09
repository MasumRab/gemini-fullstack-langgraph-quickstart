import unittest
from unittest.mock import Mock
from langchain_core.messages import HumanMessage, AIMessage
from agent.utils import (
    get_research_topic,
    resolve_urls,
    insert_citation_markers,
    get_citations
)


class TestGetResearchTopic(unittest.TestCase):
    """Tests for get_research_topic function."""

    def test_single_message(self):
        """Test with single message."""
        messages = [HumanMessage(content="What is AI?")]
        result = get_research_topic(messages)
        self.assertEqual(result, "What is AI?")

    def test_multiple_human_messages(self):
        """Test with multiple human messages."""
        messages = [
            HumanMessage(content="Tell me about Python"),
            HumanMessage(content="What about Django?")
        ]
        result = get_research_topic(messages)
        self.assertIn("User: Tell me about Python", result)
        self.assertIn("User: What about Django?", result)

    def test_mixed_messages(self):
        """Test with mixed human and AI messages."""
        messages = [
            HumanMessage(content="What is ML?"),
            AIMessage(content="ML stands for Machine Learning"),
            HumanMessage(content="Tell me more")
        ]
        result = get_research_topic(messages)
        self.assertIn("User: What is ML?", result)
        self.assertIn("Assistant: ML stands for Machine Learning", result)
        self.assertIn("User: Tell me more", result)

    def test_empty_messages_list(self):
        """Test with empty messages list."""
        messages = []
        # Should handle gracefully - accessing [-1] will raise IndexError
        with self.assertRaises(IndexError):
            get_research_topic(messages)

    def test_message_with_newlines(self):
        """Test that newlines in content are preserved."""
        messages = [HumanMessage(content="Line 1\nLine 2\nLine 3")]
        result = get_research_topic(messages)
        self.assertEqual(result, "Line 1\nLine 2\nLine 3")

    def test_message_with_special_characters(self):
        """Test messages with special characters."""
        messages = [HumanMessage(content="What about C++ & C#?")]
        result = get_research_topic(messages)
        self.assertIn("C++ & C#", result)


class TestResolveUrls(unittest.TestCase):
    """Tests for resolve_urls function."""

    def test_single_url(self):
        """Test resolving a single URL."""
        mock_site = Mock()
        mock_site.web.uri = "https://example.com/page1"
        urls_to_resolve = [mock_site]
        
        result = resolve_urls(urls_to_resolve, id=0)
        
        expected_key = "https://example.com/page1"
        expected_value = "https://vertexaisearch.cloud.google.com/id/0-0"
        self.assertEqual(result[expected_key], expected_value)

    def test_multiple_urls(self):
        """Test resolving multiple unique URLs."""
        mock_sites = []
        for i in range(3):
            site = Mock()
            site.web.uri = f"https://example.com/page{i}"
            mock_sites.append(site)
        
        result = resolve_urls(mock_sites, id=5)
        
        self.assertEqual(len(result), 3)
        self.assertEqual(result["https://example.com/page0"], "https://vertexaisearch.cloud.google.com/id/5-0")
        self.assertEqual(result["https://example.com/page1"], "https://vertexaisearch.cloud.google.com/id/5-1")
        self.assertEqual(result["https://example.com/page2"], "https://vertexaisearch.cloud.google.com/id/5-2")

    def test_duplicate_urls(self):
        """Test that duplicate URLs use the same shortened URL."""
        mock_sites = []
        for _ in range(3):
            site = Mock()
            site.web.uri = "https://example.com/same"
            mock_sites.append(site)
        
        result = resolve_urls(mock_sites, id=1)
        
        # Should only have one entry
        self.assertEqual(len(result), 1)
        # Should use the first occurrence index
        self.assertEqual(result["https://example.com/same"], "https://vertexaisearch.cloud.google.com/id/1-0")

    def test_mixed_duplicate_and_unique(self):
        """Test with mix of duplicate and unique URLs."""
        mock_sites = []
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page1",  # duplicate
            "https://example.com/page3",
            "https://example.com/page2",  # duplicate
        ]
        for url in urls:
            site = Mock()
            site.web.uri = url
            mock_sites.append(site)
        
        result = resolve_urls(mock_sites, id=10)
        
        # Should have 3 unique URLs
        self.assertEqual(len(result), 3)
        # Duplicates should map to first occurrence
        self.assertEqual(result["https://example.com/page1"], "https://vertexaisearch.cloud.google.com/id/10-0")
        self.assertEqual(result["https://example.com/page2"], "https://vertexaisearch.cloud.google.com/id/10-1")
        self.assertEqual(result["https://example.com/page3"], "https://vertexaisearch.cloud.google.com/id/10-3")

    def test_empty_list(self):
        """Test with empty URLs list."""
        result = resolve_urls([], id=0)
        self.assertEqual(result, {})


class TestInsertCitationMarkers(unittest.TestCase):
    """Tests for insert_citation_markers function."""

    def test_single_citation_at_end(self):
        """Test inserting a single citation at the end of text."""
        text = "This is a test sentence."
        citations = [{
            "end_index": 25,
            "start_index": 0,
            "segments": [{"label": "Source1", "short_url": "http://s1.com"}]
        }]
        
        result = insert_citation_markers(text, citations)
        expected = "This is a test sentence. [Source1](http://s1.com)"
        self.assertEqual(result, expected)

    def test_multiple_citations(self):
        """Test inserting multiple citations."""
        text = "First sentence. Second sentence."
        citations = [
            {
                "end_index": 15,
                "start_index": 0,
                "segments": [{"label": "S1", "short_url": "http://s1.com"}]
            },
            {
                "end_index": 32,
                "start_index": 16,
                "segments": [{"label": "S2", "short_url": "http://s2.com"}]
            }
        ]
        
        result = insert_citation_markers(text, citations)
        self.assertIn("[S1](http://s1.com)", result)
        self.assertIn("[S2](http://s2.com)", result)

    def test_citation_with_multiple_segments(self):
        """Test citation with multiple source segments."""
        text = "Test content."
        citations = [{
            "end_index": 13,
            "start_index": 0,
            "segments": [
                {"label": "Source1", "short_url": "http://s1.com"},
                {"label": "Source2", "short_url": "http://s2.com"}
            ]
        }]
        
        result = insert_citation_markers(text, citations)
        self.assertIn("[Source1](http://s1.com)", result)
        self.assertIn("[Source2](http://s2.com)", result)

    def test_empty_citations_list(self):
        """Test with no citations."""
        text = "No citations here."
        result = insert_citation_markers(text, [])
        self.assertEqual(result, text)

    def test_overlapping_citations_sorted(self):
        """Test that citations are sorted properly to avoid index issues."""
        text = "ABCDEFGHIJ"
        citations = [
            {
                "end_index": 5,
                "start_index": 0,
                "segments": [{"label": "First", "short_url": "http://1.com"}]
            },
            {
                "end_index": 10,
                "start_index": 5,
                "segments": [{"label": "Second", "short_url": "http://2.com"}]
            }
        ]
        
        result = insert_citation_markers(text, citations)
        # Should insert from end to start to maintain indices
        self.assertTrue(result.endswith("[Second](http://2.com)"))

    def test_unicode_text_with_citations(self):
        """Test citation insertion with unicode characters."""
        text = "测试文本 with émojis 🚀"
        citations = [{
            "end_index": len(text),
            "start_index": 0,
            "segments": [{"label": "Unicode", "short_url": "http://u.com"}]
        }]
        
        result = insert_citation_markers(text, citations)
        self.assertIn("[Unicode](http://u.com)", result)


class TestGetCitations(unittest.TestCase):
    """Tests for get_citations function."""

    def test_empty_response(self):
        """Test with None or empty response."""
        result = get_citations(None, {})
        self.assertEqual(result, [])

    def test_no_candidates(self):
        """Test response with no candidates."""
        response = Mock()
        response.candidates = []
        result = get_citations(response, {})
        self.assertEqual(result, [])

    def test_no_grounding_metadata(self):
        """Test candidate without grounding metadata."""
        response = Mock()
        candidate = Mock(spec=[])  # No grounding_metadata attribute
        response.candidates = [candidate]
        result = get_citations(response, {})
        self.assertEqual(result, [])

    def test_basic_citation(self):
        """Test extracting a basic citation."""
        # Create mock response structure
        response = Mock()
        candidate = Mock()
        
        # Mock grounding chunk
        chunk = Mock()
        chunk.web.uri = "https://example.com"
        chunk.web.title = "Example.Title.html"
        
        # Mock grounding support
        support = Mock()
        support.segment = Mock()
        support.segment.start_index = 0
        support.segment.end_index = 10
        support.grounding_chunk_indices = [0]
        
        # Mock metadata
        metadata = Mock()
        metadata.grounding_supports = [support]
        metadata.grounding_chunks = [chunk]
        
        candidate.grounding_metadata = metadata
        response.candidates = [candidate]
        
        resolved_urls = {"https://example.com": "http://short.url/1"}
        
        result = get_citations(response, resolved_urls)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["start_index"], 0)
        self.assertEqual(result[0]["end_index"], 10)
        self.assertEqual(len(result[0]["segments"]), 1)
        self.assertEqual(result[0]["segments"][0]["short_url"], "http://short.url/1")

    def test_citation_with_multiple_chunks(self):
        """Test citation referencing multiple grounding chunks."""
        response = Mock()
        candidate = Mock()
        
        # Create two chunks
        chunk1 = Mock()
        chunk1.web.uri = "https://example1.com"
        chunk1.web.title = "Example1.Title"
        
        chunk2 = Mock()
        chunk2.web.uri = "https://example2.com"
        chunk2.web.title = "Example2.Title"
        
        # Support referencing both chunks
        support = Mock()
        support.segment = Mock()
        support.segment.start_index = 5
        support.segment.end_index = 20
        support.grounding_chunk_indices = [0, 1]
        
        metadata = Mock()
        metadata.grounding_supports = [support]
        metadata.grounding_chunks = [chunk1, chunk2]
        
        candidate.grounding_metadata = metadata
        response.candidates = [candidate]
        
        resolved_urls = {
            "https://example1.com": "http://short1",
            "https://example2.com": "http://short2"
        }
        
        result = get_citations(response, resolved_urls)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]["segments"]), 2)

    def test_missing_segment_skipped(self):
        """Test that supports without segment are skipped."""
        response = Mock()
        candidate = Mock()
        
        support1 = Mock(spec=[])  # No segment attribute
        
        support2 = Mock()
        support2.segment = Mock()
        support2.segment.start_index = 0
        support2.segment.end_index = 5
        support2.grounding_chunk_indices = []
        
        metadata = Mock()
        metadata.grounding_supports = [support1, support2]
        metadata.grounding_chunks = []
        
        candidate.grounding_metadata = metadata
        response.candidates = [candidate]
        
        result = get_citations(response, {})
        
        # support1 should be skipped, support2 should be included
        self.assertEqual(len(result), 1)

    def test_none_start_index_defaults_to_zero(self):
        """Test that None start_index defaults to 0."""
        response = Mock()
        candidate = Mock()
        
        chunk = Mock()
        chunk.web.uri = "https://example.com"
        chunk.web.title = "Test.Title"
        
        support = Mock()
        support.segment = Mock()
        support.segment.start_index = None
        support.segment.end_index = 10
        support.grounding_chunk_indices = [0]
        
        metadata = Mock()
        metadata.grounding_supports = [support]
        metadata.grounding_chunks = [chunk]
        
        candidate.grounding_metadata = metadata
        response.candidates = [candidate]
        
        result = get_citations(response, {"https://example.com": "http://short"})
        
        self.assertEqual(result[0]["start_index"], 0)

    def test_missing_end_index_skips_support(self):
        """Test that support without end_index is skipped."""
        response = Mock()
        candidate = Mock()
        
        support = Mock()
        support.segment = Mock()
        support.segment.start_index = 0
        support.segment.end_index = None
        
        metadata = Mock()
        metadata.grounding_supports = [support]
        metadata.grounding_chunks = []
        
        candidate.grounding_metadata = metadata
        response.candidates = [candidate]
        
        result = get_citations(response, {})
        
        # Should be skipped due to missing end_index
        self.assertEqual(len(result), 0)

    def test_invalid_chunk_index_handled(self):
        """Test that invalid chunk indices are handled gracefully."""
        response = Mock()
        candidate = Mock()
        
        support = Mock()
        support.segment = Mock()
        support.segment.start_index = 0
        support.segment.end_index = 10
        support.grounding_chunk_indices = [999]  # Invalid index
        
        metadata = Mock()
        metadata.grounding_supports = [support]
        metadata.grounding_chunks = []  # Empty list
        
        candidate.grounding_metadata = metadata
        response.candidates = [candidate]
        
        result = get_citations(response, {})
        
        # Should have citation but with empty segments
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]["segments"]), 0)


if __name__ == "__main__":
    unittest.main()