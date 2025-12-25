#!/usr/bin/env python3
import os
import sys
import asyncio
import json
from datetime import datetime
from pathlib import Path

# Ensure backend modules are importable
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_SRC = REPO_ROOT / "backend" / "src"
sys.path.append(str(BACKEND_SRC))

# Import Agent Components
try:
    from agent.graph import graph
    from agent.configuration import Configuration
    from langchain_core.messages import HumanMessage
except ImportError as e:
    print(f"Error importing backend modules: {e}")
    sys.exit(1)

# Configurations to Run
# Topics:
# 1. Solid State Batteries (Fast vs Deep)
# 2. Remote Work (Broad)
# 3. Rust vs C++ (Technical)

CONFIGS = [
    {
        "name": "01_solid_state_batteries_fast",
        "topic": "Recent advances in Solid State Batteries (2024-2025)",
        "config": {
            "query_generator_model": "gemma-3-27b-it",
            "reflection_model": "gemma-3-27b-it",
            "answer_model": "gemma-3-27b-it",
            "number_of_initial_queries": 2,
            "max_research_loops": 1,
            "require_planning_confirmation": False
        }
    },
    {
        "name": "02_solid_state_batteries_deep",
        "topic": "Recent advances in Solid State Batteries (2024-2025)",
        "config": {
            "query_generator_model": "gemma-3-27b-it",
            "reflection_model": "gemma-3-27b-it",
            "answer_model": "gemma-3-27b-it",
            "number_of_initial_queries": 4,
            "max_research_loops": 3,
            "require_planning_confirmation": False
        }
    },
    {
        "name": "03_remote_work_broad",
        "topic": "Impact of Remote Work on Urban Planning",
        "config": {
            "query_generator_model": "gemma-3-27b-it",
            "reflection_model": "gemma-3-27b-it",
            "answer_model": "gemma-3-27b-it",
            "number_of_initial_queries": 6,
            "max_research_loops": 2,
            "require_planning_confirmation": False
        }
    },
    {
        "name": "04_rust_vs_cpp_technical",
        "topic": "Rust vs C++ for Embedded Systems",
        "config": {
            "query_generator_model": "gemma-3-27b-it",
            "reflection_model": "gemma-3-27b-it",
            "answer_model": "gemma-3-27b-it",
            "number_of_initial_queries": 3,
            "max_research_loops": 2,
            "require_planning_confirmation": False
        }
    }
]

OUTPUT_DIR = REPO_ROOT / "docs" / "sample_reports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def generate_report(run_config):
    name = run_config["name"]
    topic = run_config["topic"]
    conf_dict = run_config["config"]

    print(f"\n--- Starting Run: {name} ---")
    print(f"Topic: {topic}")
    print(f"Config: {conf_dict}")

    inputs = {
        "messages": [HumanMessage(content=topic)]
    }

    # Configuration wrapper for LangGraph
    # We pass the Configuration object fields via 'configurable' dict
    runnable_config = {
        "configurable": {
            "thread_id": f"sample_report_{name}_{int(datetime.now().timestamp())}",
            **conf_dict
        },
        "recursion_limit": 100
    }

    report_content = ""
    metadata = {}

    start_time = datetime.now()

    try:
        # Execute Graph
        final_state = await graph.ainvoke(inputs, runnable_config)

        # Extract Final Answer
        if "messages" in final_state and final_state["messages"]:
            last_msg = final_state["messages"][-1]
            report_content = last_msg.content
        else:
            report_content = "No final answer generated."

        # Collect Metadata
        duration = (datetime.now() - start_time).total_seconds()
        metadata = {
            "duration_seconds": duration,
            "total_steps": len(final_state.get("messages", [])), # Proxy for steps
            "research_loops_performed": conf_dict.get("max_research_loops"),
            "model": conf_dict.get("query_generator_model")
        }

    except Exception as e:
        print(f"Error generating report for {name}: {e}")
        report_content = f"Error generating report: {str(e)}"
        import traceback
        traceback.print_exc()

    # Save Artifacts
    # 1. Markdown Report
    md_filename = OUTPUT_DIR / f"{name}.md"

    header = f"""# Sample Report: {topic}
> **Configuration**: {name}
> **Model**: {conf_dict['query_generator_model']}
> **Depth**: {conf_dict['max_research_loops']} Loops
> **Breadth**: {conf_dict['number_of_initial_queries']} Initial Queries
> **Duration**: {metadata.get('duration_seconds', 0):.2f}s

---

"""
    with open(md_filename, "w", encoding="utf-8") as f:
        f.write(header + report_content)

    print(f"Saved report to {md_filename}")
    return metadata

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=int, help="Index of config to run (0-3)")
    args = parser.parse_args()

    if args.index is not None:
        if 0 <= args.index < len(CONFIGS):
            run = CONFIGS[args.index]
            await generate_report(run)
        else:
            print(f"Index {args.index} out of range.")
    else:
        results = []
        for run in CONFIGS:
            meta = await generate_report(run)
            results.append({"name": run["name"], "meta": meta})

        print("\nAll runs complete.")
        print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
