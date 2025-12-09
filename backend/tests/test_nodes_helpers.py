import unittest
from unittest.mock import Mock, patch
from agent.nodes import _flatten_queries, _keywords_from_queries


class TestFlattenQueries(unittest.TestCase):
    """Comprehensive tests for _flatten_queries helper function."""

    def test_empty_list(self):
        """Test with empty list."""
        result = _flatten_queries([])
        self.assertEqual(result, [])

    def test_flat_list_strings(self):
        """Test with already flat list of strings."""
        queries = ["query1", "query2", "query3"]
        result = _flatten_queries(queries)
        self.assertEqual(result, ["query1", "query2", "query3"])

    def test_single_level_nesting(self):
        """Test with single level of nesting."""
        queries = ["query1", ["query2", "query3"], "query4"]
        result = _flatten_queries(queries)
        self.assertEqual(result, ["query1", "query2", "query3", "query4"])

    def test_deep_nesting(self):
        """Test with deeply nested structure."""
        queries = ["q1", ["q2", ["q3", ["q4", "q5"]]]]
        result = _flatten_queries(queries)
        self.assertEqual(result, ["q1", "q2", "q3", "q4", "q5"])

    def test_mixed_nesting(self):
        """Test with mixed flat and nested elements."""
        queries = ["a", ["b", "c"], "d", ["e", ["f"]], "g"]
        result = _flatten_queries(queries)
        self.assertEqual(result, ["a", "b", "c", "d", "e", "f", "g"])

    def test_empty_nested_lists(self):
        """Test with empty nested lists."""
        queries = ["a", [], "b", [[]], "c"]
        result = _flatten_queries(queries)
        self.assertEqual(result, ["a", "b", "c"])

    def test_single_string(self):
        """Test with single string in list."""
        result = _flatten_queries(["single"])
        self.assertEqual(result, ["single"])

    def test_preserves_order(self):
        """Test that flattening preserves original order."""
        queries = ["first", ["second", "third"], "fourth"]
        result = _flatten_queries(queries)
        self.assertEqual(result, ["first", "second", "third", "fourth"])

    def test_only_nested_lists(self):
        """Test with only nested lists, no flat elements."""
        queries = [["a", "b"], ["c", "d"]]
        result = _flatten_queries(queries)
        self.assertEqual(result, ["a", "b", "c", "d"])

    def test_list_of_single_elements(self):
        """Test with list of single-element lists."""
        queries = [["a"], ["b"], ["c"]]
        result = _flatten_queries(queries)
        self.assertEqual(result, ["a", "b", "c"])


class TestKeywordsFromQueries(unittest.TestCase):
    """Comprehensive tests for _keywords_from_queries helper function."""

    def test_empty_list(self):
        """Test with empty query list."""
        result = _keywords_from_queries([])
        self.assertEqual(result, [])

    def test_single_word_query(self):
        """Test with single word >= 4 characters."""
        queries = ["python"]
        result = _keywords_from_queries(queries)
        self.assertEqual(result, ["python"])

    def test_multiple_words(self):
        """Test with multiple words."""
        queries = ["python programming language"]
        result = _keywords_from_queries(queries)
        self.assertIn("python", result)
        self.assertIn("programming", result)
        self.assertIn("language", result)

    def test_filters_short_words(self):
        """Test that words with less than 4 characters are filtered."""
        queries = ["a big cat ran"]
        result = _keywords_from_queries(queries)
        # "a" (1), "big" (3), "cat" (3), "ran" (3) should all be filtered
        self.assertEqual(result, [])

    def test_exactly_four_chars(self):
        """Test that 4-character words are included."""
        queries = ["test word here"]
        result = _keywords_from_queries(queries)
        self.assertIn("test", result)
        self.assertIn("word", result)
        self.assertIn("here", result)

    def test_case_conversion(self):
        """Test that all keywords are lowercased."""
        queries = ["Python PROGRAMMING Language"]
        result = _keywords_from_queries(queries)
        self.assertIn("python", result)
        self.assertIn("programming", result)
        self.assertIn("language", result)
        # Should not contain uppercase versions
        self.assertNotIn("Python", result)
        self.assertNotIn("PROGRAMMING", result)

    def test_special_characters_split(self):
        """Test that special characters cause word splitting."""
        queries = ["python-programming"]
        result = _keywords_from_queries(queries)
        self.assertIn("python", result)
        self.assertIn("programming", result)

    def test_punctuation_removal(self):
        """Test that punctuation is removed."""
        queries = ["python, programming! language?"]
        result = _keywords_from_queries(queries)
        self.assertIn("python", result)
        self.assertIn("programming", result)
        self.assertIn("language", result)

    def test_numbers_included(self):
        """Test that alphanumeric tokens >= 4 chars are included."""
        queries = ["python3 test123"]
        result = _keywords_from_queries(queries)
        self.assertIn("python3", result)
        self.assertIn("test123", result)

    def test_multiple_queries(self):
        """Test with multiple query strings."""
        queries = ["python programming", "machine learning"]
        result = _keywords_from_queries(queries)
        self.assertIn("python", result)
        self.assertIn("programming", result)
        self.assertIn("machine", result)
        self.assertIn("learning", result)

    def test_duplicate_keywords(self):
        """Test that duplicate keywords appear multiple times."""
        queries = ["python python programming python"]
        result = _keywords_from_queries(queries)
        # Should have multiple "python" entries
        self.assertEqual(result.count("python"), 3)

    def test_empty_string_query(self):
        """Test with empty string in queries."""
        queries = [""]
        result = _keywords_from_queries(queries)
        self.assertEqual(result, [])

    def test_whitespace_only_query(self):
        """Test with whitespace-only query."""
        queries = ["   \t\n  "]
        result = _keywords_from_queries(queries)
        self.assertEqual(result, [])

    def test_unicode_characters(self):
        """Test with unicode characters."""
        queries = ["测试 python 编程"]
        result = _keywords_from_queries(queries)
        # Unicode words should be preserved if >= 4 chars
        self.assertIn("python", result)

    def test_mixed_length_words(self):
        """Test with mix of short and long words."""
        queries = ["a big test of the system"]
        result = _keywords_from_queries(queries)
        self.assertIn("test", result)
        self.assertIn("system", result)
        # Short words should be filtered
        self.assertNotIn("a", result)
        self.assertNotIn("big", result)
        self.assertNotIn("of", result)
        self.assertNotIn("the", result)

    def test_hyphenated_words(self):
        """Test handling of hyphenated words."""
        queries = ["deep-learning neural-networks"]
        result = _keywords_from_queries(queries)
        self.assertIn("deep", result)
        self.assertIn("learning", result)
        self.assertIn("neural", result)
        self.assertIn("networks", result)

    def test_urls_parsed(self):
        """Test that URLs are split into components."""
        queries = ["https://example.com/test"]
        result = _keywords_from_queries(queries)
        # Should extract "https", "example", "test" (all >= 4 chars)
        self.assertIn("https", result)
        self.assertIn("example", result)
        self.assertIn("test", result)

    def test_email_addresses(self):
        """Test handling of email addresses."""
        queries = ["user@example.com"]
        result = _keywords_from_queries(queries)
        # Should split and extract >= 4 char components
        self.assertIn("user", result)
        self.assertIn("example", result)


if __name__ == "__main__":
    unittest.main()