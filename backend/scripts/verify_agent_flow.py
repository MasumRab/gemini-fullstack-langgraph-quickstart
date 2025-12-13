import asyncio
import os
import sys

# Setup Path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "backend", "src"))

from langchain_core.messages import HumanMessage
from agent.graph import graph
from config.app_config import config

async def run_full_flow():
    """
    Run a full agent flow verification using the graph runner and print status and results.
    
    Constructs a mock input (single HumanMessage and a short search count), invokes the graph runner with a test thread id, and prints progress, the truncated final answer when available, and the count of any validation notes. On error, prints an error message and a traceback.
    """
    print("Running Full Agent Flow Verification...")
    print(f"Config: {config}")

    # Mock Input
    inputs = {
        "messages": [HumanMessage(content="What are the latest features of LangChain?")],
        "initial_search_query_count": 1 # Keep it fast
    }

    config_run = {"configurable": {"thread_id": "test_thread_1"}}

    # Run the graph
    print("Invoking graph...")
    try:
        final_state = await graph.ainvoke(inputs, config_run)

        print("\n--- Flow Complete ---")
        if "messages" in final_state and final_state["messages"]:
            print(f"Final Answer: {final_state['messages'][-1].content[:200]}...")
        else:
            print("No final answer produced.")

        # Check if new nodes were visited
        # We can't easily check 'visited' without trace, but we can check if keys exist in state if they modify it
        # validation_notes exists
        if "validation_notes" in final_state:
            print(f"Validation Notes: {len(final_state['validation_notes'])}")

    except Exception as e:
        print(f"Flow Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_full_flow())