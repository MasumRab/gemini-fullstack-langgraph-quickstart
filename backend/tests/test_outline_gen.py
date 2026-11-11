import json
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from agent.models import TEST_MODEL
from agent.nodes import outline_gen
from agent.tools_and_schemas import Outline


@pytest.fixture
def config():
    """Basic runnable config"""
    return RunnableConfig(
        configurable={
            "model": TEST_MODEL,
            "query_generator_model": TEST_MODEL,
            "max_loops": 3,
            "num_queries": 3,
            "require_planning_confirmation": False,
            "answer_model": TEST_MODEL,
        }
    )


@pytest.fixture
def base_state():
    """Minimal valid state for graph node tests."""
    return {
        "messages": [HumanMessage(content="User: test research topic")],
        "search_query": ["test query"],
        "planning_status": None,
        "planning_feedback": [],
        "web_research_result": [],
        "validated_web_research_result": [],
        "validation_notes": [],
        "sources_gathered": [],
        "research_loop_count": 0,
    }


class TestOutlineGen:
    """Test suite for outline_gen node"""

    @patch("agent.nodes._get_rate_limited_llm")
    def test_outline_gen_structured_output(self, mock_get_llm, base_state, config):
        """Test outline generation with structured output path (non-Gemma)."""
        config["configurable"]["query_generator_model"] = "gemini-2.5-pro"

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        mock_structured_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm

        expected_outline = {
            "title": "Test Title",
            "sections": [
                {
                    "title": "Test Section",
                    "subsections": [
                        {"title": "Test Subsection", "description": "Test Desc"}
                    ],
                }
            ],
        }
        mock_structured_llm.invoke.return_value = expected_outline

        result = outline_gen(base_state, config)

        assert "outline" in result
        assert result["outline"] == expected_outline
        mock_llm.with_structured_output.assert_called_once_with(Outline)
        mock_structured_llm.invoke.assert_called_once()

    @patch("agent.nodes._get_rate_limited_llm")
    def test_outline_gen_gemma_path(self, mock_get_llm, base_state, config):
        """Test outline generation with Gemma manual JSON parsing path."""
        config["configurable"]["query_generator_model"] = "gemma-3-27b-it"

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        expected_outline = {
            "title": "Gemma Title",
            "sections": [
                {
                    "title": "Gemma Section",
                    "subsections": [
                        {"title": "Gemma Subsection", "description": "Gemma Desc"}
                    ],
                }
            ],
        }
        json_str = json.dumps(expected_outline)
        mock_llm.invoke.return_value = AIMessage(
            content=f"Here is the outline:\n```json\n{json_str}\n```"
        )

        result = outline_gen(base_state, config)

        assert "outline" in result
        assert result["outline"] == expected_outline
        mock_llm.invoke.assert_called_once()

    @patch("agent.nodes._get_rate_limited_llm")
    def test_outline_gen_gemma_malformed_output(self, mock_get_llm, base_state, config):
        """Test fallback behavior when Gemma outputs malformed content."""
        config["configurable"]["query_generator_model"] = "gemma-3-27b-it"
        base_state["messages"] = [HumanMessage(content="test research topic")]

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        mock_llm.invoke.return_value = AIMessage(content="No JSON here.")

        result = outline_gen(base_state, config)

        assert "outline" in result
        outline = result["outline"]
        assert outline["title"] == "test research topic"
        assert len(outline["sections"]) == 3
        section_titles = [s["title"] for s in outline["sections"]]
        assert section_titles == ["Introduction", "Analysis", "Conclusion"]

    @patch("agent.nodes.logger.error")
    @patch("agent.nodes._get_rate_limited_llm")
    def test_outline_gen_structured_output_raises(
        self, mock_get_llm, mock_logger_error, base_state, config
    ):
        """Test fallback behavior when structured output raises an exception."""
        config["configurable"]["query_generator_model"] = "gemini-2.5-pro"
        base_state["messages"] = [HumanMessage(content="test research topic")]

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        mock_structured_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_structured_llm.invoke.side_effect = Exception("API Error")

        result = outline_gen(base_state, config)

        assert "outline" in result
        outline = result["outline"]
        assert outline["title"] == "test research topic"
        assert len(outline["sections"]) == 3
        section_titles = [s["title"] for s in outline["sections"]]
        assert section_titles == ["Introduction", "Analysis", "Conclusion"]
        mock_logger_error.assert_called_once()

    def test_outline_gen_registry_contract(self):
        """Test that outline_gen is properly registered in graph_registry."""
        from agent.nodes import graph_registry

        node_meta = graph_registry.node_docs.get("outline_gen")
        assert node_meta is not None
        assert "outline" in node_meta.get("outputs", [])

    @patch("agent.nodes._get_rate_limited_llm")
    def test_outline_gen_empty_messages(self, mock_get_llm, base_state, config):
        """Test outline_gen behavior with an empty messages list."""
        config["configurable"]["query_generator_model"] = "gemma-3-27b-it"
        base_state["messages"] = []

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        # Trigger fallback by raising an exception
        mock_llm.invoke.side_effect = Exception("Force fallback")

        result = outline_gen(base_state, config)

        assert "outline" in result
        outline = result["outline"]
        assert outline["title"] == ""
        assert len(outline["sections"]) == 3
        section_titles = [s["title"] for s in outline["sections"]]
        assert section_titles == ["Introduction", "Analysis", "Conclusion"]
