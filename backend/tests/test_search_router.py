"""Unit tests for the SearchRouter class.

Tests cover:
- Initialization of providers (Lazy Loading).
- Routing logic (primary vs fallback).
- Error handling and fallback mechanisms.
"""
import pytest
from unittest.mock import MagicMock, patch

# Import SUT
import sys

# MOCK google.genai BEFORE importing search.router to avoid broken environment dependencies
sys.modules["google.genai"] = MagicMock()

from search.router import SearchRouter, SearchProviderType
from search.provider import SearchResult

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
        # Patch the classes at their source module locations because they are imported locally
        with patch("search.providers.google_adapter.GoogleSearchAdapter") as mock_google, \
             patch("search.providers.duckduckgo_adapter.DuckDuckGoAdapter") as mock_ddg, \
             patch("search.providers.brave_adapter.BraveSearchAdapter") as mock_brave, \
             patch("search.providers.tavily_adapter.TavilyAdapter") as mock_tavily, \
             patch("search.providers.bing_adapter.BingAdapter") as mock_bing:

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

    def test_lazy_init_providers(self, mock_config, mock_adapters):
        """Test that providers are NOT initialized on startup (Lazy Loading)."""
        router = SearchRouter(app_config=mock_config)

        # Verify NO adapters were attempted during init
        mock_adapters["google"].assert_not_called()
        mock_adapters["duckduckgo"].assert_not_called()
        mock_adapters["brave"].assert_not_called()
        mock_adapters["tavily"].assert_not_called()
        mock_adapters["bing"].assert_not_called()

        # Verify providers dict is empty
        assert len(router.providers) == 0

    def test_search_triggers_loading(self, mock_config, mock_adapters):
        """Test that search triggers loading of the specific provider."""
        router = SearchRouter(app_config=mock_config)
        mock_config.search_provider = "google"

        # Mock search result
        expected_results = [SearchResult(title="Title", content="test", url="http://test.com")]
        mock_adapters["google"].return_value.search.return_value = expected_results

        # Execute search
        results = router.search("query", max_results=3)

        assert results == expected_results

        # Verify Google was initialized
        mock_adapters["google"].assert_called_once()
        assert "google" in router.providers

        # Verify others were NOT initialized
        mock_adapters["duckduckgo"].assert_not_called()

    def test_search_fallback_on_load_failure(self, mock_config, mock_adapters):
        """Test fallback when primary provider fails to load."""
        router = SearchRouter(app_config=mock_config)
        mock_config.search_provider = "google"
        mock_config.search_fallback = "duckduckgo"

        # Simulate Google instantiation failing (ImportError or similar)
        mock_adapters["google"].side_effect = Exception("Import error")

        expected_results = [SearchResult(title="DDG", content="ddg", url="http://ddg.com")]
        mock_adapters["duckduckgo"].return_value.search.return_value = expected_results

        results = router.search("query")

        assert results == expected_results
        # Google should have been attempted
        mock_adapters["google"].assert_called_once()
        # DDG should have been attempted
        mock_adapters["duckduckgo"].assert_called_once()

        # Verify provider state: google failed to load, so not in providers (or None/failed state)
        # implementation details: we only add to self.providers if successful
        assert "google" not in router.providers
        assert "duckduckgo" in router.providers

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
        """Test switching to fallback provider when primary fails both attempts (runtime error)."""
        router = SearchRouter(app_config=mock_config)
        mock_config.search_provider = "google"
        mock_config.search_fallback = "duckduckgo"

        google_mock = mock_adapters["google"].return_value
        ddg_mock = mock_adapters["duckduckgo"].return_value

        # Google fails twice (runtime search error, not load error)
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

        # Ensure all adapters fail to load
        mock_adapters["google"].side_effect = Exception("Fail")
        mock_adapters["duckduckgo"].side_effect = Exception("Fail")
        mock_adapters["brave"].side_effect = Exception("Fail")
        mock_adapters["tavily"].side_effect = Exception("Fail")
        mock_adapters["bing"].side_effect = Exception("Fail")

        with pytest.raises(ValueError, match="No valid search provider available"):
            router.search("query")
