
import sys
import os
from pathlib import Path

# Add the src directory to sys.path to allow imports
project_root = Path(__file__).parent
src_path = project_root / "open_deep_research_example" / "src"
sys.path.append(str(src_path))

with open("debug_log.txt", "w") as f:
    f.write("Script started\n")

print("Starting imports...")
try:
    with open("debug_log.txt", "a") as f:
        f.write("Importing Current Graph...\n")
    print("Importing Current Graph...")
    from open_deep_research.deep_researcher import deep_researcher as current_graph
    print("Successfully imported Current Graph")
except ImportError as e:
    print(f"Error importing Current Graph: {e}")
    current_graph = None
except Exception as e:
    print(f"Unexpected error importing Current Graph: {e}")
    current_graph = None

try:
    print("Importing Legacy Workflow Graph...")
    from legacy.graph import graph as legacy_workflow_graph
    print("Successfully imported Legacy Workflow Graph")
except ImportError as e:
    print(f"Error importing Legacy Workflow Graph: {e}")
    legacy_workflow_graph = None
except Exception as e:
    print(f"Unexpected error importing Legacy Workflow Graph: {e}")
    legacy_workflow_graph = None

try:
    print("Importing Legacy Multi-Agent Graph...")
    from legacy.multi_agent import graph as legacy_multi_agent_graph
    print("Successfully imported Legacy Multi-Agent Graph")
except ImportError as e:
    print(f"Error importing Legacy Multi-Agent Graph: {e}")
    legacy_multi_agent_graph = None
except Exception as e:
    print(f"Unexpected error importing Legacy Multi-Agent Graph: {e}")
    legacy_multi_agent_graph = None

def visualize_graph(graph, name):
    if graph is None:
        print(f"Skipping {name} as it was not imported.")
        return

    print(f"\n{'='*20} {name} {'='*20}\n")

    # ASCII
    try:
        print(f"--- ASCII Representation of {name} ---")
        graph.get_graph().print_ascii()
    except Exception as e:
        print(f"Error printing ASCII for {name}: {e}")

    # Mermaid
    try:
        mermaid_code = graph.get_graph().draw_mermaid()
        print(f"\n--- Mermaid Diagram for {name} ---")
        print(mermaid_code)
        
        with open(f"{name.lower().replace(' ', '_')}.mermaid", "w", encoding="utf-8") as f:
            f.write(mermaid_code)
        print(f"Saved mermaid code to {name.lower().replace(' ', '_')}.mermaid")
    except Exception as e:
        print(f"Error drawing mermaid for {name}: {e}")

    # PNG
    try:
        png_data = graph.get_graph().draw_mermaid_png()
        with open(f"{name.lower().replace(' ', '_')}.png", "wb") as f:
            f.write(png_data)
        print(f"Saved PNG to {name.lower().replace(' ', '_')}.png")
    except Exception as e:
        print(f"Error saving PNG for {name}: {e}")
        print("Note: draw_mermaid_png requires a mermaid renderer (like mermaid-cli) to be installed or accessible.")

if __name__ == "__main__":
    # visualize_graph(current_graph, "Current Deep Research Graph")
    visualize_graph(legacy_workflow_graph, "Legacy Workflow Graph")
    visualize_graph(legacy_multi_agent_graph, "Legacy Multi-Agent Graph")
