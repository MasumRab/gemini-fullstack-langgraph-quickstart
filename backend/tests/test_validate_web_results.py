import pathlib
import sys

import pytest
from langchain_core.runnables import RunnableConfig

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from agent.nodes import validate_web_results  # noqa: E402


def test_validate_web_results_filters_irrelevant_summary():
    state = {
        "search_query": ["quantum computing advancements"],
        "web_research_result": [
            "Quantum breakthroughs in error correction were announced.",
            "Celebrity gossip unrelated to science.",
        ],
    }
    config = RunnableConfig(configurable={})

    result = validate_web_results(state, config)

    assert result["validated_web_research_result"] == [
        "Quantum breakthroughs in error correction were announced."
    ]
    # The note usually says "Result X filtered..."
    assert "Result 2 filtered" in " ".join(result["validation_notes"])


def test_validate_web_results_falls_back_when_no_matches():
    summaries = ["Generic summary with no overlap."]
    # Provide a query that definitely doesn't match the summary
    state = {"search_query": ["specific topic"], "web_research_result": summaries}
    config = RunnableConfig(configurable={})

    result = validate_web_results(state, config)

    # Should retain the original if nothing matches (safeguard)
    assert result["validated_web_research_result"] == summaries
    assert any("All summaries failed" in note for note in result["validation_notes"])


def test_validate_web_results_handles_missing_summaries():
    state = {"search_query": ["ai"], "web_research_result": []}
    config = RunnableConfig(configurable={})

    result = validate_web_results(state, config)

    assert result["validated_web_research_result"] == []
    assert result["validation_notes"] == [
        "No web research summaries available for validation."
    ]
