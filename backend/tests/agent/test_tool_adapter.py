"""Unit tests for the Gemma Tool Adapter."""

import json
import unittest
from typing import List

from langchain_core.tools import tool
from agent.tool_adapter import format_tools_to_json_schema, parse_tool_calls

class TestGemmaToolAdapter(unittest.TestCase):

    def setUp(self):
        @tool
        def get_weather(location: str):
            """Get the weather for a location."""
            return f"Weather in {location}"

        @tool
        def calculator(expression: str):
            """Calculate a math expression."""
            return eval(expression)

        self.tools = [get_weather, calculator]

    def test_format_tools_to_json_schema(self):
        schema_str = format_tools_to_json_schema(self.tools)
        schemas = json.loads(schema_str)

        self.assertEqual(len(schemas), 2)
        self.assertEqual(schemas[0]["name"], "get_weather")
        self.assertIn("parameters", schemas[0])
        self.assertEqual(schemas[1]["name"], "calculator")

    def test_parse_tool_calls_valid_markdown(self):
        content = """
        Here is the plan.
        ```json
        {
          "tool_calls": [
            {
              "name": "get_weather",
              "arguments": {
                "location": "Paris"
              }
            }
          ]
        }
        ```
        """
        calls = parse_tool_calls(content)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["name"], "get_weather")
        self.assertEqual(calls[0]["args"]["location"], "Paris")
        self.assertTrue(calls[0]["id"].startswith("call_"))

    def test_parse_tool_calls_raw_json(self):
        content = """
        {
          "tool_calls": [
            {
              "name": "calculator",
              "arguments": {
                "expression": "2 + 2"
              }
            }
          ]
        }
        """
        calls = parse_tool_calls(content)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["name"], "calculator")
        self.assertEqual(calls[0]["args"]["expression"], "2 + 2")

    def test_parse_tool_calls_single_object(self):
        # Test case where model outputs just the tool object instead of nested list
        content = """
        ```json
        {
          "name": "get_weather",
          "arguments": {
            "location": "London"
          }
        }
        ```
        """
        calls = parse_tool_calls(content)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["name"], "get_weather")
        self.assertEqual(calls[0]["args"]["location"], "London")

    def test_parse_tool_calls_malformed(self):
        content = """
        ```json
        { "name": "broken", "arguments": {
        ```
        """
        calls = parse_tool_calls(content)
        self.assertEqual(len(calls), 0)

    def test_parse_tool_calls_no_calls(self):
        content = "Just some text response."
        calls = parse_tool_calls(content)
        self.assertEqual(len(calls), 0)

if __name__ == "__main__":
    unittest.main()
