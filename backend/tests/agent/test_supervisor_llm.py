import dataclasses
from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from agent.graphs import supervisor
from agent.graphs.supervisor import compress_context


@pytest.fixture
def enable_compression():
    """Enable compression for testing."""
    original_config = supervisor.app_config
    new_config = dataclasses.replace(
        original_config,
        compression_enabled=True,
        compression_mode="tiered"
    )

    with patch("agent.graphs.supervisor.app_config", new_config):
        yield

@patch("agent.graphs.supervisor.get_cached_llm")
def test_compress_context_with_llm(mock_get_llm, enable_compression):
    """Test compress_context with LLM enabled uses get_cached_llm."""

    # Setup Mock LLM
    mock_llm = mock_get_llm.return_value
    mock_llm.invoke.return_value = AIMessage(content="Compressed Summary")

    state = {
        "web_research_result": ["Old Result"],
        "validated_web_research_result": ["New Result"]
    }
    config = RunnableConfig()

    # Execute
    result = compress_context(state, config)

    # Assert
    assert result["web_research_result"] == ["Compressed Summary"]

    # Verify get_cached_llm was called correctly
    mock_get_llm.assert_called_once()

    # Verify LLM invoke was called
    mock_llm.invoke.assert_called_once()
