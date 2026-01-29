
import os
import sys

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    print("Successfully imported Configuration")
except Exception as e:
    print(f"Failed to import Configuration: {e}")

try:
    print("Successfully imported nodes")
except Exception as e:
    print(f"Failed to import nodes: {e}")
