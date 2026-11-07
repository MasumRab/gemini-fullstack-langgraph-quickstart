import pytest
from unittest.mock import patch, MagicMock
from dspy_integration.framework.dispatcher import Dispatcher, select_best_route, DispatchResult
import sys
import importlib

@pytest.fixture
def sample_candidates():
    return [
        {"id": "route_a", "semantic_score": 0.8, "lexical_score": 0.2},
        {"id": "route_b", "semantic_score": 0.4, "lexical_score": 0.9},
        {"id": "route_c", "semantic_score": 0.9, "lexical_score": 0.1},
    ]

_FAKE_MODULES = (
    'dspy_helm',
    'dspy_helm.routing',
    'dspy_helm.routing.intelligent_dispatcher',
)


@pytest.fixture(autouse=True)
def setup_mock_dispatcher():
    """Install a fake ``dspy_helm`` package for exactly one test.

    The fake entries must be removed again on teardown. Leaving them in
    ``sys.modules`` hands a later test in the same process a MagicMock where it
    expected the real package, which turns an import failure into a silently
    passing test.
    """
    saved = {name: sys.modules.get(name) for name in _FAKE_MODULES}
    for name in _FAKE_MODULES:
        if name not in sys.modules:
            sys.modules[name] = MagicMock()

    mock_cls = MagicMock()
    setattr(
        sys.modules['dspy_helm.routing.intelligent_dispatcher'],
        'IntelligentDispatcher',
        mock_cls,
    )

    try:
        yield mock_cls
    finally:
        for name in _FAKE_MODULES:
            previous = saved[name]
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous

def test_dispatch_empty_candidates(setup_mock_dispatcher):
    dispatcher = Dispatcher()
    result = dispatcher.dispatch("hello", [])
    
    assert result.route == "default"
    assert result.confidence == 0.0
    setup_mock_dispatcher.assert_not_called()

def test_dispatch_ranking_order(setup_mock_dispatcher, sample_candidates):
    # Setup mock instance
    mock_instance = MagicMock()
    mock_instance.select_intent.return_value = {"intent": "route_b"}
    setup_mock_dispatcher.return_value = mock_instance
    
    # 0.5 * 0.4 + 0.5 * 0.9 = 0.2 + 0.45 = 0.65
    dispatcher = Dispatcher(semantic_weight=0.5, lexical_weight=0.5)
    
    result = dispatcher.dispatch("test query", sample_candidates)
    
    assert result.route == "route_b"
    assert result.confidence == 0.65
    mock_instance.select_intent.assert_called_once_with("test query", ["route_b"])

def test_dispatch_weight_sensitivity_semantic(setup_mock_dispatcher, sample_candidates):
    mock_instance = MagicMock()
    mock_instance.select_intent.return_value = {"intent": "route_c"}
    setup_mock_dispatcher.return_value = mock_instance
    
    dispatcher = Dispatcher(semantic_weight=1.0, lexical_weight=0.0)
    
    result = dispatcher.dispatch("test query", sample_candidates)
    
    assert result.route == "route_c"
    assert result.confidence == 0.9
    mock_instance.select_intent.assert_called_once_with("test query", ["route_c"])

def test_dispatch_weight_sensitivity_lexical(setup_mock_dispatcher, sample_candidates):
    mock_instance = MagicMock()
    mock_instance.select_intent.return_value = {"intent": "route_b"}
    setup_mock_dispatcher.return_value = mock_instance
    
    dispatcher = Dispatcher(semantic_weight=0.0, lexical_weight=1.0)
    
    result = dispatcher.dispatch("test query", sample_candidates)
    
    assert result.route == "route_b"
    assert result.confidence == 0.9

def test_dispatch_tie_break(setup_mock_dispatcher):
    mock_instance = MagicMock()
    mock_instance.select_intent.return_value = {"intent": "route_1"}
    setup_mock_dispatcher.return_value = mock_instance
    
    candidates = [
        {"id": "route_2", "semantic_score": 0.5, "lexical_score": 0.5},
        {"id": "route_1", "semantic_score": 0.5, "lexical_score": 0.5},
    ]
    
    dispatcher = Dispatcher()
    result = dispatcher.dispatch("test", candidates)
    
    assert result.route == "route_1"
    assert result.confidence == 0.5

