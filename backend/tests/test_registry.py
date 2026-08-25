"""
Unit tests for backend/src/agent/registry.py

Tests cover:
- GraphRegistry initialization
- Node documentation with describe decorator
- Edge documentation
- Notes functionality
- Overview rendering
"""

import pytest

from agent.registry import GraphRegistry, graph_registry


class TestGraphRegistryInitialization:
    """Test suite for GraphRegistry initialization"""

    def test_registry_initializes_empty(self):
        """Test that registry starts empty"""
        registry = GraphRegistry()
        assert len(registry.node_docs) == 0
        assert len(registry.edge_docs) == 0
        assert len(registry.notes) == 0

    def test_registry_has_required_attributes(self):
        """Test that registry has required data structures"""
        registry = GraphRegistry()
        assert hasattr(registry, 'node_docs')
        assert hasattr(registry, 'edge_docs')
        assert hasattr(registry, 'notes')
        assert isinstance(registry.node_docs, dict)
        assert isinstance(registry.edge_docs, list)
        assert isinstance(registry.notes, list)


class TestDescribeDecorator:
    """Test suite for the describe decorator"""

    def test_describe_registers_node_metadata(self):
        """Test that describe decorator registers node metadata"""
        registry = GraphRegistry()

        @registry.describe(
            "test_node",
            summary="A test node",
            tags=["test", "example"],
            outputs=["result"],
        )
        def test_func(state, config):
            return {"result": "success"}

        assert "test_node" in registry.node_docs
        assert registry.node_docs["test_node"]["summary"] == "A test node"
        assert registry.node_docs["test_node"]["tags"] == ["test", "example"]
        assert registry.node_docs["test_node"]["outputs"] == ["result"]

    def test_describe_preserves_function(self):
        """Test that describe decorator returns the original function"""
        registry = GraphRegistry()

        @registry.describe("test_node", summary="Test")
        def original_func(state, config):
            return {"value": 42}

        # Function should still work
        result = original_func({}, {})
        assert result["value"] == 42

    def test_describe_records_handler_name(self):
        """Test that describe records the function name"""
        registry = GraphRegistry()

        @registry.describe("my_node", summary="My node")
        def my_handler_function(state, config):
            return {}

        assert registry.node_docs["my_node"]["handler"] == "my_handler_function"

    def test_describe_with_no_optional_params(self):
        """Test describe with only required parameters"""
        registry = GraphRegistry()

        @registry.describe("minimal_node", summary="Minimal")
        def minimal(state, config):
            return {}

        assert registry.node_docs["minimal_node"]["tags"] == []
        assert registry.node_docs["minimal_node"]["outputs"] == []


class TestEdgeDocumentation:
    """Test suite for edge documentation"""

    def test_document_edge_basic(self):
        """Test basic edge documentation"""
        registry = GraphRegistry()
        registry.document_edge("node_a", "node_b", description="Transition from A to B")

        assert len(registry.edge_docs) == 1
        assert registry.edge_docs[0]["source"] == "node_a"
        assert registry.edge_docs[0]["target"] == "node_b"
        assert registry.edge_docs[0]["description"] == "Transition from A to B"

    def test_document_edge_without_description(self):
        """Test edge documentation without description"""
        registry = GraphRegistry()
        registry.document_edge("start", "end")

        assert len(registry.edge_docs) == 1
        assert registry.edge_docs[0]["description"] == ""

    def test_document_multiple_edges(self):
        """Test documenting multiple edges"""
        registry = GraphRegistry()
        registry.document_edge("a", "b")
        registry.document_edge("b", "c")
        registry.document_edge("c", "d")

        assert len(registry.edge_docs) == 3


class TestNotes:
    """Test suite for notes functionality"""

    def test_add_note(self):
        """Test adding a note"""
        registry = GraphRegistry()
        registry.add_note("This is an important note")

        assert len(registry.notes) == 1
        assert registry.notes[0] == "This is an important note"

    def test_add_multiple_notes(self):
        """Test adding multiple notes"""
        registry = GraphRegistry()
        registry.add_note("Note 1")
        registry.add_note("Note 2")
        registry.add_note("Note 3")

        assert len(registry.notes) == 3


class TestRenderOverview:
    """Test suite for render_overview method"""

    def test_render_overview_empty_registry(self):
        """Test rendering overview of empty registry"""
        registry = GraphRegistry()
        overview = registry.render_overview()

        assert "Registered Nodes:" in overview

    def test_render_overview_with_nodes(self):
        """Test rendering overview with registered nodes"""
        registry = GraphRegistry()

        @registry.describe("test_node", summary="A test node", tags=["test"])
        def test_func(state, config):
            return {}

        overview = registry.render_overview()

        assert "test_node" in overview
        assert "A test node" in overview
        assert "test" in overview

    def test_render_overview_with_edges(self):
        """Test rendering overview with documented edges"""
        registry = GraphRegistry()
        registry.document_edge("start", "process", description="Begin processing")

        overview = registry.render_overview()

        assert "Documented Edges:" in overview
        assert "start -> process" in overview
        assert "Begin processing" in overview

    def test_render_overview_with_notes(self):
        """Test rendering overview with notes"""
        registry = GraphRegistry()
        registry.add_note("Important implementation detail")

        overview = registry.render_overview()

        assert "Notes:" in overview
        assert "Important implementation detail" in overview


class TestSingletonInstance:
    """Test the singleton graph_registry instance"""

    def test_singleton_exists(self):
        """Test that singleton instance exists"""
        assert graph_registry is not None
        assert isinstance(graph_registry, GraphRegistry)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])