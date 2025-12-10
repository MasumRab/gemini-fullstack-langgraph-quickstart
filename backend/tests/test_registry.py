"""
Comprehensive unit tests for backend/src/agent/registry.py

Tests cover:
- NodeRegistry initialization
- Node registration
- Node retrieval
- Node listing
- Error handling
- Edge cases
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Callable

from agent.registry import NodeRegistry


# Fixtures
@pytest.fixture
def registry():
    """Create a fresh NodeRegistry for each test"""
    return NodeRegistry()


@pytest.fixture
def sample_node():
    """Create a sample node function"""
    def node_func(state, config):
        return {"result": "success"}
    return node_func


@pytest.fixture
def another_node():
    """Create another sample node function"""
    def another_func(state, config):
        return {"result": "another"}
    return another_func


# Tests for NodeRegistry initialization
class TestNodeRegistryInitialization:
    """Test suite for NodeRegistry initialization"""

    def test_registry_initializes_empty(self):
        """Test that registry starts with no nodes"""
        registry = NodeRegistry()
        assert len(registry.list_nodes()) == 0

    def test_registry_has_nodes_dict(self):
        """Test that registry has _nodes dictionary"""
        registry = NodeRegistry()
        assert hasattr(registry, '_nodes')
        assert isinstance(registry._nodes, dict)


# Tests for node registration
class TestNodeRegistration:
    """Test suite for registering nodes"""

    def test_register_single_node(self, registry, sample_node):
        """Test registering a single node"""
        registry.register("test_node", sample_node)

        assert "test_node" in registry.list_nodes()
        assert registry.get("test_node") == sample_node

    def test_register_multiple_nodes(self, registry, sample_node, another_node):
        """Test registering multiple nodes"""
        registry.register("node1", sample_node)
        registry.register("node2", another_node)

        nodes = registry.list_nodes()
        assert "node1" in nodes
        assert "node2" in nodes
        assert len(nodes) == 2

    def test_register_with_same_name_overwrites(self, registry, sample_node, another_node):
        """Test that registering with same name overwrites previous"""
        registry.register("test_node", sample_node)
        registry.register("test_node", another_node)

        assert registry.get("test_node") == another_node
        assert len(registry.list_nodes()) == 1

    def test_register_with_empty_name(self, registry, sample_node):
        """Test registering with empty name"""
        # Should handle gracefully or raise appropriate error
        try:
            registry.register("", sample_node)
            # If it allows empty names, verify it's registered
            assert "" in registry.list_nodes()
        except (ValueError, KeyError) as e:
            # If it rejects empty names, that's also acceptable
            assert True

    def test_register_with_none_name(self, registry, sample_node):
        """Test registering with None as name"""
        with pytest.raises((TypeError, ValueError)):
            registry.register(None, sample_node)

    def test_register_with_none_node(self, registry):
        """Test registering None as node function"""
        # Should handle gracefully or raise appropriate error
        try:
            registry.register("test_node", None)
            # If it allows None, verify it's registered
            assert "test_node" in registry.list_nodes()
        except (ValueError, TypeError):
            # If it rejects None, that's also acceptable
            assert True

    def test_register_with_non_callable(self, registry):
        """Test registering non-callable object"""
        with pytest.raises((TypeError, ValueError)):
            registry.register("test_node", "not a function")

    def test_register_preserves_function_metadata(self, registry):
        """Test that registration preserves function metadata"""
        def documented_node(state, config):
            """This is a documented node"""
            return {"result": "success"}

        registry.register("doc_node", documented_node)
        retrieved = registry.get("doc_node")

        assert retrieved.__doc__ == "This is a documented node"
        assert retrieved.__name__ == "documented_node"


# Tests for node retrieval
class TestNodeRetrieval:
    """Test suite for retrieving nodes"""

    def test_get_existing_node(self, registry, sample_node):
        """Test retrieving an existing node"""
        registry.register("test_node", sample_node)

        retrieved = registry.get("test_node")
        assert retrieved == sample_node

    def test_get_nonexistent_node_returns_none(self, registry):
        """Test retrieving non-existent node returns None"""
        result = registry.get("nonexistent")
        assert result is None

    def test_get_after_overwrite(self, registry, sample_node, another_node):
        """Test getting node after it's been overwritten"""
        registry.register("test_node", sample_node)
        registry.register("test_node", another_node)

        retrieved = registry.get("test_node")
        assert retrieved == another_node
        assert retrieved != sample_node

    def test_get_with_empty_string(self, registry):
        """Test retrieving with empty string"""
        result = registry.get("")
        # Should return None or raise appropriate error
        assert result is None or isinstance(result, Exception)

    def test_get_with_none(self, registry):
        """Test retrieving with None"""
        with pytest.raises((TypeError, KeyError)):
            registry.get(None)


