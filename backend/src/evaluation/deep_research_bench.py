# Fine-grained implementation guide for DeepResearch-Bench Evaluation:
#
# TODO(priority=High, complexity=Low): [deep_bench:1] Dataset loader
# - Connect to muset-ai/DeepResearch-Bench on HuggingFace
# - Implement load_deep_research_dataset() -> List[Task]
# - Each Task: {id, query, gold_report, evaluation_criteria}
#
# TODO(priority=High, complexity=Medium): [deep_bench:2] Agent runner
# - Import graph from agent.graph
# - Configure for full research mode (scoping -> planning -> research -> synthesis)
# - Capture final report and all intermediate artifacts
#
# TODO(priority=Medium, complexity=High): [deep_bench:3] Report scorer
# - Compare generated report against gold_report
# - Use metrics: ROUGE-L, BERTScore, factual accuracy (via NLI)
# - Return composite score (0.0-1.0)
#
# TODO(priority=Medium, complexity=Medium): [deep_bench:4] Citation verifier
# - Check that all claims are backed by sources
# - Verify source URLs are valid and content matches claims
# - Return citation_coverage score
#
# TODO(priority=Medium, complexity=Low): [deep_bench:5] Metrics aggregator
# - Aggregate scores across all tasks
# - Compute mean, std, percentiles
# - Track token usage and latency
#
# TODO(priority=Low, complexity=Low): [deep_bench:6] Report generator
# - Output results to JSON and Markdown
# - Generate comparison charts (if multiple runs)
#
# See docs/tasks/04_SOTA_DEEP_RESEARCH_TASKS.md

def evaluate_deep_research():
    """
    Evaluates the agent on DeepResearch-Bench (muset-ai).
    """
    # TODO(priority=High, complexity=Low): [deep_bench:1] Load dataset
    dataset = []  # load_deep_research_dataset()
    
    # TODO(priority=High, complexity=Medium): [deep_bench:2] Run agent
    results = []
    for task in dataset:
        # report = run_full_research(task.query)
        # results.append({"task_id": task.id, "report": report})
        pass
    
    # TODO(priority=Medium, complexity=High): [deep_bench:3] Score reports
    scores = []
    # for result in results:
    #     score = score_report(result["report"], gold_report)
    #     scores.append(score)
    
    # TODO(priority=Medium, complexity=Medium): [deep_bench:4] Verify citations
    # for result in results:
    #     citation_score = verify_citations(result["report"])
    
    # TODO(priority=Medium, complexity=Low): [deep_bench:5] Aggregate
    # mean_score = sum(scores) / len(scores) if scores else 0
    
    # TODO(priority=Low, complexity=Low): [deep_bench:6] Report
    print("DeepResearch-Bench evaluation not yet implemented")

if __name__ == "__main__":
    evaluate_deep_research()

