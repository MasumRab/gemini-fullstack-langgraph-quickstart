"""Shared test helpers and mocks."""
from types import SimpleNamespace
from typing import List

# =============================================================================
# Mock Classes for External Dependencies
# =============================================================================

class MockSegment:
    """Mock for grounding segment metadata."""
    def __init__(self, start_index=None, end_index=None):
        self.start_index = start_index
        self.end_index = end_index


class MockChunk:
    """Mock for grounding chunk with web metadata."""
    def __init__(self, uri: str, title: str):
        self.web = SimpleNamespace(uri=uri, title=title)


class MockSupport:
    """Mock for grounding support metadata."""
    def __init__(self, segment: MockSegment, grounding_chunk_indices: List[int] = None):
        self.segment = segment
        self.grounding_chunk_indices = grounding_chunk_indices or []


class MockCandidate:
    """Mock for API response candidate."""
    def __init__(self, grounding_supports: List[MockSupport], grounding_chunks: List[MockChunk]):
        self.grounding_metadata = SimpleNamespace(
            grounding_supports=grounding_supports,
            grounding_chunks=grounding_chunks,
        )


class MockResponse:
    """Mock for API response with candidates."""
    def __init__(self, candidates: List[MockCandidate]):
        self.candidates = candidates


class MockSite:
    """Mock for URL site data."""
    def __init__(self, uri: str):
        self.web = SimpleNamespace(uri=uri)
