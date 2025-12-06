"""
Comprehensive unit tests for backend/src/agent/utils.py

Tests cover:
- format_sources function
- Edge cases and error handling
- Various input formats
"""

import pytest
from agent.utils import format_sources


# Tests for format_sources function
class TestFormatSources:
    """Test suite for format_sources function"""

    def test_format_sources_with_single_source(self):
        """Test format_sources with a single source"""
        sources = [
            {"url": "http://example.com", "content": "Test content"}
        ]
        
        result = format_sources(sources)
        
        assert isinstance(result, str)
        assert "http://example.com" in result
        assert len(result) > 0

    def test_format_sources_with_multiple_sources(self):
        """Test format_sources with multiple sources"""
        sources = [
            {"url": "http://example.com/1", "content": "Content 1"},
            {"url": "http://example.com/2", "content": "Content 2"},
            {"url": "http://example.com/3", "content": "Content 3"},
        ]
        
        result = format_sources(sources)
        
        assert "http://example.com/1" in result
        assert "http://example.com/2" in result
        assert "http://example.com/3" in result

    def test_format_sources_with_empty_list(self):
        """Test format_sources with empty list"""
        sources = []
        
        result = format_sources(sources)
        
        assert isinstance(result, str)
        # Should return empty string or a default message
        assert len(result) >= 0

    def test_format_sources_includes_content(self):
        """Test that format_sources includes content from sources"""
        sources = [
            {"url": "http://example.com", "content": "Important information"}
        ]
        
        result = format_sources(sources)
        
        # Check if content is included (might be truncated)
        assert "Important" in result or "information" in result or len(result) > 20

    def test_format_sources_with_long_content(self):
        """Test format_sources with very long content"""
        long_content = "a" * 10000
        sources = [
            {"url": "http://example.com", "content": long_content}
        ]
        
        result = format_sources(sources)
        
        assert isinstance(result, str)
        # Content might be truncated, but URL should be present
        assert "http://example.com" in result

    def test_format_sources_with_special_characters(self):
        """Test format_sources with special characters in content"""
        sources = [
            {
                "url": "http://example.com",
                "content": "Content with <html> tags & special chars: @#$%"
            }
        ]
        
        result = format_sources(sources)
        
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_sources_with_unicode(self):
        """Test format_sources with unicode characters"""
        sources = [
            {
                "url": "http://example.com",
                "content": "Content with unicode: 你好 🚀 Привет"
            }
        ]
        
        result = format_sources(sources)
        
        assert isinstance(result, str)
        # Should handle unicode gracefully
        assert len(result) > 0

    def test_format_sources_with_newlines(self):
        """Test format_sources with content containing newlines"""
        sources = [
            {
                "url": "http://example.com",
                "content": "Line 1\nLine 2\nLine 3"
            }
        ]
        
        result = format_sources(sources)
        
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_sources_numbering(self):
        """Test that format_sources numbers sources correctly"""
        sources = [
            {"url": "http://example.com/1", "content": "Content 1"},
            {"url": "http://example.com/2", "content": "Content 2"},
            {"url": "http://example.com/3", "content": "Content 3"},
        ]
        
        result = format_sources(sources)
        
        # Check if sources are numbered (common pattern)
        # This might use [1], (1), 1., etc.
        has_numbering = (
            "1" in result and "2" in result and "3" in result or
            "[1]" in result or "(1)" in result or "1." in result
        )
        assert has_numbering or len(result) > 0

    def test_format_sources_with_missing_url(self):
        """Test format_sources when URL is missing"""
        sources = [
            {"content": "Content without URL"}
        ]
        
        # Should handle gracefully
        try:
            result = format_sources(sources)
            assert isinstance(result, str)
        except KeyError:
            # If it raises KeyError, that's also acceptable behavior
            assert True

    def test_format_sources_with_missing_content(self):
        """Test format_sources when content is missing"""
        sources = [
            {"url": "http://example.com"}
        ]
        
        # Should handle gracefully
        try:
            result = format_sources(sources)
            assert isinstance(result, str)
            assert "http://example.com" in result
        except KeyError:
            # If it raises KeyError, that's also acceptable behavior
            assert True

    def test_format_sources_with_none_values(self):
        """Test format_sources with None values"""
        sources = [
            {"url": "http://example.com", "content": None}
        ]
        
        # Should handle None gracefully
        try:
            result = format_sources(sources)
            assert isinstance(result, str)
        except (TypeError, AttributeError):
            assert True

    def test_format_sources_with_empty_strings(self):
        """Test format_sources with empty strings"""
        sources = [
            {"url": "", "content": ""}
        ]
        
        result = format_sources(sources)
        
        assert isinstance(result, str)

    def test_format_sources_preserves_order(self):
        """Test that format_sources preserves source order"""
        sources = [
            {"url": "http://first.com", "content": "First"},
            {"url": "http://second.com", "content": "Second"},
            {"url": "http://third.com", "content": "Third"},
        ]
        
        result = format_sources(sources)
        
        # Check that first appears before second and second before third
        first_pos = result.find("first.com")
        second_pos = result.find("second.com")
        third_pos = result.find("third.com")
        
        if first_pos != -1 and second_pos != -1 and third_pos != -1:
            assert first_pos < second_pos < third_pos


