"""Benchmark script to evaluate agent performance against reference questions."""

import json
import logging
import time
import os
import argparse
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Try to import graph - handle import error if app structure is different
try:
    from agent.graph import graph
    from agent.models import DEFAULT_ANSWER_MODEL
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))
    from agent.graph import graph
    from agent.models import DEFAULT_ANSWER_MODEL

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_benchmark_data(path: str) -> List[Dict[str, Any]]:
    """Load benchmark questions from JSON file."""
    if not os.path.exists(path):
        logger.error(f"Benchmark file not found: {path}")
        return []

    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load benchmark data: {e}")
        return []

async def run_single_benchmark(item: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single benchmark item."""
    question = item.get("question")
    if not question:
        return {"error": "Missing question", "status": "skipped"}

    start_time = time.time()
    try:
        # Prepare input
        inputs = {"messages": [{"role": "user", "content": question}]}

        # Run agent
        result = await graph.ainvoke(inputs, config=config)

        # Extract answer (assuming standard graph output structure)
        messages = result.get("messages", [])
        final_answer = "No answer produced"
        if messages:
            last_msg = messages[-1]
            if isinstance(last_msg, dict):
                final_answer = last_msg.get("content", str(last_msg))
            else:
                final_answer = getattr(last_msg, "content", str(last_msg))

        duration = time.time() - start_time

        return {
            "question": question,
            "answer": final_answer,
            "duration": duration,
            "status": "success",
            "expected_topics": item.get("expected_topics", [])
        }
    except Exception as e:
        logger.error(f"Error processing '{question}': {e}")
        return {
            "question": question,
            "error": str(e),
            "duration": time.time() - start_time,
            "status": "failed"
        }

async def run_benchmark(data_path: str, output_path: str = "benchmark_report.md"):
    """Run full benchmark suite."""
    data = load_benchmark_data(data_path)
    if not data:
        logger.warning("No data to benchmark.")
        return

    results = []
    logger.info(f"Starting benchmark with {len(data)} questions...")

    # Configure agent for benchmark (e.g. no human-in-the-loop)
    config = {
        "configurable": {
            "thread_id": "benchmark_run",
            "model_name": DEFAULT_ANSWER_MODEL,
            "require_planning_confirmation": False
        }
    }

    # Run sequentially for now to avoid rate limits, or use semaphore if needed
    for item in data:
        res = await run_single_benchmark(item, config)
        results.append(res)
        logger.info(f"Completed: {item.get('question', 'Unknown')[:30]}... ({res['status']})")

    # Generate Report
    generate_report(results, output_path)

def generate_report(results: List[Dict[str, Any]], output_path: str):
    """Generate a markdown report of results."""
    success_count = sum(1 for r in results if r["status"] == "success")
    total_time = sum(r.get("duration", 0) for r in results)
    avg_time = total_time / len(results) if results else 0

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Benchmark Report\n\n")
        f.write(f"- **Total Questions**: {len(results)}\n")
        f.write(f"- **Success Rate**: {success_count}/{len(results)}\n")
        f.write(f"- **Average Time**: {avg_time:.2f}s\n\n")
        
        f.write("## Detailed Results\n\n")
        for res in results:
            f.write(f"### Q: {res.get('question', 'N/A')}\n")
            f.write(f"- **Status**: {res['status']}\n")
            f.write(f"- **Time**: {res.get('duration', 0):.2f}s\n")
            if res["status"] == "success":
                f.write(f"- **Answer Snippet**: {str(res.get('answer', ''))[:200]}...\n")
            else:
                f.write(f"- **Error**: {res.get('error')}\n")
            f.write("\n---\n")

    logger.info(f"Report saved to {output_path}")

if __name__ == "__main__":
    import asyncio

    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="tests/data/benchmark_questions.json", help="Path to benchmark data")
    args = parser.parse_args()

    # Resolve path relative to script if needed
    data_path = args.data
    if not os.path.exists(data_path):
        # Try finding it relative to backend root
        alt_path = os.path.join(os.path.dirname(__file__), "..", data_path)
        if os.path.exists(alt_path):
            data_path = alt_path

    asyncio.run(run_benchmark(data_path))
