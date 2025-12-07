"""Unit tests for research_tools module.

Tests cover search functions, summarization, deduplication, and tool definitions.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_get_today_str_format(self):
        """Should return date in expected format."""
        from agent.research_tools import get_today_str
        
        result = get_today_str()
        
        # Should be non-empty and contain expected components
        assert len(result) > 0
        # Format is "Sun Dec 08, 2024" - contains comma and year
        assert "," in result
        assert "20" in result  # Year prefix

    def test_get_tavily_api_key_from_config(self):
        """Should retrieve API key from config."""
        from agent.research_tools import get_tavily_api_key
        
        config = {"configurable": {"tavily_api_key": "test-key-123"}}
        result = get_tavily_api_key(config)
        
        assert result == "test-key-123"

    def test_get_tavily_api_key_from_env(self, monkeypatch):
        """Should fall back to environment variable."""
        from agent.research_tools import get_tavily_api_key
        
        monkeypatch.setenv("TAVILY_API_KEY", "env-key-456")
        result = get_tavily_api_key(None)
        
        assert result == "env-key-456"

    def test_get_tavily_api_key_raises_when_missing(self, monkeypatch):
        """Should raise ValueError when no key found."""
        from agent.research_tools import get_tavily_api_key
        
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        
        with pytest.raises(ValueError, match="Tavily API key not found"):
            get_tavily_api_key({})


class TestDeduplication:
    """Tests for search result deduplication."""

    def test_deduplicate_removes_duplicate_urls(self):
        """Should keep only first occurrence of each URL."""
        from agent.research_tools import deduplicate_search_results
        
        search_results = [
            {
                "query": "query1",
                "results": [
                    {"url": "http://example.com/a", "title": "Title A"},
                    {"url": "http://example.com/b", "title": "Title B"},
                ]
            },
            {
                "query": "query2",
                "results": [
                    {"url": "http://example.com/a", "title": "Title A duplicate"},
                    {"url": "http://example.com/c", "title": "Title C"},
                ]
            }
        ]
        
        result = deduplicate_search_results(search_results)
        
        assert len(result) == 3
        assert "http://example.com/a" in result
        assert "http://example.com/b" in result
        assert "http://example.com/c" in result
        # First occurrence should be kept
        assert result["http://example.com/a"]["title"] == "Title A"

    def test_deduplicate_handles_empty_results(self):
        """Should handle empty results gracefully."""
        from agent.research_tools import deduplicate_search_results
        
        result = deduplicate_search_results([])
        assert result == {}

    def test_deduplicate_handles_missing_results_key(self):
        """Should handle responses without 'results' key."""
        from agent.research_tools import deduplicate_search_results
        
        search_results = [{"query": "test"}]  # No results key
        result = deduplicate_search_results(search_results)
        
        assert result == {}


class TestProcessSearchResults:
    """Tests for search result processing."""

    def test_process_uses_content_when_no_raw(self):
        """Should use 'content' when 'raw_content' is missing."""
        from agent.research_tools import process_search_results
        
        unique_results = {
            "http://example.com": {
                "title": "Test Title",
                "content": "Short snippet",
            }
        }
        
        result = process_search_results(unique_results)
        
        assert result["http://example.com"]["content"] == "Short snippet"
        assert result["http://example.com"]["title"] == "Test Title"

    def test_process_truncates_raw_content_without_model(self):
        """Should truncate raw_content when no summarization model."""
        from agent.research_tools import process_search_results
        
        long_content = "x" * 300000  # Very long content
        unique_results = {
            "http://example.com": {
                "title": "Test",
                "content": "Short",
                "raw_content": long_content,
            }
        }
        
        result = process_search_results(unique_results, max_content_length=1000)
        
        assert len(result["http://example.com"]["content"]) == 1000

    def test_process_handles_empty_input(self):
        """Should handle empty input."""
        from agent.research_tools import process_search_results
        
        result = process_search_results({})
        assert result == {}


class TestFormatSearchOutput:
    """Tests for search output formatting."""

    def test_format_produces_structured_output(self):
        """Should produce well-formatted output."""
        from agent.research_tools import format_search_output
        
        summarized_results = {
            "http://example.com/a": {"title": "Article A", "content": "Summary A"},
            "http://example.com/b": {"title": "Article B", "content": "Summary B"},
        }
        
        result = format_search_output(summarized_results)
        
        assert "SOURCE 1:" in result
        assert "SOURCE 2:" in result
        assert "Article A" in result
        assert "Article B" in result
        assert "http://example.com/a" in result
        assert "Summary A" in result

    def test_format_handles_empty_results(self):
        """Should return appropriate message for empty results."""
        from agent.research_tools import format_search_output
        
        result = format_search_output({})
        
        assert "No valid search results" in result


class TestSummarization:
    """Tests for webpage summarization."""

    def test_summarize_handles_model_exception(self):
        """Should return truncated content on model failure."""
        from agent.research_tools import summarize_webpage_content
        
        mock_model = Mock()
        mock_model.invoke.side_effect = Exception("Model error")
        
        long_content = "x" * 2000
        result = summarize_webpage_content(mock_model, long_content)
        
        assert len(result) < len(long_content)
        assert result.endswith("...")

    def test_summarize_returns_short_content_on_error(self):
        """Should return full content if short enough on error."""
        from agent.research_tools import summarize_webpage_content
        
        mock_model = Mock()
        mock_model.invoke.side_effect = Exception("Model error")
        
        short_content = "Short content"
        result = summarize_webpage_content(mock_model, short_content)
        
        assert result == short_content

    def test_summarize_handles_structured_output(self):
        """Should format structured output correctly."""
        from agent.research_tools import summarize_webpage_content
        
        mock_summary = Mock()
        mock_summary.summary = "This is the summary"
        mock_summary.key_excerpts = "Key excerpt 1"
        
        mock_model = Mock()
        mock_model.invoke.return_value = mock_summary
        
        result = summarize_webpage_content(mock_model, "Test content")
        
        assert "<summary>" in result
        assert "This is the summary" in result
        assert "<key_excerpts>" in result


class TestThinkTool:
    """Tests for the think_tool."""

    def test_think_tool_returns_reflection(self):
        """Should return formatted reflection."""
        from agent.research_tools import think_tool
        
        result = think_tool.invoke({"reflection": "I found key information about X"})
        
        assert "Reflection recorded:" in result
        assert "key information about X" in result


class TestTokenLimitDetection:
    """Tests for token limit detection."""

    def test_detects_token_limit_error(self):
        """Should detect common token limit error messages."""
        from agent.research_tools import is_token_limit_exceeded
        
        cases = [
            Exception("token limit exceeded"),
            Exception("Maximum context length is 128000"),
            Exception("Please reduce the length of your prompt"),
            Exception("prompt is too long"),
            Exception("resource exhausted: quota exceeded"),
        ]
        
        for exc in cases:
            assert is_token_limit_exceeded(exc) is True

    def test_returns_false_for_other_errors(self):
        """Should return False for non-token-limit errors."""
        from agent.research_tools import is_token_limit_exceeded
        
        cases = [
            Exception("Network error"),
            Exception("Authentication failed"),
            Exception("Invalid API key"),
        ]
        
        for exc in cases:
            assert is_token_limit_exceeded(exc) is False


class TestModelTokenLimits:
    """Tests for model token limit lookup."""

    def test_get_known_model_limit(self):
        """Should return correct limit for known models."""
        from agent.research_tools import get_model_token_limit
        
        assert get_model_token_limit("gemini-1.5-pro") == 2097152
        assert get_model_token_limit("openai:gpt-4o") == 128000

    def test_get_unknown_model_returns_default(self):
        """Should return default for unknown models."""
        from agent.research_tools import get_model_token_limit
        
        result = get_model_token_limit("unknown-model-xyz")
        assert result == 128000  # Default


class TestTavilySearchWithMock:
    """Tests for Tavily search with mocked client."""

    @patch('agent.research_tools.TAVILY_AVAILABLE', False)
    def test_search_returns_empty_when_tavily_unavailable(self):
        """Should return empty results when Tavily not installed."""
        from agent.research_tools import tavily_search_multiple
        
        result = tavily_search_multiple(["test query"])
        
        assert result == []
