from unittest.mock import Mock, patch

import pytest

from agent.rag_nodes import rag_retrieve


@pytest.fixture
def mock_rag_state():
    return {
        "messages": [{"content": "What is RAG?"}],
        "rag_resources": ["uri1"],
        "rag_documents": [],
    }


class TestRagNodes:
    @patch("agent.rag_nodes.is_rag_enabled")
    @patch("agent.rag_nodes.create_rag_tool")
    @patch("agent.rag_nodes._lazy_import_state_utils")
    def test_rag_retrieve_success(
        self, mock_lazy_import, mock_create_tool, mock_enabled, mock_rag_state
    ):
        # Setup mocks
        mock_enabled.return_value = True

        # Mock lazy import return values: (OverallState, create_rag_resources, get_research_topic)
        mock_create_res = Mock(return_value=["res1"])
        mock_get_topic = Mock(return_value="RAG")
        mock_lazy_import.return_value = (Mock(), mock_create_res, mock_get_topic)

        # Mock tool invocation
        mock_tool = Mock()
        mock_tool.invoke.return_value = "Retrieved Document Content"
        mock_create_tool.return_value = mock_tool

        # Execute
        result = rag_retrieve(mock_rag_state, config=None)

        # Verify
        assert "rag_documents" in result
        assert len(result["rag_documents"]) == 1
        assert result["rag_documents"][0] == "Retrieved Document Content"
        assert result["rag_enabled"] is True

    @patch("agent.rag_nodes.is_rag_enabled")
    @patch("agent.rag_nodes._lazy_import_state_utils")
    def test_rag_retrieve_disabled(
        self, mock_lazy_import, mock_enabled, mock_rag_state
    ):
        mock_enabled.return_value = False
        # Setup lazy import just in case, though it shouldn't be reached if enabled check is first
        mock_lazy_import.return_value = (Mock(), Mock(), Mock())

        result = rag_retrieve(mock_rag_state, config=None)

        assert "rag_documents" in result
        assert result["rag_documents"] == []
        assert result["rag_enabled"] is False

    @patch("agent.rag_nodes.is_rag_enabled")
    @patch("agent.rag_nodes.create_rag_tool")
    @patch("agent.rag_nodes._lazy_import_state_utils")
    def test_rag_retrieve_no_results(
        self, mock_lazy_import, mock_create_tool, mock_enabled, mock_rag_state
    ):
        mock_enabled.return_value = True
        # Ensure create_rag_resources returns a list so len() works
        mock_create_resources = Mock(return_value=["res1"])
        mock_lazy_import.return_value = (
            Mock(),
            mock_create_resources,
            Mock(return_value="topic"),
        )

        mock_tool = Mock()
        mock_tool.invoke.return_value = "No relevant information found"
        mock_create_tool.return_value = mock_tool

        result = rag_retrieve(mock_rag_state, config=None)

        assert result["rag_documents"] == []
