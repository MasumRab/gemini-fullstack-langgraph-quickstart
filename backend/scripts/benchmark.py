"""Benchmark Orchestration Script

This script runs the agent against a dataset of questions and evaluates performance 
using the evaluators defined in backend/tests/evaluators.py.
"""

import asyncio
import logging
from typing import List, Dict, Any
from agent.graph import graph
from tests.evaluators import eval_quality, eval_groundedness

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# TODO(priority=High, complexity=Medium): [Benchmarking] Dataset Loading
# Implement logic to load questions from a JSON file or LangSmith dataset.
# See backend/docs/benchmarks/PLAN.md
QUESTIONS = [
    {"question": "What are the latest developments in rooms-temperature superconductivity as of 2025?", "expected_topics": ["LK-99", "Reddmatter", "high pressure"]},
]

async def run_benchmark():
    """Run evaluation for all questions."""
    results = []
    
    for item in QUESTIONS:
        question = item["question"]
        logger.info(f"Running benchmark for: {question}")
        
        # TODO(priority=Medium, complexity=Low): [Benchmarking] Agent Invocation
        # Call agent graph. Ensure planning_status is auto_approved.
        try:
            # response = await graph.ainvoke({"messages": [("user", question)]})
            # content = response["messages"][-1].content
            pass
        except Exception as e:
            logger.error(f"Agent failed: {e}")
            continue

        # TODO(priority=High, complexity=Low): [Benchmarking] Evaluation Call
        # Pass the result to eval_quality and eval_groundedness.
        # Store results for reporting.
        
    # TODO(priority=Low, complexity=Medium): [Benchmarking] Report Generation
    # Summarize scores (Mean, Variance) and output as Markdown or JSON.

if __name__ == "__main__":
    asyncio.run(run_benchmark())
