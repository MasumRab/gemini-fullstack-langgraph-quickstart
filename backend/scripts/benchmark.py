"""Benchmark Orchestration Script

This script runs the agent against a dataset of questions and evaluates performance 
using the evaluators defined in backend/tests/evaluators.py.
"""

import asyncio
import logging
import json
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load env vars before importing evaluators or agent components
load_dotenv()

from agent.graph import graph
try:
    from tests.evaluators import eval_quality, eval_groundedness
except ImportError:
    # This might happen if running script directly without module context
    # But usually handled by running as `python -m scripts.benchmark`
    raise

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path relative to backend root
DATASET_PATH = os.path.join("tests", "data", "benchmark_questions.json")

def load_dataset(path: str) -> List[Dict[str, Any]]:
    """Load questions from a JSON file."""
    if not os.path.exists(path):
        # Try finding it relative to script if run differently
        script_dir = os.path.dirname(os.path.abspath(__file__))
        alt_path = os.path.join(script_dir, "..", path)
        if os.path.exists(alt_path):
            path = alt_path
        else:
            logger.error(f"Dataset not found at {path}")
            return []

    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        return []

async def run_benchmark():
    """Run evaluation for all questions."""
    questions = load_dataset(DATASET_PATH)
    if not questions:
        logger.warning("No questions loaded. Exiting.")
        return

    results = []
    
    for item in questions:
        question = item["question"]
        expected_topics = item.get("expected_topics", [])
        logger.info(f"Running benchmark for: {question}")
        
        try:
            # Invoke agent
            # We rely on the agent graph to handle the flow.
            # If the graph requires user input (e.g. scoping), it might stop or need handling.
            # For automation, we assume the graph can run autonomously or we'd need to mock input.
            # Increase recursion limit to handle multi-step research plans (default is 25)
            # Disable planning confirmation to allow automated execution
            response = await graph.ainvoke({
                "messages": [("user", question)]
            }, config={
                "recursion_limit": 100,
                "configurable": {"require_planning_confirmation": False}
            })

            # Extract final answer from the last message content
            messages = response.get("messages", [])
            final_content = ""
            if messages:
                final_content = messages[-1].content
            else:
                logger.warning(f"No messages returned for '{question}'")

            # Extract sources
            sources = response.get("sources_gathered", [])
            if not sources:
                # Fallback to checking web_research_result if sources_gathered is empty
                # web_research_result is usually a list of strings (summaries)
                sources = response.get("web_research_result", [])

            # Ensure sources is a list of strings
            sources_list = []
            for s in sources:
                if isinstance(s, dict):
                    # If source is a dictionary (e.g. Evidence), convert to string
                    sources_list.append(str(s))
                else:
                    sources_list.append(str(s))

            # Evaluate
            logger.info("Evaluating quality...")
            quality_result = eval_quality(question, final_content)

            logger.info("Evaluating groundedness...")
            groundedness_result = eval_groundedness(final_content, sources_list)

            result_entry = {
                "question": question,
                "expected_topics": expected_topics,
                "quality_score": quality_result.get("score", 0),
                "quality_reasoning": quality_result.get("metadata", {}).get("reasoning", "No reasoning provided"),
                "groundedness_score": groundedness_result.get("score", 0),
                "groundedness_reasoning": groundedness_result.get("metadata", {}).get("reasoning", "No reasoning provided"),
                "final_answer_snippet": (final_content[:200] + "...") if final_content else "No content"
            }
            results.append(result_entry)

            logger.info(f"Result for '{question}': Q={result_entry['quality_score']}, G={result_entry['groundedness_score']}")

        except Exception as e:
            logger.error(f"Agent failed for '{question}': {e}", exc_info=True)
            continue

    # Report Generation
    if results:
        avg_quality = sum(r["quality_score"] for r in results) / len(results)
        avg_groundedness = sum(r["groundedness_score"] for r in results) / len(results)

        report = f"""
# Benchmark Report

**Average Quality Score:** {avg_quality:.2f}
**Average Groundedness Score:** {avg_groundedness:.2f}

## Detailed Results
"""
        for r in results:
            report += f"""
### {r['question']}
- **Quality:** {r['quality_score']}
  - *Reasoning:* {r['quality_reasoning']}
- **Groundedness:** {r['groundedness_score']}
  - *Reasoning:* {r['groundedness_reasoning']}
- **Snippet:** {r['final_answer_snippet']}
"""
        print(report)
        
        # Save to file
        with open("benchmark_report.md", "w") as f:
            f.write(report)
        logger.info("Report saved to benchmark_report.md")
    else:
        logger.warning("No results to report.")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
