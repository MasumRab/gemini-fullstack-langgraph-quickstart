
import sys
import os

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    import agent
    print(f"Agent module: {agent}")
    print(f"Agent file: {getattr(agent, '__file__', 'unknown')}")
    print(f"Agent path: {getattr(agent, '__path__', 'unknown')}")
except Exception as e:
    print(f"Failed to import agent: {e}")

try:
    from agent import configuration
    print("Successfully imported agent.configuration")
except Exception as e:
    print(f"Failed to import agent.configuration: {e}")
