import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from agent.utils import (  # noqa: E402
    get_citations,
    resolve_urls,
    insert_citation_markers,
    get_research_topic,
)


class TestGetCitations:
    """Test suite for get_citations function."""

    def test_get_citations_basic(self):
        """Test get_citations extracts citation information correctly."""
        # Mock response structure
        mock_response = type('obj', (object,), {
            'text': 'Sample text with citations',
            'candidates': [
                type('obj', (object,), {
                    'grounding_metadata': type('obj', (object,), {
                        'grounding_supports': [
                            type('obj', (object,), {
                                'segment': type('obj', (object,), {
                                    'start_index': 0,
                                    'end_index': 11,
                                })(),
                                'grounding_chunk_indices': [0],
                            })(),
                        ],
                    })(),
                })(),
            ],
        })()
        
        resolved_urls = {0: {"short_url": "[1]", "label": "source1", "value": "http://example.com"}}
        
        citations = get_citations(mock_response, resolved_urls)
        
        assert len(citations) > 0
        assert citations[0]['start_index'] == 0
        # The comment notes that end_index handling might need adjustment
        assert 'end_index' in citations[0]

    def test_get_citations_with_comment_awareness(self):
        """Test that the citation extraction includes proper end_index handling.
        
        This test verifies the comment added in utils.py about end_index being
        exclusive or inclusive based on the Gemini API behavior.
        """
        # This is a verification test for the comment addition
        # The actual behavior depends on API observation
        mock_response = type('obj', (object,), {
            'text': 'Text',
            'candidates': [
                type('obj', (object,), {
                    'grounding_metadata': type('obj', (object,), {
                        'grounding_supports': [
                            type('obj', (object,), {
                                'segment': type('obj', (object,), {
                                    'start_index': 0,
                                    'end_index': 4,  # Could be exclusive or inclusive
                                })(),
                                'grounding_chunk_indices': [0],
                            })(),
                        ],
                    })(),
                })(),
            ],
        })()
        
        resolved_urls = {0: {"short_url": "[1]", "label": "test", "value": "http://test.com"}}
        citations = get_citations(mock_response, resolved_urls)
        
        # Verify end_index is preserved as returned by API
        assert citations[0]['end_index'] == 4


class TestResolveUrls:
    """Test suite for resolve_urls function."""

    def test_resolve_urls_creates_short_urls(self):
        """Test that resolve_urls creates short URL mappings."""
        mock_chunks = [
            type('obj', (object,), {
                'web': type('obj', (object,), {
                    'uri': 'https://example.com/page1',
                    'title': 'Example Page',
                })(),
            })(),
            type('obj', (object,), {
                'web': type('obj', (object,), {
                    'uri': 'https://example.com/page2',
                    'title': 'Another Page',
                })(),
            })(),
        ]
        
        result = resolve_urls(mock_chunks, "test-id")
        
        assert len(result) == 2
        # Should create mappings with indices
        assert 0 in result
        assert 1 in result

    def test_resolve_urls_empty_chunks(self):
        """Test resolve_urls with empty chunks."""
        result = resolve_urls([], "id")
        assert result == {}


class TestInsertCitationMarkers:
    """Test suite for insert_citation_markers function."""

    def test_insert_citation_markers_basic(self):
        """Test inserting citation markers into text."""
        text = "This is a sample text with sources."
        citations = [
            {
                'start_index': 10,
                'end_index': 16,
                'segments': [{'short_url': '[1]'}]
            }
        ]
        
        result = insert_citation_markers(text, citations)
        
        # Should insert citation marker
        assert '[1]' in result

    def test_insert_citation_markers_multiple(self):
        """Test inserting multiple citation markers."""
        text = "First citation and second citation here."
        citations = [
            {
                'start_index': 0,
                'end_index': 14,
                'segments': [{'short_url': '[1]'}]
            },
            {
                'start_index': 19,
                'end_index': 34,
                'segments': [{'short_url': '[2]'}]
            }
        ]
        
        result = insert_citation_markers(text, citations)
        
        assert '[1]' in result
        assert '[2]' in result

    def test_insert_citation_markers_empty_citations(self):
        """Test with no citations."""
        text = "Text without citations"
        result = insert_citation_markers(text, [])
        
        assert result == text


class TestGetResearchTopic:
    """Test suite for get_research_topic function."""

    def test_get_research_topic_from_human_message(self):
        """Test extracting topic from human message."""
        messages = [
            {"role": "human", "content": "Tell me about quantum computing"}
        ]
        
        topic = get_research_topic(messages)
        
        assert "quantum computing" in topic.lower()

    def test_get_research_topic_last_human_message(self):
        """Test that it extracts from the last human message."""
        messages = [
            {"role": "human", "content": "First question"},
            {"role": "ai", "content": "First answer"},
            {"role": "human", "content": "Second question about AI"},
        ]
        
        topic = get_research_topic(messages)
        
        assert "second question" in topic.lower() or "ai" in topic.lower()

    def test_get_research_topic_with_message_objects(self):
        """Test with message objects instead of dicts."""
        from langchain_core.messages import HumanMessage, AIMessage
        
        messages = [
            HumanMessage(content="Research topic here"),
            AIMessage(content="Response"),
        ]
        
        topic = get_research_topic(messages)
        
        assert "research topic" in topic.lower()

    def test_get_research_topic_empty_messages(self):
        """Test handling of empty message list."""
        topic = get_research_topic([])
        
        # Should handle gracefully (implementation dependent)
        assert topic is not None


class TestUtilsEdgeCases:
    """Test edge cases and error handling in utils."""

    def test_get_citations_no_grounding_metadata(self):
        """Test get_citations when no grounding metadata exists."""
        mock_response = type('obj', (object,), {
            'text': 'Text',
            'candidates': [],
        })()
        
        citations = get_citations(mock_response, {})
        
        # Should handle gracefully
        assert isinstance(citations, list)

    def test_get_citations_empty_supports(self):
        """Test with empty grounding supports."""
        mock_response = type('obj', (object,), {
            'text': 'Text',
            'candidates': [
                type('obj', (object,), {
                    'grounding_metadata': type('obj', (object,), {
                        'grounding_supports': [],
                    })(),
                })(),
            ],
        })()
        
        citations = get_citations(mock_response, {})
        assert isinstance(citations, list)

    def test_insert_citation_markers_overlapping(self):
        """Test citation markers with overlapping ranges."""
        text = "Overlapping citation ranges text"
        citations = [
            {
                'start_index': 0,
                'end_index': 15,
                'segments': [{'short_url': '[1]'}]
            },
            {
                'start_index': 10,
                'end_index': 20,
                'segments': [{'short_url': '[2]'}]
            }
        ]
        
        result = insert_citation_markers(text, citations)
        
        # Should handle overlapping citations
        assert '[1]' in result or '[2]' in result

    def test_resolve_urls_with_special_characters(self):
        """Test URL resolution with special characters in URLs."""
        mock_chunks = [
            type('obj', (object,), {
                'web': type('obj', (object,), {
                    'uri': 'https://example.com/page?query=test&param=value',
                    'title': 'Page with query params',
                })(),
            })(),
        ]
        
        result = resolve_urls(mock_chunks, "test")
        
        assert 0 in result
        # URL should be preserved correctly
        assert 'query=test' in str(result[0])