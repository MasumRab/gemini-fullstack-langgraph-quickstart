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
        """Decorator that records metadata for a node without altering wiring."""

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
