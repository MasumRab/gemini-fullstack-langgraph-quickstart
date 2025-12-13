# 📊 Agent Visualization Guide

This guide explains how to visualize and inspect the Deep Research Agent's graph architecture.

## 1. Quick Visualization (Jupyter Notebook)

The easiest way to visualize the graph is using the provided notebooks.

```python
from agent.graph import graph
from IPython.display import Image, display

# Draw the graph as a PNG
try:
    png_data = graph.get_graph().draw_mermaid_png()
    display(Image(png_data))
except Exception as e:
    print(f"Visualization failed: {e}")
    # Fallback to ASCII
    graph.get_graph().print_ascii()
```

## 2. Command Line Visualization

You can generate a Mermaid diagram file directly from the CLI.

```bash
# Generate mermaid file
python scripts/visualize_graph.py --output agent_graph.mermaid
```

*(Note: `scripts/visualize_graph.py` needs to be created if not present)*

## 3. LangGraph Studio (Interactive)

For the best experience, use **LangGraph Studio**.

1. Install LangGraph CLI:
   ```bash
   pip install langgraph-cli
   ```

2. Start the development server:
   ```bash
   langgraph dev
   ```

3. Open the provided URL (usually `http://localhost:8123`) to interact with the graph, view traces, and inspect state.

## 4. Understanding the Graph Components

### Main Graph (`agent.graph`)
The high-level orchestration graph.
- **Start**: Entry point.
- **Planning**: Generates the research plan.
- **Research Loop**: Executes web search and reflection.
- **Finalize**: Synthesizes the answer.

### Subgraphs
Complex nodes like `web_research` can be expanded into subgraphs in LangGraph Studio.

## 5. Troubleshooting Visualization

**"GraphvizExecutableNotFound"**
- Install Graphviz on your system (`brew install graphviz` or `sudo apt-get install graphviz`).
- Alternatively, use `draw_mermaid_png()` which relies on an external API or local mermaid-cli, often easier to set up.

**"Mermaid rendering failed"**
- Ensure you are in an environment that supports image display (like Jupyter).
- If running in a script, save the output to a file:
  ```python
  with open("graph.png", "wb") as f:
      f.write(graph.get_graph().draw_mermaid_png())
  ```

## 6. External Resources & Tutorials

Here are some excellent resources for learning more about visualizing LangGraph agents:

**Video Tutorials:**
- [LangSmith Studio: An IDE for visualizing and debugging agents](https://www.youtube.com/watch?v=7kL5_vP-k-4) - Official guide to the interactive visualize.
- [How to visualize a LangGraph?](https://www.youtube.com/watch?v=q3aKq3bC-nE) - Quick tutorial on PNG/ASCII visualization.
- [Getting Started with LangGraph](https://www.youtube.com/watch?v=9LpL_uP4-e8) - General intro including visualization concepts.

**Documentation & Articles:**
- [LangGraph Official Docs: Visualization](https://langchain-ai.github.io/langgraph/how-tos/visualization/) - The definitive guide.
- [Laminar Integration](https://lmnr.ai/docs/integrations/langgraph) - Using Laminar to trace and visualize graph execution.