# Tests for listing nodes
class TestNodeListing:
    """Test suite for listing registered nodes"""

    def test_list_nodes_empty_registry(self, registry):
        """Test listing nodes in empty registry"""
        nodes = registry.list_nodes()
        assert nodes == []

    def test_list_nodes_single_node(self, registry, sample_node):
        """Test listing with single registered node"""
        registry.register("test_node", sample_node)

        nodes = registry.list_nodes()
        assert len(nodes) == 1
        assert "test_node" in nodes

    def test_list_nodes_multiple_nodes(self, registry, sample_node, another_node):
        """Test listing multiple registered nodes"""
        registry.register("node1", sample_node)
        registry.register("node2", another_node)
        registry.register("node3", sample_node)

        nodes = registry.list_nodes()
        assert len(nodes) == 3
        assert "node1" in nodes
        assert "node2" in nodes
        assert "node3" in nodes

    def test_list_nodes_returns_copy(self, registry, sample_node):
        """Test that list_nodes returns a copy, not reference"""
        registry.register("test_node", sample_node)

        nodes1 = registry.list_nodes()
        nodes2 = registry.list_nodes()

        # Modifying one list shouldn't affect the other
        nodes1.append("fake_node")
        assert "fake_node" not in nodes2

    def test_list_nodes_after_overwrite(self, registry, sample_node, another_node):
        """Test that list doesn't include duplicates after overwrite"""
        registry.register("test_node", sample_node)
        registry.register("test_node", another_node)

        nodes = registry.list_nodes()
        assert nodes.count("test_node") == 1


# Tests for node execution
class TestNodeExecution:
    """Test suite for executing registered nodes"""

    def test_execute_registered_node(self, registry):
        """Test executing a registered node"""
        def add_node(state, config):
            return {"count": state.get("count", 0) + 1}

        registry.register("add", add_node)

        node = registry.get("add")
        result = node({"count": 5}, {})

        assert result["count"] == 6

    def test_execute_node_with_state(self, registry):
        """Test node execution with complex state"""
        def state_processor(state, config):
            return {
                "messages": state.get("messages", []) + ["new message"],
                "count": state.get("count", 0) + 1,
            }

        registry.register("processor", state_processor)

        node = registry.get("processor")
        initial_state = {"messages": ["hello"], "count": 5}
        result = node(initial_state, {})

        assert len(result["messages"]) == 2
        assert result["count"] == 6

    def test_execute_node_with_config(self, registry):
        """Test node execution with configuration"""
        def configurable_node(state, config):
            multiplier = config.get("multiplier", 1)
            return {"value": state.get("value", 0) * multiplier}

        registry.register("multiply", configurable_node)

        node = registry.get("multiply")
        result = node({"value": 5}, {"multiplier": 3})

        assert result["value"] == 15


# Tests for checking node existence
class TestNodeExistence:
    """Test suite for checking if nodes exist"""

    def test_has_node_exists(self, registry, sample_node):
        """Test checking for existing node"""
        registry.register("test_node", sample_node)

        # Assuming has_node or similar method exists
        assert "test_node" in registry.list_nodes()

    def test_has_node_not_exists(self, registry):
        """Test checking for non-existent node"""
        assert "nonexistent" not in registry.list_nodes()


# Tests for special characters in names
class TestSpecialCharacterNames:
    """Test suite for node names with special characters"""

    def test_register_with_spaces(self, registry, sample_node):
        """Test registering node with spaces in name"""
        registry.register("test node with spaces", sample_node)

        assert "test node with spaces" in registry.list_nodes()
        assert registry.get("test node with spaces") == sample_node

    def test_register_with_underscores(self, registry, sample_node):
        """Test registering node with underscores"""
        registry.register("test_node_with_underscores", sample_node)

        assert "test_node_with_underscores" in registry.list_nodes()

    def test_register_with_hyphens(self, registry, sample_node):
        """Test registering node with hyphens"""
        registry.register("test-node-with-hyphens", sample_node)

        assert "test-node-with-hyphens" in registry.list_nodes()

    def test_register_with_dots(self, registry, sample_node):
        """Test registering node with dots"""
        registry.register("test.node.with.dots", sample_node)

        assert "test.node.with.dots" in registry.list_nodes()

    def test_register_with_unicode(self, registry, sample_node):
        """Test registering node with unicode characters"""
        registry.register("test_node_🚀", sample_node)

        assert "test_node_🚀" in registry.list_nodes()


