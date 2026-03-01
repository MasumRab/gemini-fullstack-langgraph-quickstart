from typing import Callable, Dict, List


class GraphRegistry:
    """Metadata registry for documenting graph components and helper utilities.

    Work in Progress/Experimental: This registry is intended for documentation
    and metadata tracking. It does not affect the runtime logic of the graph,
    but provides a structure for future tooling or introspection.

    Rather than wiring the graph directly, this registry keeps track of node
    annotations, optional notes, and edge descriptions that can power docs or
    experimentation tooling.
    """

    def __init__(self):
        self.node_docs: Dict[str, Dict[str, object]] = {}
        self.edge_docs: List[Dict[str, str]] = []
        self.notes: List[str] = []

    def describe(
        self,
        name: str,
        *,
        summary: str,
        tags: List[str] | None = None,
        outputs: List[str] | None = None,
    ):
        """
        Create a decorator that registers documentation metadata for a graph node.
        
        The returned decorator records the node's handler name, summary, tags, and outputs in the registry under the provided name without altering the decorated function's behavior.
        
        Parameters:
            name (str): Key under which to store the node metadata in the registry.
            summary (str): Short description of the node's purpose.
            tags (List[str] | None): Optional list of tags for grouping or filtering; treated as an empty list if None.
            outputs (List[str] | None): Optional list of output names produced by the node; treated as an empty list if None.
        
        Returns:
            callable: A decorator that accepts a function, stores its metadata under `name`, and returns the original function.
        """

        def decorator(func: Callable):
            self.node_docs[name] = {
                "handler": func.__name__,
                "summary": summary,
                "tags": tags or [],
                "outputs": outputs or [],
            }
            return func

        return decorator

    def document_edge(self, source: str, target: str, *, description: str = ""):
        self.edge_docs.append(
            {
                "source": source,
                "target": target,
                "description": description,
            }
        )

    def add_note(self, note: str):
        self.notes.append(note)

    def render_overview(self) -> str:
        lines = ["Registered Nodes:"]
        for name, meta in self.node_docs.items():
            lines.append(
                f"- {name} ({meta['handler']}): {meta['summary']}"  # type: ignore[index]
            )
            if meta["tags"]:
                lines.append(f"    tags: {', '.join(meta['tags'])}")
            if meta["outputs"]:
                lines.append(f"    outputs: {', '.join(meta['outputs'])}")

        if self.edge_docs:
            lines.append("\nDocumented Edges:")
            for edge in self.edge_docs:
                desc = f" - {edge['description']}" if edge["description"] else ""
                lines.append(f"- {edge['source']} -> {edge['target']}{desc}")

        if self.notes:
            lines.append("\nNotes:")
            for note in self.notes:
                lines.append(f"- {note}")

        return "\n".join(lines)


# Singleton instance
graph_registry = GraphRegistry()
