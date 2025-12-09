import unittest
from agent.registry import GraphRegistry, graph_registry


class TestGraphRegistry(unittest.TestCase):
    """Comprehensive tests for GraphRegistry class."""

    def setUp(self):
        """Create a fresh registry for each test."""
        self.registry = GraphRegistry()

    def test_initialization(self):
        """Test that registry initializes with empty structures."""
        self.assertEqual(self.registry.node_docs, {})
        self.assertEqual(self.registry.edge_docs, [])
        self.assertEqual(self.registry.notes, [])

    def test_describe_decorator_basic(self):
        """Test that describe decorator records metadata."""
        @self.registry.describe(
            "test_node",
            summary="Test summary",
            tags=["test"],
            outputs=["result"]
        )
        def test_function():
            return "test"

        self.assertIn("test_node", self.registry.node_docs)
        docs = self.registry.node_docs["test_node"]
        self.assertEqual(docs["handler"], "test_function")
        self.assertEqual(docs["summary"], "Test summary")
        self.assertEqual(docs["tags"], ["test"])
        self.assertEqual(docs["outputs"], ["result"])

    def test_describe_decorator_minimal(self):
        """Test describe decorator with minimal arguments."""
        @self.registry.describe("minimal_node", summary="Minimal")
        def minimal_func():
            pass

        docs = self.registry.node_docs["minimal_node"]
        self.assertEqual(docs["tags"], [])
        self.assertEqual(docs["outputs"], [])

    def test_describe_decorator_preserves_function(self):
        """Test that decorator doesn't change function behavior."""
        @self.registry.describe("func_node", summary="Test")
        def add_numbers(a, b):
            return a + b

        result = add_numbers(2, 3)
        self.assertEqual(result, 5)

    def test_document_edge_basic(self):
        """Test documenting edges between nodes."""
        self.registry.document_edge(
            "node_a",
            "node_b",
            description="Connects A to B"
        )
        self.assertEqual(len(self.registry.edge_docs), 1)
        edge = self.registry.edge_docs[0]
        self.assertEqual(edge["source"], "node_a")
        self.assertEqual(edge["target"], "node_b")
        self.assertEqual(edge["description"], "Connects A to B")

    def test_document_edge_without_description(self):
        """Test documenting edge without description."""
        self.registry.document_edge("node_x", "node_y")
        edge = self.registry.edge_docs[0]
        self.assertEqual(edge["description"], "")

    def test_document_multiple_edges(self):
        """Test documenting multiple edges."""
        self.registry.document_edge("a", "b", description="First")
        self.registry.document_edge("b", "c", description="Second")
        self.registry.document_edge("c", "d", description="Third")
        
        self.assertEqual(len(self.registry.edge_docs), 3)
        self.assertEqual(self.registry.edge_docs[0]["source"], "a")
        self.assertEqual(self.registry.edge_docs[1]["source"], "b")
        self.assertEqual(self.registry.edge_docs[2]["source"], "c")

    def test_add_note(self):
        """Test adding notes to registry."""
        self.registry.add_note("This is a note")
        self.assertEqual(len(self.registry.notes), 1)
        self.assertEqual(self.registry.notes[0], "This is a note")

    def test_add_multiple_notes(self):
        """Test adding multiple notes."""
        self.registry.add_note("First note")
        self.registry.add_note("Second note")
        self.registry.add_note("Third note")
        
        self.assertEqual(len(self.registry.notes), 3)
        self.assertEqual(self.registry.notes[1], "Second note")

    def test_render_overview_empty(self):
        """Test rendering overview with empty registry."""
        overview = self.registry.render_overview()
        self.assertIn("Registered Nodes:", overview)
        self.assertNotIn("Documented Edges:", overview)
        self.assertNotIn("Notes:", overview)

    def test_render_overview_with_nodes(self):
        """Test rendering overview with registered nodes."""
        @self.registry.describe(
            "node1",
            summary="First node",
            tags=["tag1", "tag2"],
            outputs=["out1"]
        )
        def func1():
            pass

        @self.registry.describe(
            "node2",
            summary="Second node"
        )
        def func2():
            pass

        overview = self.registry.render_overview()
        self.assertIn("node1 (func1): First node", overview)
        self.assertIn("tags: tag1, tag2", overview)
        self.assertIn("outputs: out1", overview)
        self.assertIn("node2 (func2): Second node", overview)

    def test_render_overview_with_edges(self):
        """Test rendering overview with documented edges."""
        self.registry.document_edge("start", "middle", description="First hop")
        self.registry.document_edge("middle", "end", description="Second hop")

        overview = self.registry.render_overview()
        self.assertIn("Documented Edges:", overview)
        self.assertIn("start -> middle - First hop", overview)
        self.assertIn("middle -> end - Second hop", overview)

    def test_render_overview_with_notes(self):
        """Test rendering overview with notes."""
        self.registry.add_note("Important: Check configuration")
        self.registry.add_note("TODO: Optimize performance")

        overview = self.registry.render_overview()
        self.assertIn("Notes:", overview)
        self.assertIn("Important: Check configuration", overview)
        self.assertIn("TODO: Optimize performance", overview)

    def test_render_overview_complete(self):
        """Test rendering complete overview with all elements."""
        @self.registry.describe("process", summary="Process data", tags=["core"])
        def process_data():
            pass

        self.registry.document_edge("start", "process", description="Begin processing")
        self.registry.add_note("System initialized")

        overview = self.registry.render_overview()
        self.assertIn("Registered Nodes:", overview)
        self.assertIn("process (process_data): Process data", overview)
        self.assertIn("Documented Edges:", overview)
        self.assertIn("start -> process - Begin processing", overview)
        self.assertIn("Notes:", overview)
        self.assertIn("System initialized", overview)

    def test_multiple_tags(self):
        """Test node with multiple tags."""
        @self.registry.describe(
            "multi_tag_node",
            summary="Node with many tags",
            tags=["tag1", "tag2", "tag3", "tag4"]
        )
        def multi_func():
            pass

        docs = self.registry.node_docs["multi_tag_node"]
        self.assertEqual(len(docs["tags"]), 4)

    def test_multiple_outputs(self):
        """Test node with multiple outputs."""
        @self.registry.describe(
            "multi_output_node",
            summary="Node with many outputs",
            outputs=["output1", "output2", "output3"]
        )
        def multi_output():
            pass

        docs = self.registry.node_docs["multi_output_node"]
        self.assertEqual(len(docs["outputs"]), 3)

    def test_global_registry_exists(self):
        """Test that global graph_registry instance exists."""
        self.assertIsInstance(graph_registry, GraphRegistry)

    def test_node_docs_immutability(self):
        """Test that we can safely modify node_docs entries."""
        @self.registry.describe("test", summary="Test")
        def test_func():
            pass

        # Should be able to read docs
        docs = self.registry.node_docs["test"]
        self.assertEqual(docs["summary"], "Test")

    def test_edge_with_same_source_different_targets(self):
        """Test documenting multiple edges from same source."""
        self.registry.document_edge("hub", "node1", description="First")
        self.registry.document_edge("hub", "node2", description="Second")
        self.registry.document_edge("hub", "node3", description="Third")

        hub_edges = [e for e in self.registry.edge_docs if e["source"] == "hub"]
        self.assertEqual(len(hub_edges), 3)

    def test_special_characters_in_names(self):
        """Test that special characters in names are handled."""
        @self.registry.describe(
            "node_with-special.chars",
            summary="Special node"
        )
        def special_func():
            pass

        self.assertIn("node_with-special.chars", self.registry.node_docs)

    def test_unicode_in_descriptions(self):
        """Test that unicode characters are handled in descriptions."""
        self.registry.document_edge(
            "start",
            "end",
            description="Unicode test: émojis 🚀 and symbols ±∞"
        )
        edge = self.registry.edge_docs[0]
        self.assertIn("🚀", edge["description"])

    def test_empty_tags_list(self):
        """Test that empty tags list is handled correctly."""
        @self.registry.describe("node", summary="Test", tags=[])
        def func():
            pass

        docs = self.registry.node_docs["node"]
        self.assertEqual(docs["tags"], [])

    def test_empty_outputs_list(self):
        """Test that empty outputs list is handled correctly."""
        @self.registry.describe("node", summary="Test", outputs=[])
        def func():
            pass

        docs = self.registry.node_docs["node"]
        self.assertEqual(docs["outputs"], [])


if __name__ == "__main__":
    unittest.main()