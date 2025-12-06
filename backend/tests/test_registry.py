import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from agent.registry import GraphRegistry, graph_registry


class TestGraphRegistry:
    def test_registry_singleton_exists(self):
        """Test that the global graph_registry singleton exists."""
        assert graph_registry is not None
        assert isinstance(graph_registry, GraphRegistry)

    def test_describe_decorator_registers_node(self):
        """Test that describe decorator registers node metadata."""
        registry = GraphRegistry()

        @registry.describe(
            "test_node",
            summary="Test node summary",
            tags=["test", "example"],
            outputs=["result"],
        )
        def test_function():
            return {"result": "success"}

        assert "test_node" in registry.node_docs
        assert registry.node_docs["test_node"]["handler"] == "test_function"
        assert registry.node_docs["test_node"]["summary"] == "Test node summary"
        assert registry.node_docs["test_node"]["tags"] == ["test", "example"]
        assert registry.node_docs["test_node"]["outputs"] == ["result"]

    def test_describe_decorator_preserves_function(self):
        """Test that describe decorator doesn't alter function behavior."""
        registry = GraphRegistry()

        @registry.describe("node", summary="Summary")
        def add_numbers(a, b):
            return a + b

        result = add_numbers(2, 3)
        assert result == 5

    def test_document_edge_records_edge(self):
        """Test that document_edge records edge information."""
        registry = GraphRegistry()

        registry.document_edge(
            "node1", "node2", description="Edge from node1 to node2"
        )

        assert len(registry.edge_docs) == 1
        assert registry.edge_docs[0]["source"] == "node1"
        assert registry.edge_docs[0]["target"] == "node2"
        assert registry.edge_docs[0]["description"] == "Edge from node1 to node2"

    def test_document_edge_without_description(self):
        """Test document_edge with empty description."""
        registry = GraphRegistry()

        registry.document_edge("start", "end")

        assert len(registry.edge_docs) == 1
        assert registry.edge_docs[0]["description"] == ""

    def test_add_note_appends_notes(self):
        """Test that add_note appends notes to the registry."""
        registry = GraphRegistry()

        registry.add_note("First note")
        registry.add_note("Second note")

        assert len(registry.notes) == 2
        assert "First note" in registry.notes
        assert "Second note" in registry.notes

    def test_render_overview_includes_nodes(self):
        """Test that render_overview includes registered nodes."""
        registry = GraphRegistry()

        @registry.describe("test_node", summary="Test summary", tags=["tag1"])
        def test_func():
            pass

        overview = registry.render_overview()

        assert "Registered Nodes:" in overview
        assert "test_node" in overview
        assert "Test summary" in overview
        assert "tags: tag1" in overview

    def test_render_overview_includes_edges(self):
        """Test that render_overview includes documented edges."""
        registry = GraphRegistry()

        registry.document_edge("source", "target", description="Test edge")

        overview = registry.render_overview()

        assert "Documented Edges:" in overview
        assert "source -> target" in overview
        assert "Test edge" in overview

    def test_render_overview_includes_notes(self):
        """Test that render_overview includes notes."""
        registry = GraphRegistry()

        registry.add_note("Important note about the graph")

        overview = registry.render_overview()

        assert "Notes:" in overview
        assert "Important note about the graph" in overview

    def test_render_overview_handles_empty_registry(self):
        """Test render_overview with empty registry."""
        registry = GraphRegistry()

        overview = registry.render_overview()

        assert "Registered Nodes:" in overview
        # Should not crash, just show headers

    def test_describe_with_no_tags_or_outputs(self):
        """Test describe decorator with minimal parameters."""
        registry = GraphRegistry()

        @registry.describe("minimal_node", summary="Minimal summary")
        def minimal_func():
            pass

        assert registry.node_docs["minimal_node"]["tags"] == []
        assert registry.node_docs["minimal_node"]["outputs"] == []

    def test_multiple_nodes_registration(self):
        """Test registering multiple nodes."""
        registry = GraphRegistry()

        @registry.describe("node1", summary="First node")
        def func1():
            pass

        @registry.describe("node2", summary="Second node")
        def func2():
            pass

        assert len(registry.node_docs) == 2
        assert "node1" in registry.node_docs
        assert "node2" in registry.node_docs

    def test_registry_independence(self):
        """Test that separate registry instances are independent."""
        registry1 = GraphRegistry()
        registry2 = GraphRegistry()

        registry1.add_note("Note in registry1")
        registry2.add_note("Note in registry2")

        assert len(registry1.notes) == 1
        assert len(registry2.notes) == 1
        assert registry1.notes[0] != registry2.notes[0]