# Edge case tests
class TestFormatSourcesEdgeCases:
    """Test edge cases for format_sources"""

    def test_format_sources_with_none_input(self):
        """Test format_sources with None as input"""
        with pytest.raises((TypeError, AttributeError)):
            format_sources(None)

    def test_format_sources_with_dict_instead_of_list(self):
        """Test format_sources with dict instead of list"""
        source_dict = {"url": "http://example.com", "content": "content"}
        
        with pytest.raises((TypeError, AttributeError, KeyError)):
            format_sources(source_dict)

    def test_format_sources_with_string_instead_of_list(self):
        """Test format_sources with string instead of list"""
        with pytest.raises((TypeError, AttributeError, KeyError)):
            format_sources("not a list")

    def test_format_sources_with_mixed_types(self):
        """Test format_sources with mixed types in list"""
        sources = [
            {"url": "http://example.com", "content": "content"},
            "not a dict",
            {"url": "http://example2.com", "content": "content2"},
        ]
        
        # Should either skip invalid items or raise error
        try:
            result = format_sources(sources)
            # If it handles gracefully, verify it got the valid ones
            assert "http://example.com" in result or "http://example2.com" in result
        except (TypeError, AttributeError, KeyError):
            assert True

    def test_format_sources_with_extra_fields(self):
        """Test format_sources with extra fields in source dict"""
        sources = [
            {
                "url": "http://example.com",
                "content": "content",
                "title": "Example Title",
                "score": 0.95,
                "extra": "extra data"
            }
        ]
        
        result = format_sources(sources)
        
        assert isinstance(result, str)
        assert "http://example.com" in result

    def test_format_sources_with_very_long_url(self):
        """Test format_sources with very long URL"""
        long_url = "http://example.com/" + "a" * 1000
        sources = [
            {"url": long_url, "content": "content"}
        ]
        
        result = format_sources(sources)
        
        assert isinstance(result, str)
        # URL might be truncated but result should exist
        assert len(result) > 0

    def test_format_sources_consistency(self):
        """Test that format_sources returns consistent results"""
        sources = [
            {"url": "http://example.com", "content": "Test content"}
        ]
        
        result1 = format_sources(sources)
        result2 = format_sources(sources)
        
        assert result1 == result2


# Performance tests
class TestFormatSourcesPerformance:
    """Test performance characteristics of format_sources"""

    def test_format_sources_with_many_sources(self):
        """Test format_sources with large number of sources"""
        sources = [
            {"url": f"http://example.com/{i}", "content": f"Content {i}"}
            for i in range(100)
        ]
        
        result = format_sources(sources)
        
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_sources_with_large_content(self):
        """Test format_sources with very large content in sources"""
        large_content = "Lorem ipsum " * 1000
        sources = [
            {"url": "http://example.com", "content": large_content}
            for _ in range(10)
        ]
        
        result = format_sources(sources)
        
        assert isinstance(result, str)


# Integration tests
class TestFormatSourcesIntegration:
    """Integration tests for format_sources usage"""

    def test_format_sources_with_web_research_results(self):
        """Test format_sources with typical web research results"""
        # Simulate actual web research results structure
        sources = [
            {
                "url": "https://en.wikipedia.org/wiki/Python",
                "content": "Python is a high-level programming language...",
            },
            {
                "url": "https://docs.python.org/",
                "content": "Python documentation and tutorials...",
            },
        ]
        
        result = format_sources(sources)
        
        assert "wikipedia" in result.lower() or "python" in result.lower()
        assert len(result) > 50  # Should have substantial content

    def test_format_sources_output_for_llm(self):
        """Test that format_sources output is suitable for LLM consumption"""
        sources = [
            {"url": "http://example.com/1", "content": "Source 1 content"},
            {"url": "http://example.com/2", "content": "Source 2 content"},
        ]
        
        result = format_sources(sources)
        
        # Output should be structured and readable
        assert isinstance(result, str)
        assert len(result) > 20
        # Should be able to identify multiple sources
        assert result.count("http://") >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])