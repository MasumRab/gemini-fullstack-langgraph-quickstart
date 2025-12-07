"""Property-based tests for utility functions using Hypothesis.

These tests generate random inputs to find edge cases that standard unit tests might miss.
"""
import pytest
from hypothesis import given, settings, HealthCheck, strategies as st
from agent.utils import insert_citation_markers, resolve_urls
from agent.research_tools import deduplicate_search_results


# =============================================================================
# Strategies
# =============================================================================

# Strategy for citation segments
citation_segment_strategy = st.fixed_dictionaries({
    "label": st.text(min_size=1, max_size=10),
    "short_url": st.text(min_size=1, max_size=20),
    "value": st.text(min_size=1, max_size=50),
})

# Strategy for citation objects
citation_strategy = st.fixed_dictionaries({
    "start_index": st.integers(min_value=0, max_value=500),
    "end_index": st.integers(min_value=0, max_value=500),
    "segments": st.lists(citation_segment_strategy, max_size=3),
})

# Strategy for search results
search_result_strategy = st.fixed_dictionaries({
    "url": st.text(min_size=1, max_size=50),
    "title": st.text(max_size=50),
    "content": st.text(max_size=100),
    "raw_content": st.one_of(st.none(), st.text(max_size=100)),
})

# Strategy for search response objects
search_response_strategy = st.fixed_dictionaries({
    "query": st.text(max_size=50),
    "results": st.lists(search_result_strategy, max_size=3),
})


# =============================================================================
# Property Tests
# =============================================================================

class TestUtilsProperties:
    """Property-based tests for utility functions."""

    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
    @given(
        text=st.text(min_size=0, max_size=200),
        citations=st.lists(citation_strategy, max_size=3)
    )
    def test_insert_citation_markers_never_crashes(self, text, citations):
        """insert_citation_markers should never raise an exception for valid types."""
        try:
            result = insert_citation_markers(text, citations)
            assert isinstance(result, str)
            if len(text) > 0 and len(citations) == 0:
                assert result == text
        except Exception as e:
            pytest.fail(f"insert_citation_markers crashed with: {e}")

    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
    @given(
        text=st.text(max_size=200),
        citations=st.lists(citation_strategy, max_size=3)
    )
    def test_insert_citation_markers_preserves_length_invariant(self, text, citations):
        """Result length should be >= original text length."""
        result = insert_citation_markers(text, citations)
        assert len(result) >= len(text)

    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
    @given(
        urls=st.lists(st.text(min_size=1, max_size=50), max_size=10),
        id_val=st.integers(min_value=0, max_value=10000)
    )
    def test_resolve_urls_consistency(self, urls, id_val):
        """resolve_urls should produce consistent output."""
        class MockSite:
            def __init__(self, uri):
                self.web = type('obj', (object,), {'uri': uri})
        
        mock_sites = [MockSite(u) for u in urls]
        
        result = resolve_urls(mock_sites, id_val)
        
        assert isinstance(result, dict)
        assert len(result) <= len(urls)
        
        for val in result.values():
            assert "vertexaisearch.cloud.google.com/id/" in val
            assert str(id_val) in val


class TestResearchToolsProperties:
    """Property-based tests for research tools."""

    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
    @given(search_results=st.lists(search_response_strategy, max_size=5))
    def test_deduplicate_search_results_properties(self, search_results):
        """deduplicate_search_results should handle any valid structure."""
        result = deduplicate_search_results(search_results)
        
        assert isinstance(result, dict)
        
        for url, item in result.items():
            assert isinstance(url, str)
            assert isinstance(item, dict)
            assert item["url"] == url
            
        all_input_urls = set()
        for resp in search_results:
            for res in resp["results"]:
                if res["url"]:  # Only non-empty URLs are processed
                    all_input_urls.add(res["url"])
                
        for url in result:
            assert url in all_input_urls
