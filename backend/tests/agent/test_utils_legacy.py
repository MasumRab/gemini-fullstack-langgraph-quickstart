import pytest
import sys
from unittest.mock import MagicMock

from langchain_core.messages import HumanMessage, AIMessage
from agent.utils import (
    get_research_topic,
    resolve_urls,
    insert_citation_markers,
    get_citations
)

# Test get_research_topic
def test_get_research_topic_single_message():
    messages = [HumanMessage(content="Hello world")]
    assert get_research_topic(messages) == "Hello world"

def test_get_research_topic_multiple_messages():
    messages = [
        HumanMessage(content="Hello"),
        AIMessage(content="Hi there"),
        HumanMessage(content="Research topic")
    ]
    expected = "User: Hello\nAssistant: Hi there\nUser: Research topic\n"
    assert get_research_topic(messages) == expected

def test_get_research_topic_empty():
    assert get_research_topic([]) == ""

# Test resolve_urls
class MockWeb:
    def __init__(self, uri):
        self.uri = uri

class MockSite:
    def __init__(self, uri):
        self.web = MockWeb(uri)

def test_resolve_urls():
    urls = [
        MockSite("http://example.com/1"),
        MockSite("http://example.com/2"),
        MockSite("http://example.com/1"), # Duplicate
    ]
    resolved = resolve_urls(urls, id=123)

    assert resolved["http://example.com/1"] == "https://vertexaisearch.cloud.google.com/id/123-0"
    assert resolved["http://example.com/2"] == "https://vertexaisearch.cloud.google.com/id/123-1"
    # Ensure duplicates don't overwrite the first mapping logic or are handled as expected.
    # The logic says: if url not in resolved_map: resolved_map[url] = ...
    # So the first occurrence wins.
    assert len(resolved) == 2

# Test insert_citation_markers
def test_insert_citation_markers():
    text = "This is a statement. This is another."
    citations = [
        {
            "start_index": 0,
            "end_index": 19,
            "segments": [{"label": "Source 1", "short_url": "url1"}]
        }
    ]
    # "This is a statement." is 20 chars? 0-19 covers "This is a statement"

    result = insert_citation_markers(text, citations)
    # The function inserts AT end_index.
    expected = "This is a statement [Source 1](url1). This is another."
    assert result == expected

def test_insert_citation_markers_multiple_overlap():
    text = "ABCD"
    citations = [
        {"start_index": 0, "end_index": 1, "segments": [{"label": "S1", "short_url": "u1"}]}, # After A
        {"start_index": 2, "end_index": 3, "segments": [{"label": "S2", "short_url": "u2"}]}  # After C
    ]
    # Sorted by end_index reverse: 3, then 1.
    # Insert at 3 (after C): ABC [S2](u2)D
    # Insert at 1 (after A): A [S1](u1)BC [S2](u2)D

    result = insert_citation_markers(text, citations)
    assert result == "A [S1](u1)BC [S2](u2)D"

# Test get_citations
class MockSegment:
    def __init__(self, start, end):
        self.start_index = start
        self.end_index = end

class MockChunk:
    def __init__(self, uri, title):
        self.web = MockWeb(uri)
        self.web.title = title

class MockSupport:
    def __init__(self, segment, indices):
        self.segment = segment
        self.grounding_chunk_indices = indices

class MockMetadata:
    def __init__(self, supports, chunks):
        self.grounding_supports = supports
        self.grounding_chunks = chunks

class MockCandidate:
    def __init__(self, metadata):
        self.grounding_metadata = metadata

class MockResponse:
    def __init__(self, candidate):
        self.candidates = [candidate] if candidate else []

def test_get_citations_basic():
    # Setup
    chunk1 = MockChunk("http://site1.com", "Title 1.")
    resolved_map = {"http://site1.com": "short1"}

    segment = MockSegment(0, 10)
    support = MockSupport(segment, [0])

    metadata = MockMetadata([support], [chunk1])
    candidate = MockCandidate(metadata)
    response = MockResponse(candidate)

    citations = get_citations(response, resolved_map)

    assert len(citations) == 1
    assert citations[0]["start_index"] == 0
    assert citations[0]["end_index"] == 10
    assert len(citations[0]["segments"]) == 1
    assert citations[0]["segments"][0]["label"] == "Title 1"
    assert citations[0]["segments"][0]["short_url"] == "short1"

def test_get_citations_empty_or_invalid():
    assert get_citations(None, {}) == []
    assert get_citations(MockResponse(None), {}) == [] # No candidates

    # Missing metadata
    cand = MockCandidate(None)
    assert get_citations(MockResponse(cand), {}) == []
