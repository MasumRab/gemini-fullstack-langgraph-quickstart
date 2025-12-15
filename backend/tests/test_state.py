"""
Comprehensive unit tests for backend/src/agent/state.py

Tests cover:
- create_rag_resources function behavior
- OverallState TypedDict structure
- ReflectionState TypedDict structure
- State validation and edge cases
"""

import pytest
from typing import List, Dict, Any

from agent.state import (
    create_rag_resources,
    OverallState,
    ReflectionState,
    Query,
    QueryGenerationState,
    WebSearchState,
    SearchStateOutput,
)


# =============================================================================
# Tests for create_rag_resources Function
# =============================================================================

class TestCreateRagResources:
    """Test suite for create_rag_resources function."""

    def test_create_rag_resources_raises_not_implemented_error(self):
        """Test that create_rag_resources raises NotImplementedError."""
        # Setup
        resource_uris = ["uri1", "uri2", "uri3"]

        # Execute & Assert
        with pytest.raises(NotImplementedError) as exc_info:
            create_rag_resources(resource_uris)

        # Verify error message content
        assert "create_rag_resources is not implemented" in str(exc_info.value)
        assert "Provide agent.state.create_rag_resources" in str(exc_info.value)
        assert "Resource objects" in str(exc_info.value)

    def test_create_rag_resources_with_empty_list(self):
        """Test create_rag_resources with empty URI list."""
        # Setup
        resource_uris = []

        # Execute & Assert
        with pytest.raises(NotImplementedError):
            create_rag_resources(resource_uris)

    def test_create_rag_resources_with_single_uri(self):
        """Test create_rag_resources with single URI."""
        # Setup
        resource_uris = ["s3://bucket/document.pdf"]

        # Execute & Assert
        with pytest.raises(NotImplementedError):
            create_rag_resources(resource_uris)

    def test_create_rag_resources_with_multiple_uris(self):
        """Test create_rag_resources with multiple URIs."""
        # Setup
        resource_uris = [
            "s3://bucket/doc1.pdf",
            "https://example.com/doc2.html",
            "file:///local/doc3.txt",
        ]

        # Execute & Assert
        with pytest.raises(NotImplementedError):
            create_rag_resources(resource_uris)

    def test_create_rag_resources_docstring_completeness(self):
        """Test that create_rag_resources has comprehensive docstring."""
        # Get function docstring
        docstring = create_rag_resources.__doc__

        # Assert docstring exists and is detailed
        assert docstring is not None
        assert len(docstring) > 50  # Should be substantial
        
        # Check for key documentation elements
        assert "extension point" in docstring.lower()
        assert "example" in docstring.lower()
        assert "raises" in docstring.lower()
        assert "NotImplementedError" in docstring

    def test_create_rag_resources_function_signature(self):
        """Test that create_rag_resources has correct function signature."""
        import inspect
        
        # Get function signature
        sig = inspect.signature(create_rag_resources)
        params = list(sig.parameters.keys())
        
        # Assert signature is as expected
        assert len(params) == 1
        assert params[0] == "resource_uris"
        
        # Check parameter annotation
        param = sig.parameters["resource_uris"]
        # Handle stringified annotations due to from __future__ import annotations
        annotation = param.annotation
        assert annotation == list[str] or annotation == 'list[str]'


# =============================================================================
# Tests for State TypedDict Structures
# =============================================================================

class TestOverallState:
    """Test suite for OverallState TypedDict."""

    def test_overall_state_has_required_fields(self):
        """Test that OverallState defines all required fields."""
        # Get annotations
        annotations = OverallState.__annotations__
        
        # Check for essential fields
        essential_fields = [
            "messages",
            "search_query",
            "web_research_result",
            "validated_web_research_result",
            "validation_notes",
            "sources_gathered",
            "scoping_status",
            "planning_status",
            "research_loop_count",
        ]
        
        for field in essential_fields:
            assert field in annotations, f"Field {field} missing from OverallState"


class TestReflectionState:
    """Test suite for ReflectionState TypedDict."""

    def test_reflection_state_has_required_fields(self):
        """Test that ReflectionState defines all required fields."""
        annotations = ReflectionState.__annotations__
        
        required_fields = [
            "is_sufficient",
            "knowledge_gap",
            "follow_up_queries",
            "research_loop_count",
            "number_of_ran_queries",
        ]
        
        for field in required_fields:
            assert field in annotations, f"Field {field} missing from ReflectionState"

    def test_reflection_state_is_sufficient_is_bool(self):
        """Test that is_sufficient field is boolean."""
        import typing
        # Resolve forward references
        annotations = typing.get_type_hints(ReflectionState)
        assert annotations["is_sufficient"] == bool


class TestSearchStateOutput:
    """Test suite for SearchStateOutput dataclass."""

    def test_search_state_output_has_running_summary(self):
        """Test SearchStateOutput dataclass has running_summary field."""
        # Create instance
        output = SearchStateOutput()
        
        # Check field exists and defaults to None
        assert hasattr(output, "running_summary")
        assert output.running_summary is None

    def test_search_state_output_can_set_running_summary(self):
        """Test that running_summary can be set."""
        # Create instance with summary
        output = SearchStateOutput(running_summary="Test summary")
        
        # Assert value is set
        assert output.running_summary == "Test summary"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])