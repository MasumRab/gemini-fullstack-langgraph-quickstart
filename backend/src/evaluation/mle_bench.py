# Fine-grained implementation guide for MLE-bench Evaluation:
#
# TODO(priority=High, complexity=Low): [mle_bench:1] Dataset loader
# - Define path to MLE-bench dataset (HuggingFace or local)
# - Implement load_mle_dataset() -> List[Task]
# - Each Task: {id, prompt, expected_output, metadata}
#
# TODO(priority=High, complexity=Medium): [mle_bench:2] Agent runner
# - Import graph from agent.graph
# - Run graph.invoke({"messages": [task.prompt]})
# - Capture final output and execution time
#
# TODO(priority=Medium, complexity=Medium): [mle_bench:3] Output evaluator
# - Compare agent output against expected_output
# - Implement exact_match, fuzzy_match, and llm_judge scoring
# - Return score (0.0-1.0) per task
#
# TODO(priority=Medium, complexity=Low): [mle_bench:4] Metrics aggregator
# - Compute Pass@1 (% tasks with score >= threshold)
# - Compute average score across all tasks
# - Track latency percentiles (p50, p95, p99)
#
# TODO(priority=Low, complexity=Low): [mle_bench:5] Report generator
# - Output results to JSON and Markdown
# - Include per-task breakdown and aggregate stats
#
# See docs/tasks/04_SOTA_DEEP_RESEARCH_TASKS.md

def evaluate_mle_bench():
    """
    Evaluates the agent on MLE-bench tasks.
    """
    # TODO(priority=High, complexity=Low): [mle_bench:1] Load dataset
    dataset = []  # load_mle_dataset()
    
    # TODO(priority=High, complexity=Medium): [mle_bench:2] Run agent
    results = []
    for task in dataset:
        # output = run_agent(task.prompt)
        # results.append({"task_id": task.id, "output": output})
        pass
    
    # TODO(priority=Medium, complexity=Medium): [mle_bench:3] Evaluate
    scores = []
    # for result in results:
    #     score = evaluate_output(result["output"], ...)
    #     scores.append(score)
    
    # TODO(priority=Medium, complexity=Low): [mle_bench:4] Aggregate
    # pass_at_1 = sum(1 for s in scores if s >= 0.5) / len(scores)
    # avg_score = sum(scores) / len(scores)
    
    # TODO(priority=Low, complexity=Low): [mle_bench:5] Report
    print("MLE-bench evaluation not yet implemented")

if __name__ == "__main__":
    evaluate_mle_bench()

