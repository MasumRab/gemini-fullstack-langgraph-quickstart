
import sys
import os
from pathlib import Path

# Add the src directory to sys.path to allow imports
# backend/scripts/visualize_agent_graph.py -> backend/scripts -> backend -> root
project_root = Path(__file__).parent.parent.parent

# Updated path to reflect the move to examples/open_deep_research_example
src_path = project_root / "examples" / "open_deep_research_example" / "src"
sys.path.append(str(src_path))

def visualize_graph(graph, name):
    if graph is None:
        print(f"Skipping {name} as it was not imported.")
        return

    print(f"\n{'='*20} {name} {'='*20}\n")

    # Mermaid
    try:
        mermaid_code = graph.get_graph().draw_mermaid()
        print(f"\n--- Mermaid Diagram for {name} ---")
        print(mermaid_code)
        
        filename = name.lower().replace(' ', '_')
        with open(f"{filename}.mermaid", "w", encoding="utf-8") as f:
            f.write(mermaid_code)
        print(f"Saved mermaid code to {filename}.mermaid")

        # Try PNG
        try:
            png_data = graph.get_graph().draw_mermaid_png()
            with open(f"{filename}.png", "wb") as f:
                f.write(png_data)
            print(f"Saved PNG to {filename}.png")
        except Exception as e:
            print(f"Could not save PNG for {name} (likely missing mermaid-cli): {e}")

    except Exception as e:
        print(f"Error drawing mermaid for {name}: {e}")

    # ASCII (fallback/quick view)
    try:
        print(f"\n--- ASCII Representation of {name} ---")
        graph.get_graph().print_ascii()
    except Exception as e:
        print(f"Error printing ASCII for {name}: {e}")

    sys.stdout.flush()

print("Starting visualization script...", flush=True)

# 1. Current Deep Research Graph & Subgraphs
# try:
#     print("Importing Current Deep Research Graph...", flush=True)
#     from open_deep_research.deep_researcher import (
#         deep_researcher as current_graph,
#         supervisor_subgraph,
#         researcher_subgraph
#     )
#     print("Successfully imported Current Deep Research Graph and Subgraphs", flush=True)

#     visualize_graph(current_graph, "Current Deep Research Graph")
#     visualize_graph(supervisor_subgraph, "Current Supervisor Subgraph")
#     visualize_graph(researcher_subgraph, "Current Researcher Subgraph")

# except ImportError as e:
#     print(f"Error importing Current Deep Research Graph: {e}", flush=True)
# except Exception as e:
#     print(f"Unexpected error importing Current Deep Research Graph: {e}", flush=True)

# # 2. Legacy Workflow Graph
# try:
#     print("Importing Legacy Workflow Graph...", flush=True)
#     from legacy.graph import graph as legacy_workflow_graph
#     print("Successfully imported Legacy Workflow Graph", flush=True)
#     visualize_graph(legacy_workflow_graph, "Legacy Workflow Graph")
# except ImportError as e:
#     print(f"Error importing Legacy Workflow Graph: {e}", flush=True)
# except Exception as e:
#     print(f"Unexpected error importing Legacy Workflow Graph: {e}", flush=True)

# # 3. Legacy Multi-Agent Graph
# try:
#     print("Importing Legacy Multi-Agent Graph...", flush=True)
#     from legacy.multi_agent import graph as legacy_multi_agent_graph
#     print("Successfully imported Legacy Multi-Agent Graph", flush=True)
#     visualize_graph(legacy_multi_agent_graph, "Legacy Multi-Agent Graph")
# except ImportError as e:
#     print(f"Error importing Legacy Multi-Agent Graph: {e}", flush=True)
# except Exception as e:
#     print(f"Unexpected error importing Legacy Multi-Agent Graph: {e}", flush=True)


# 4. Proposed Improved Graph (Planning Agent)
try:
    print("Importing Proposed Improved Graph (Planning Agent)...", flush=True)

    # Add backend/src to sys.path
    backend_src_path = project_root / "backend" / "src"
    sys.path.append(str(backend_src_path))

    # Set dummy API key to avoid ValueError during import if not set
    if "GEMINI_API_KEY" not in os.environ:
        os.environ["GEMINI_API_KEY"] = "dummy_key_for_visualization"

    from agent.graph import graph as proposed_graph
    print("Successfully imported Proposed Improved Graph", flush=True)
    visualize_graph(proposed_graph, "Proposed Improved Graph")
except ImportError as e:
    print(f"Error importing Proposed Improved Graph: {e}", flush=True)
except Exception as e:
    print(f"Unexpected error importing Proposed Improved Graph: {e}", flush=True)

print("Visualization script finished.", flush=True)
