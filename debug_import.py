
import sys
import os
from pathlib import Path

# Add backend/src to sys.path
project_root = Path(__file__).parent
backend_src_path = project_root / "backend" / "src"
sys.path.append(str(backend_src_path))

# Set dummy API key
if "GEMINI_API_KEY" not in os.environ:
    os.environ["GEMINI_API_KEY"] = "dummy_key_for_visualization"

print(f"sys.path: {sys.path}")

try:
    print("Attempting to import agent.graph...")
    from agent.graph import graph
    print("Successfully imported agent.graph")
except Exception as e:
    print(f"Error importing agent.graph: {e}")
    import traceback
    traceback.print_exc()
