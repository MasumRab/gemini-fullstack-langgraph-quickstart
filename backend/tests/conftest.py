"""Shared test fixtures and utilities for the agent test suite.

This module provides reusable fixtures that can be used across all test files.
Fixtures are designed to be path-insensitive and robust to minor code changes.
"""
import pathlib
import sys
from typing import Any, Dict, List
from types import SimpleNamespace

import pytest
import os

# Set dummy API key before any imports that might use it
os.environ["GEMINI_API_KEY"] = "dummy_key_for_tests"

# Ensure the src directory is on the path
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
# Add PROJECT_ROOT's parent to path to find 'backend' package
if str(PROJECT_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT.parent))
# Add PROJECT_ROOT to path to allow 'from src...' (if needed) or finding modules in backend root
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


# =============================================================================
# State Fixtures
# =============================================================================

@pytest.fixture
def base_state() -> Dict[str, Any]:
    """Minimal valid state for graph node tests."""
    return {
        "messages": [{"content": "User: test research topic"}],
        "search_query": ["test query"],
        "planning_status": None,
        "planning_feedback": [],
        "web_research_result": [],
        "validated_web_research_result": [],
        "validation_notes": [],
        "sources_gathered": [],
        "research_loop_count": 0,
    }


@pytest.fixture
def planning_state(base_state) -> Dict[str, Any]:
    """State configured for planning mode tests."""
    state = base_state.copy()
    state["search_query"] = ["solar energy market", "renewable trends"]
    return state


@pytest.fixture
def reflection_state(base_state) -> Dict[str, Any]:
    """State configured for reflection tests."""
    state = base_state.copy()
    state["is_sufficient"] = False
    state["knowledge_gap"] = "Need more data"
    state["follow_up_queries"] = ["follow up query"]
    state["number_of_ran_queries"] = 1
    return state


# =============================================================================
# Config Fixtures
# =============================================================================

@pytest.fixture
def base_config() -> Dict[str, Any]:
    """Base configuration for tests."""
    return {
        "configurable": {
            "require_planning_confirmation": False,
        }
    }


@pytest.fixture
def confirmation_required_config() -> Dict[str, Any]:
    """Configuration requiring planning confirmation."""
    return {
        "configurable": {
            "require_planning_confirmation": True,
        }
    }


# =============================================================================
# Mock Classes for External Dependencies
# =============================================================================

class MockSegment:
    """Mock for grounding segment metadata."""
    def __init__(self, start_index=None, end_index=None):
        self.start_index = start_index
        self.end_index = end_index


class MockChunk:
    """Mock for grounding chunk with web metadata."""
    def __init__(self, uri: str, title: str):
        self.web = SimpleNamespace(uri=uri, title=title)


class MockSupport:
    """Mock for grounding support metadata."""
    def __init__(self, segment: MockSegment, grounding_chunk_indices: List[int] = None):
        self.segment = segment
        self.grounding_chunk_indices = grounding_chunk_indices or []


class MockCandidate:
    """Mock for API response candidate."""
    def __init__(self, grounding_supports: List[MockSupport], grounding_chunks: List[MockChunk]):
        self.grounding_metadata = SimpleNamespace(
            grounding_supports=grounding_supports,
            grounding_chunks=grounding_chunks,
        )


class MockResponse:
    """Mock for API response with candidates."""
    def __init__(self, candidates: List[MockCandidate]):
        self.candidates = candidates


class MockSite:
    """Mock for URL site data."""
    def __init__(self, uri: str):
        self.web = SimpleNamespace(uri=uri)


# =============================================================================
# Helper Functions
# =============================================================================

def make_message(content: str, role: str = "human"):
    """Create a simple message dict for testing."""
    return {"content": content, "role": role}


def make_human_message(content: str):
    """Create a mock HumanMessage-like object."""
    from langchain_core.messages import HumanMessage
    return HumanMessage(content=content)


def make_ai_message(content: str):
    """Create a mock AIMessage-like object."""
    from langchain_core.messages import AIMessage
    return AIMessage(content=content)
