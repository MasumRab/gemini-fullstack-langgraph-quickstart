
import sys
import os

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), 'src'))

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
