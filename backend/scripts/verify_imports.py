import os
import sys

# Add src to sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(script_dir, "..", "src"))

try:
    from agent.configuration import Configuration

    print("Successfully imported Configuration")
except Exception as e:
    print(f"Failed to import Configuration: {e}")

try:
    from agent.nodes import generate_query

    print("Successfully imported nodes")
except Exception as e:
    print(f"Failed to import nodes: {e}")
