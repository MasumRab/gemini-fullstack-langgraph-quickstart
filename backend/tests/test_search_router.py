"""Unit tests for the SearchRouter class.

Tests cover:
- Initialization of providers.
- Routing logic (primary vs fallback).
- Error handling and fallback mechanisms.
"""
# Import SUT
import sys
from unittest.mock import MagicMock, patch

import pytest

# MOCK google.genai BEFORE importing search.router to avoid broken environment dependencies
# (e.g. pycares/aiohttp issues in current env)
sys.modules["google.genai"] = MagicMock()

from search.provider import SearchResult
from search.router import SearchRouter


class TestSearchRouter:
    """Tests for SearchRouter logic."""

    @pytest.fixture
    def mock_config(self):
        """Mock AppConfig."""
        config = MagicMock()
        config.search_provider = "google"
        config.search_fallback = "duckduckgo"
        return config

    @pytest.fixture
    def mock_adapters(self):
        """Mock the adapter classes used by SearchRouter."""
        # Patch the classes where they are imported in router.py

        with patch("search.router.GoogleSearchAdapter") as mock_google, \
             patch("search.router.DuckDuckGoAdapter") as mock_ddg, \
             patch("search.router.BraveSearchAdapter") as mock_brave, \
             patch("search.router.TavilyAdapter") as mock_tavily, \
             patch("search.router.BingAdapter") as mock_bing:

            # Setup instances
            mock_google.return_value = MagicMock(name="google_instance")
            mock_ddg.return_value = MagicMock(name="ddg_instance")
            mock_brave.return_value = MagicMock(name="brave_instance")
            mock_tavily.return_value = MagicMock(name="tavily_instance")
            mock_bing.return_value = MagicMock(name="bing_instance")

            yield {
                "google": mock_google,
                "duckduckgo": mock_ddg,
                "brave": mock_brave,
                "tavily": mock_tavily,
                "bing": mock_bing
            }

    def test_init_providers(self, mock_config, mock_adapters):
        """Test that providers are initialized correctly."""
        router = SearchRouter(app_config=mock_config)

        # Verify all adapters were attempted
        mock_adapters["google"].assert_called()
        mock_adapters["duckduckgo"].assert_called()
        mock_adapters["brave"].assert_called()
        mock_adapters["tavily"].assert_called()
        mock_adapters["bing"].assert_called()

        # Verify providers dict is populated
        assert "google" in router.providers
        assert "duckduckgo" in router.providers
        assert "brave" in router.providers
        assert "tavily" in router.providers
        assert "bing" in router.providers

    def test_search_primary_success(self, mock_config, mock_adapters):
        """Test search using primary provider successfully."""
        router = SearchRouter(app_config=mock_config)
        mock_config.search_provider = "google"

        expected_results = [SearchResult(title="Title", content="test", url="http://test.com")]
        mock_adapters["google"].return_value.search.return_value = expected_results

        results = router.search("query", max_results=3)

        assert results == expected_results
        mock_adapters["google"].return_value.search.assert_called_with("query", max_results=3, tuned=True)

    def test_search_fallback_on_missing_provider(self, mock_config, mock_adapters):
        """Test fallback when primary provider is not available."""
        router = SearchRouter(app_config=mock_config)

        # Simulate Google not being available (removed from providers dict)
        del router.providers["google"]
        mock_config.search_provider = "google"
        mock_config.search_fallback = "duckduckgo"

        expected_results = [SearchResult(title="DDG", content="ddg", url="http://ddg.com")]
        mock_adapters["duckduckgo"].return_value.search.return_value = expected_results

        results = router.search("query")

        assert results == expected_results
        # Should have called DDG (tuned=True by default in fallback logic implementation)
        mock_adapters["duckduckgo"].return_value.search.assert_called_with("query", max_results=5, tuned=True)

    def test_search_retry_logic(self, mock_config, mock_adapters):
        """Test retry with tuned=False if tuned=True fails."""
        router = SearchRouter(app_config=mock_config)
        mock_config.search_provider = "google"

        provider_mock = mock_adapters["google"].return_value

        # First call fails, second succeeds
        provider_mock.search.side_effect = [Exception("Tuned failed"), [SearchResult(title="Relaxed", content="relaxed", url="http://test.com")]]

        results = router.search("query")

        assert len(results) == 1
        assert results[0].content == "relaxed"

        # Verify calls
        assert provider_mock.search.call_count == 2
        provider_mock.search.assert_any_call("query", max_results=5, tuned=True)
        provider_mock.search.assert_any_call("query", max_results=5, tuned=False)

    def test_search_fallback_execution(self, mock_config, mock_adapters):
        """Test switching to fallback provider when primary fails both attempts."""
        router = SearchRouter(app_config=mock_config)
        mock_config.search_provider = "google"
        mock_config.search_fallback = "duckduckgo"

        google_mock = mock_adapters["google"].return_value
        ddg_mock = mock_adapters["duckduckgo"].return_value

        # Google fails twice
        google_mock.search.side_effect = [Exception("Fail 1"), Exception("Fail 2")]
        # DDG succeeds
        ddg_mock.search.return_value = [SearchResult(title="Fallback", content="fallback", url="http://ddg.com")]

        results = router.search("query")

        assert len(results) == 1
        assert results[0].content == "fallback"

        # Verify Google called twice
        assert google_mock.search.call_count == 2
        # Verify DDG called once
        ddg_mock.search.assert_called_once()

    def test_search_all_fail(self, mock_config, mock_adapters):
        """Test empty list returned when all providers fail."""
        router = SearchRouter(app_config=mock_config)
        mock_config.search_provider = "google"
        mock_config.search_fallback = "duckduckgo"

        google_mock = mock_adapters["google"].return_value
        ddg_mock = mock_adapters["duckduckgo"].return_value

        # Google fails twice
        google_mock.search.side_effect = Exception("Google Fail")
        # DDG fails
        ddg_mock.search.side_effect = Exception("DDG Fail")

        with pytest.raises(Exception, match="DDG Fail"):
            router.search("query")

    def test_search_no_provider_available(self, mock_config, mock_adapters):
        """Test ValueError when no providers are configured/available."""
        router = SearchRouter(app_config=mock_config)
        router.providers.clear() # Simulate no init

        with pytest.raises(ValueError, match="No valid search provider available"):
            router.search("query")