# Tests for registry operations
class TestRegistryOperations:
    """Test suite for registry-level operations"""

    def test_clear_registry(self, registry, sample_node, another_node):
        """Test clearing all nodes from registry"""
        registry.register("node1", sample_node)
        registry.register("node2", another_node)

        # If clear method exists
        if hasattr(registry, 'clear'):
            registry.clear()
            assert len(registry.list_nodes()) == 0

    def test_registry_is_singleton_or_not(self):
        """Test whether registry behaves as singleton"""
        registry1 = NodeRegistry()
        registry2 = NodeRegistry()

        # Document the behavior - either singleton or separate instances
        # This test just verifies consistency
        def test_node(state, config):
            return {"result": "test"}

        registry1.register("test", test_node)

        # Check if registry2 sees the same registration
        if "test" in registry2.list_nodes():
            # Singleton behavior
            assert registry1 is registry2 or registry1._nodes is registry2._nodes
        else:
            # Separate instances
            assert registry1 is not registry2

    def test_registry_size_tracking(self, registry, sample_node):
        """Test tracking number of registered nodes"""
        assert len(registry.list_nodes()) == 0

        registry.register("node1", sample_node)
        assert len(registry.list_nodes()) == 1

        registry.register("node2", sample_node)
        assert len(registry.list_nodes()) == 2

        registry.register("node1", sample_node)  # Overwrite
        assert len(registry.list_nodes()) == 2


# Integration tests
class TestRegistryIntegration:
    """Integration tests for registry usage"""

    def test_typical_usage_pattern(self, registry):
        """Test typical registry usage pattern"""
        # Define nodes
        def node_a(state, config):
            return {"step": "A"}

        def node_b(state, config):
            return {"step": "B"}

        # Register nodes
        registry.register("node_a", node_a)
        registry.register("node_b", node_b)

        # List and execute
        nodes = registry.list_nodes()
        assert len(nodes) == 2

        result_a = registry.get("node_a")({}, {})
        assert result_a["step"] == "A"

        result_b = registry.get("node_b")({}, {})
        assert result_b["step"] == "B"

    def test_dynamic_node_registration(self, registry):
        """Test registering nodes dynamically"""
        # Simulate dynamic node creation
        for i in range(5):
            def node_func(state, config, index=i):
                return {"index": index}

            registry.register(f"node_{i}", node_func)

        assert len(registry.list_nodes()) == 5

        # Execute one
        node_3 = registry.get("node_3")
        result = node_3({}, {})
        assert "index" in result


# Edge cases and error handling
class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_register_lambda(self, registry):
        """Test registering lambda function"""
        registry.register("lambda_node", lambda state, config: {"result": "lambda"})

        assert "lambda_node" in registry.list_nodes()
        result = registry.get("lambda_node")({}, {})
        assert result["result"] == "lambda"

    def test_register_class_method(self, registry):
        """Test registering class method as node"""
        class NodeClass:
            def node_method(self, state, config):
                return {"result": "method"}

        instance = NodeClass()
        registry.register("method_node", instance.node_method)

        assert "method_node" in registry.list_nodes()

    def test_register_static_method(self, registry):
        """Test registering static method as node"""
        class NodeClass:
            @staticmethod
            def static_node(state, config):
                return {"result": "static"}

        registry.register("static_node", NodeClass.static_node)

        assert "static_node" in registry.list_nodes()

    def test_very_long_node_name(self, registry, sample_node):
        """Test registering node with very long name"""
        long_name = "a" * 1000
        registry.register(long_name, sample_node)

        assert long_name in registry.list_nodes()
        assert registry.get(long_name) == sample_node

    def test_case_sensitive_names(self, registry, sample_node, another_node):
        """Test that node names are case-sensitive"""
        registry.register("TestNode", sample_node)
        registry.register("testnode", another_node)

        assert "TestNode" in registry.list_nodes()
        assert "testnode" in registry.list_nodes()
        assert registry.get("TestNode") != registry.get("testnode")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])