import pathlib
import sys

import pytest

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

    result = validate_web_results(state)

    assert result["validated_web_research_result"] == [
        "Quantum breakthroughs in error correction were announced."
    ]
    assert "Celebrity" in " ".join(result["validation_notes"])


def test_validate_web_results_falls_back_when_no_matches():
    summaries = ["Generic summary with no overlap."]
    state = {"search_query": [], "web_research_result": summaries}

    result = validate_web_results(state)

    assert result["validated_web_research_result"] == summaries
    assert any("All summaries failed" in note for note in result["validation_notes"])


def test_validate_web_results_handles_missing_summaries():
    state = {"search_query": ["ai"], "web_research_result": []}

    result = validate_web_results(state)

    assert result["validated_web_research_result"] == []
    assert result["validation_notes"] == [
        "No web research summaries available for validation."
    ]
