import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from agent.registry import GraphRegistry, graph_registry  # noqa: E402


class TestGraphRegistry:
    """Test suite for GraphRegistry class."""

    def test_initialization(self):
        """Test GraphRegistry initializes with empty collections."""
        registry = GraphRegistry()
        assert registry.node_docs == {}
        assert registry.edge_docs == []
        assert registry.notes == []

    def test_describe_decorator_registers_node(self):
        """Test that describe decorator registers node metadata."""
        registry = GraphRegistry()
        
        @registry.describe(
            "test_node",
            summary="Test node summary",
            tags=["test", "example"],
            outputs=["output1", "output2"],
        )
        def test_function():
            return "test"
        
        assert "test_node" in registry.node_docs
        node_meta = registry.node_docs["test_node"]
        assert node_meta["handler"] == "test_function"
        assert node_meta["summary"] == "Test node summary"
        assert node_meta["tags"] == ["test", "example"]
        assert node_meta["outputs"] == ["output1", "output2"]

    def test_describe_decorator_preserves_function(self):
        """Test that describe decorator doesn't modify the function."""
        registry = GraphRegistry()
        
        @registry.describe("node", summary="Summary")
        def original_func(x):
            return x * 2
        
        # Function should still work normally
        assert original_func(5) == 10
        assert original_func.__name__ == "original_func"

    def test_describe_with_minimal_args(self):
        """Test describe with only required arguments."""
        registry = GraphRegistry()
        
        @registry.describe("minimal_node", summary="Minimal summary")
        def minimal_func():
            pass
        
        node_meta = registry.node_docs["minimal_node"]
        assert node_meta["tags"] == []
        assert node_meta["outputs"] == []

    def test_describe_multiple_nodes(self):
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

    def test_document_edge(self):
        """Test documenting edges between nodes."""
        registry = GraphRegistry()
        
        registry.document_edge("node1", "node2", description="Flows to node2")
        
        assert len(registry.edge_docs) == 1
        edge = registry.edge_docs[0]
        assert edge["source"] == "node1"
        assert edge["target"] == "node2"
        assert edge["description"] == "Flows to node2"

    def test_document_edge_without_description(self):
        """Test documenting edge without description."""
        registry = GraphRegistry()
        
        registry.document_edge("nodeA", "nodeB")
        
        assert len(registry.edge_docs) == 1
        edge = registry.edge_docs[0]
        assert edge["source"] == "nodeA"
        assert edge["target"] == "nodeB"
        assert edge["description"] == ""

    def test_document_multiple_edges(self):
        """Test documenting multiple edges."""
        registry = GraphRegistry()
        
        registry.document_edge("A", "B", description="A to B")
        registry.document_edge("B", "C", description="B to C")
        registry.document_edge("A", "C", description="A to C shortcut")
        
        assert len(registry.edge_docs) == 3

    def test_add_note(self):
        """Test adding notes to registry."""
        registry = GraphRegistry()
        
        registry.add_note("Important implementation detail")
        registry.add_note("Another note")
        
        assert len(registry.notes) == 2
        assert "Important implementation detail" in registry.notes
        assert "Another note" in registry.notes

    def test_render_overview_with_nodes(self):
        """Test rendering overview with node documentation."""
        registry = GraphRegistry()
        
        @registry.describe(
            "test_node",
            summary="Processes data",
            tags=["processing", "core"],
            outputs=["result", "metadata"],
        )
        def process_data():
            pass
        
        overview = registry.render_overview()
        
        assert "Registered Nodes:" in overview
        assert "test_node" in overview
        assert "process_data" in overview
        assert "Processes data" in overview
        assert "processing, core" in overview
        assert "result, metadata" in overview

    def test_render_overview_with_edges(self):
        """Test rendering overview with edge documentation."""
        registry = GraphRegistry()
        
        registry.document_edge("input", "process", description="Initial processing")
        registry.document_edge("process", "output", description="Final output")
        
        overview = registry.render_overview()
        
        assert "Documented Edges:" in overview
        assert "input -> process" in overview
        assert "Initial processing" in overview
        assert "process -> output" in overview
        assert "Final output" in overview

    def test_render_overview_with_notes(self):
        """Test rendering overview with notes."""
        registry = GraphRegistry()
        
        registry.add_note("Experimental feature")
        registry.add_note("Requires API key")
        
        overview = registry.render_overview()
        
        assert "Notes:" in overview
        assert "Experimental feature" in overview
        assert "Requires API key" in overview

    def test_render_overview_comprehensive(self):
        """Test rendering complete overview with all elements."""
        registry = GraphRegistry()
        
        @registry.describe("node1", summary="First node", tags=["input"])
        def node1():
            pass
        
        @registry.describe("node2", summary="Second node", outputs=["data"])
        def node2():
            pass
        
        registry.document_edge("node1", "node2", description="Data flow")
        registry.add_note("System is experimental")
        
        overview = registry.render_overview()
        
        # Check all sections are present
        assert "Registered Nodes:" in overview
        assert "node1" in overview
        assert "node2" in overview
        assert "Documented Edges:" in overview
        assert "node1 -> node2" in overview
        assert "Notes:" in overview
        assert "System is experimental" in overview

    def test_render_overview_empty_registry(self):
        """Test rendering overview when registry is empty."""
        registry = GraphRegistry()
        overview = registry.render_overview()
        
        assert "Registered Nodes:" in overview
        # Should not have edges or notes sections if empty
        assert "Documented Edges:" not in overview
        assert "Notes:" not in overview

    def test_singleton_instance_exists(self):
        """Test that graph_registry singleton exists and is usable."""
        # The module exports a singleton instance
        assert graph_registry is not None
        assert isinstance(graph_registry, GraphRegistry)
        
        # Should be able to use it
        initial_count = len(graph_registry.node_docs)
        
        @graph_registry.describe("singleton_test", summary="Testing singleton")
        def test_func():
            pass
        
        # Should have registered the node
        assert len(graph_registry.node_docs) >= initial_count

    def test_multiple_tags(self):
        """Test node with multiple tags."""
        registry = GraphRegistry()
        
        @registry.describe(
            "multi_tag_node",
            summary="Node with many tags",
            tags=["tag1", "tag2", "tag3", "tag4"],
        )
        def func():
            pass
        
        node_meta = registry.node_docs["multi_tag_node"]
        assert len(node_meta["tags"]) == 4
        assert "tag1" in node_meta["tags"]

    def test_multiple_outputs(self):
        """Test node with multiple outputs."""
        registry = GraphRegistry()
        
        @registry.describe(
            "multi_output_node",
            summary="Node with many outputs",
            outputs=["out1", "out2", "out3"],
        )
        def func():
            pass
        
        node_meta = registry.node_docs["multi_output_node"]
        assert len(node_meta["outputs"]) == 3

    def test_edge_between_same_node(self):
        """Test documenting self-referential edge."""
        registry = GraphRegistry()
        
        registry.document_edge("recursive", "recursive", description="Self loop")
        
        edge = registry.edge_docs[0]
        assert edge["source"] == "recursive"
        assert edge["target"] == "recursive"

    def test_describe_overwrites_existing(self):
        """Test that describing same node name overwrites."""
        registry = GraphRegistry()
        
        @registry.describe("node", summary="First summary")
        def func1():
            pass
        
        @registry.describe("node", summary="Second summary")
        def func2():
            pass
        
        # Should have overwritten
        assert len(registry.node_docs) == 1
        assert registry.node_docs["node"]["summary"] == "Second summary"
        assert registry.node_docs["node"]["handler"] == "func2"

    def test_empty_tags_and_outputs(self):
        """Test explicitly passing empty lists for tags and outputs."""
        registry = GraphRegistry()
        
        @registry.describe("node", summary="Summary", tags=[], outputs=[])
        def func():
            pass
        
        node_meta = registry.node_docs["node"]
        assert node_meta["tags"] == []
        assert node_meta["outputs"] == []

    def test_render_overview_formatting(self):
        """Test that render_overview uses proper formatting."""
        registry = GraphRegistry()
        
        @registry.describe("format_test", summary="Test formatting")
        def func():
            pass
        
        overview = registry.render_overview()
        lines = overview.split("\n")
        
        # Should have proper structure
        assert any(line.startswith("Registered Nodes:") for line in lines)
        assert any(line.startswith("- format_test") for line in lines)