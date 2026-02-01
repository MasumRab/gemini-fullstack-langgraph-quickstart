import sys

print(sys.path)
try:
    import agent

    print(f"Agent: {agent}")
except ImportError as e:
    print(f"ImportError: {e}")