def test_select_best_route_public_api(setup_mock_dispatcher, sample_candidates):
    mock_instance = MagicMock()
    mock_instance.select_intent.return_value = {"intent": "route_b"}
    setup_mock_dispatcher.return_value = mock_instance
    
    route = select_best_route("test", sample_candidates)
    assert route == "route_b"

def test_dispatch_missing_scores(setup_mock_dispatcher):
    mock_instance = MagicMock()
    mock_instance.select_intent.return_value = {"intent": "only_route"}
    setup_mock_dispatcher.return_value = mock_instance
    
    candidates = [{"id": "only_route"}]
    
    dispatcher = Dispatcher()
    result = dispatcher.dispatch("test", candidates)
    
    assert result.route == "only_route"
    assert result.confidence == 0.0

def test_dispatch_fallback_when_intent_missing(setup_mock_dispatcher):
    mock_instance = MagicMock()
    mock_instance.select_intent.return_value = {} 
    setup_mock_dispatcher.return_value = mock_instance
    
    candidates = [{"id": "route_a", "semantic_score": 1.0}]
    
    dispatcher = Dispatcher()
    result = dispatcher.dispatch("test", candidates)
    
    assert result.route == "route_a"

def test_dispatch_delegation_called(setup_mock_dispatcher):
    mock_instance = MagicMock()
    mock_instance.select_intent.return_value = {"intent": "expected_intent"}
    setup_mock_dispatcher.return_value = mock_instance
    
    dispatcher = Dispatcher()
    dispatcher.dispatch("some query", [{"id": "cand1", "semantic_score": 1.0}])
    
    setup_mock_dispatcher.assert_called_once()
    mock_instance.select_intent.assert_called_once_with("some query", ["cand1"])

def test_dispatch_metadata_populated(setup_mock_dispatcher):
    mock_instance = MagicMock()
    mock_instance.select_intent.return_value = {"intent": "cand1", "reason": "matches"}
    setup_mock_dispatcher.return_value = mock_instance
    
    cand = {"id": "cand1", "semantic_score": 1.0, "lexical_score": 0.0}
    
    dispatcher = Dispatcher()
    result = dispatcher.dispatch("query", [cand])
    
    assert result.metadata["hybrid_score"] == 0.5
    assert result.metadata["raw_candidate"] == cand
    assert result.metadata["intelligent_dispatcher_result"] == {"intent": "cand1", "reason": "matches"}

def test_invalid_candidate_ids(setup_mock_dispatcher):
    mock_instance = MagicMock()
    mock_instance.select_intent.return_value = {"intent": "valid_route"}
    setup_mock_dispatcher.return_value = mock_instance
    
    candidates = [
        {"id": "", "semantic_score": 1.0}, # empty
        {"id": 123, "semantic_score": 1.0}, # not string
        {"semantic_score": 1.0}, # missing
        {"id": "valid_route", "semantic_score": 1.0}
    ]
    
    dispatcher = Dispatcher()
    result = dispatcher.dispatch("query", candidates)
    
    assert result.route == "valid_route"

def test_route_confidence_swap(setup_mock_dispatcher):
    mock_instance = MagicMock()
    # Mock intelligent dispatcher choosing different intent than the top ranking one
    mock_instance.select_intent.return_value = {"intent": "route_b"} 
    setup_mock_dispatcher.return_value = mock_instance
    
    candidates = [
        {"id": "route_a", "semantic_score": 1.0, "lexical_score": 1.0}, # score 1.0
        {"id": "route_b", "semantic_score": 0.5, "lexical_score": 0.5}, # score 0.5
    ]
    
    dispatcher = Dispatcher(semantic_weight=0.5, lexical_weight=0.5)
    result = dispatcher.dispatch("query", candidates)
    
    # It should correctly assign route_b, and its corresponding confidence of 0.5
    assert result.route == "route_b"
    assert result.confidence == 0.5
    assert result.metadata["raw_candidate"] == candidates[1]
    
