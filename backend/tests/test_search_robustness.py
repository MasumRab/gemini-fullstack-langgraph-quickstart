
"""Unit tests for search checking robustness against malformed or edge-case external data.

These tests ensure that the agent's search tools do not crash when external APIs return
unexpected structures, empty strings, or partial data.
"""
from agent.research_tools import (
    deduplicate_search_results,
    format_search_output,
    process_search_results,
)


class TestSearchRobustness:
    
    def test_deduplicate_missing_keys(self):
        """Test resilience against missing 'url' or 'results' keys in API response."""
        # Scenario: API returns a 200 OK but the structure is missing 'results'
        malformed_response = [{"status": "ok", "metadata": "something"}] 
        assert deduplicate_search_results(malformed_response) == {}

        # Scenario: 'results' exists but items abstract 'url'
        missing_url_response = [{
            "query": "test", 
            "results": [{"title": "Good title", "content": "Good content"}] # No URL
        }]
        assert deduplicate_search_results(missing_url_response) == {}

    def test_deduplicate_mixed_quality(self):
        """Test that we salvage valid items even if some are broken."""
        mixed_response = [{
            "query": "test",
            "results": [
                {"title": "Bad Item"}, # Missing URL
                {"url": "http://ok.com", "title": "Good Item"},
                {"url": None, "title": "Null URL"}
            ]
        }]
        result = deduplicate_search_results(mixed_response)
        assert len(result) == 1
        assert "http://ok.com" in result

    def test_process_search_results_empty_content(self):
        """Test handling of results with empty strings for content/raw_content."""
        input_data = {
            "http://empty.com": {
                "title": "Empty Page",
                "content": "",
                "raw_content": ""
            },
            "http://partial.com": {
                "title": "Partial Page",
                "content": "Snippet",
                "raw_content": None
            }
        }
        
        # Should not crash, should preserve what it has
        processed = process_search_results(input_data)
        
        assert processed["http://empty.com"]["content"] == ""
        assert processed["http://partial.com"]["content"] == "Snippet"

    def test_format_search_output_special_chars(self):
        """Test formatting handles special characters or massive strings gracefully."""
        input_data = {
            "http://test.com": {
                "title": "Title with \n newlines and \t tabs",
                "content": "Content with \"quotes\" and emojis 🚀"
            }
        }
        
        output = format_search_output(input_data)
        
        # Verify it remains a string and contains our content
        assert isinstance(output, str)
        assert "🚀" in output
        assert "Title with \n newlines" in output

    def test_process_search_results_sanitization(self):
        """Ensure we don't crash on non-string content (e.g. if API returns dicts in content)."""
        input_data = {
            "http://weird.com": {
                "title": 12345, # Numeric title
                "content": {"nested": "dict"}, # Malformed content
                "raw_content": {"nested": "raw"} # Malformed raw content
            }
        }
        
        # Should proceed without error and convert to string
        result = process_search_results(input_data)
        
        processed = result["http://weird.com"]
        assert isinstance(processed["title"], str)
        assert processed["title"] == "12345"
        assert isinstance(processed["content"], str)
        # raw_content is used if present, converted to string and truncated
        assert "{'nested': 'raw'}" in processed["content"]

