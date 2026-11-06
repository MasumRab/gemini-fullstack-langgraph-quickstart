import pathlib
import sys
from types import SimpleNamespace

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from agent import rag_nodes  # noqa: E402


def test_rag_retrieve_skips_when_rag_disabled(monkeypatch):
    monkeypatch.setattr(rag_nodes, "is_rag_enabled", lambda: False)

    result = rag_nodes.rag_retrieve({"messages": []}, config=None)

    assert result == {"rag_documents": [], "rag_enabled": False}


def test_should_use_rag_prefers_rag_when_resources_present(monkeypatch):
    monkeypatch.setattr(rag_nodes, "is_rag_enabled", lambda: True)
    monkeypatch.setattr(rag_nodes, "rag_config", SimpleNamespace(enabled=False))

    state = {"rag_resources": ["s3://bucket/doc"]}

    assert rag_nodes.should_use_rag(state) == "rag_retrieve"


def test_should_use_rag_routes_to_web_when_disabled(monkeypatch):
    monkeypatch.setattr(rag_nodes, "is_rag_enabled", lambda: False)
    monkeypatch.setattr(rag_nodes, "rag_config", SimpleNamespace(enabled=False))

    assert rag_nodes.should_use_rag({}) == "web_research"


def test_rag_fallback_to_web_handles_continue_iterations(monkeypatch):
    monkeypatch.setattr(rag_nodes, "rag_config", SimpleNamespace(enable_fallback=False))

    assert (
        rag_nodes.rag_fallback_to_web(
            {"research_loop_count": 1, "rag_documents": ["doc"]}
        )
        == "web_research"
    )


def test_rag_fallback_to_web_respects_enable_fallback(monkeypatch):
    monkeypatch.setattr(rag_nodes, "rag_config", SimpleNamespace(enable_fallback=True))

    state = {"research_loop_count": 0, "rag_documents": ["doc"]}

    assert rag_nodes.rag_fallback_to_web(state) == "web_research"


def test_rag_fallback_to_web_goes_to_reflection_when_no_fallback(monkeypatch):
    monkeypatch.setattr(rag_nodes, "rag_config", SimpleNamespace(enable_fallback=False))

    state = {"research_loop_count": 0, "rag_documents": ["doc"]}

    assert rag_nodes.rag_fallback_to_web(state) == "reflection"
