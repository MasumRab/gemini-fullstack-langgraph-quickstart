import json
import logging
from pathlib import Path
from typing import Dict, List

import numpy as np
from tqdm import tqdm

# We assume 'agent' and 'evaluation' are in python path
from agent.deep_search_agent import DeepSearchAgent
from evaluation.metrics import DeepResearchMetrics

logger = logging.getLogger(__name__)


class BenchmarkEvaluator:
    """Complete evaluation pipeline for DeepResearch-Bench.
    Matches the leaderboard evaluation protocol.
    """

    def __init__(self, agent: DeepSearchAgent, data_dir: str = "data/benchmark"):
        """
        Initialize the BenchmarkEvaluator with an agent and benchmark data directory.
        
        Parameters:
            agent (DeepSearchAgent): Agent used to run research queries during evaluation.
            data_dir (str): Path to the benchmark data directory containing `criteria.jsonl` and `reference.jsonl`. Defaults to `"data/benchmark"`.
        
        Description:
            Stores the agent and data directory, initializes the metrics collector, loads criteria and reference entries from the data directory, and builds a lookup mapping from `query_id` to reference entry for quick access during evaluation.
        """
        self.agent = agent
        self.data_dir = Path(data_dir)
        self.metrics = DeepResearchMetrics()

        # Load benchmark data
        self.criteria = self._load_jsonl(self.data_dir / "criteria.jsonl")
        self.references = self._load_jsonl(self.data_dir / "reference.jsonl")

        # Create lookup
        self.ref_lookup = {r["query_id"]: r for r in self.references}

    def _load_jsonl(self, file_path: Path) -> List[Dict]:
        """
        Load a JSON Lines (JSONL) file and return a list of parsed JSON objects.
        
        If the file does not exist, a warning is logged and an empty list is returned. Blank lines are skipped; each non-blank line is parsed as a JSON object and appended to the result.
        
        Parameters:
            file_path (Path): Path to the JSON Lines file to load.
        
        Returns:
            List[Dict]: A list of dictionaries, one per parsed JSON line.
        
        Raises:
            json.JSONDecodeError: If a non-blank line contains invalid JSON.
        """
        data = []
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return []
        with open(file_path) as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
        return data

    def evaluate_full_benchmark(
        self,
        output_file: str = "results/benchmark_results.json",
        save_detailed: bool = True,
    ) -> Dict:
        """
        Run the full benchmark over all criteria and produce aggregated leaderboard-style scores.
        
        Parameters:
            output_file (str): Path to write the JSON results file.
            save_detailed (bool): If True, include per-query detailed results in the output file.
        
        Returns:
            final_scores (Dict): Mapping of aggregated metric names to their computed values, including:
                - overall_score (float): Weighted leaderboard score scaled 0–100.
                - pass_at_1_accuracy (float): Mean Pass@1 accuracy as a percentage (0–100).
                - evidence_quality (float): Mean evidence quality score as a percentage (0–100).
                - subgoal_completion (float): Mean subgoal completion rate as a percentage (0–100).
                - hallucination_rate (float): Mean hallucination rate as a percentage (0–100).
                - context_efficiency (float): Mean context efficiency score (raw scale).
                - num_queries_evaluated (int): Number of queries that were successfully evaluated.
        """
        all_results = []
        aggregate_scores = {
            "pass_at_1": [],
            "evidence_quality": [],
            "subgoal_completion": [],
            "hallucination_rate": [],
            "context_efficiency": [],
        }

        logger.info(f"Evaluating {len(self.criteria)} queries...")

        # Use tqdm if running in interactive/console mode
        iterator = tqdm(self.criteria) if len(self.criteria) > 0 else []

        for criterion in iterator:
            query_id = criterion["query_id"]
            # query = criterion["query"] # unused locally

            # Get reference data
            reference = self.ref_lookup.get(query_id)
            if not reference:
                logger.warning(f"Warning: No reference for {query_id}")
                continue

            # Run agent
            try:
                result = self._evaluate_single_query(criterion, reference)
                all_results.append(result)

                # Aggregate scores
                aggregate_scores["pass_at_1"].append(result["pass_at_1"]["score"])
                aggregate_scores["evidence_quality"].append(
                    result["evidence_quality"]["quality_score"]
                )
                aggregate_scores["subgoal_completion"].append(
                    result["subgoal_completion"]["completion_rate"]
                )
                aggregate_scores["hallucination_rate"].append(
                    result["hallucination"]["hallucination_rate"]
                )
                aggregate_scores["context_efficiency"].append(
                    result["context_efficiency"]["efficiency_score"]
                )

            except Exception as e:
                logger.error(f"Error evaluating {query_id}: {e}")
                import traceback

                traceback.print_exc()
                continue

        if not all_results:
            logger.warning("No results generated.")
            return {}

        # Calculate final scores
        final_scores = {
            "overall_score": self._calculate_overall_score(aggregate_scores),
            "pass_at_1_accuracy": float(np.mean(aggregate_scores["pass_at_1"]) * 100),
            "evidence_quality": float(
                np.mean(aggregate_scores["evidence_quality"]) * 100
            ),
            "subgoal_completion": float(
                np.mean(aggregate_scores["subgoal_completion"]) * 100
            ),
            "hallucination_rate": float(
                np.mean(aggregate_scores["hallucination_rate"]) * 100
            ),
            "context_efficiency": float(
                np.mean(aggregate_scores["context_efficiency"])
            ),
            "num_queries_evaluated": len(all_results),
        }

        # Save results
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(
                {
                    "final_scores": final_scores,
                    "detailed_results": all_results if save_detailed else [],
                },
                f,
                indent=2,
            )

        logger.info(f"\n✓ Evaluation complete. Results saved to {output_path}")
        self._print_summary(final_scores)

        return final_scores

    def _evaluate_single_query(self, criterion: Dict, reference: Dict) -> Dict:
        """
        Evaluate a single benchmark query and compute the full set of evaluation metrics.
        
        Parameters:
            criterion (Dict): Benchmark criterion containing at least the keys:
                - "query": the natural-language query to evaluate.
                - "query_id": unique identifier for the query.
                - "subgoals": list of subgoals used for subgoal completion measurement.
            reference (Dict): Reference data containing at least the keys:
                - "reference_answer": the canonical answer for the query.
                - "key_facts": facts required for Pass@1 evaluation.
                - "required_sources": source identifiers expected for evidence quality.
                - "min_evidence_count": minimum evidence items expected.
        
        Returns:
            Dict: A results dictionary with the following keys:
                - "query_id": the provided query identifier.
                - "query": the evaluated query text.
                - "generated_answer": the agent-produced answer text.
                - "pass_at_1": Pass@1 evaluation result (score object/dict indicating match to reference).
                - "evidence_quality": numeric score assessing retrieved evidence relevance/coverage (typically 0–1).
                - "subgoal_completion": numeric rate of completed subgoals (typically 0–1).
                - "hallucination": numeric hallucination rate (typically 0–1).
                - "context_efficiency": numeric score measuring answer length vs. context cost (typically 0–1).
        """
        query = criterion["query"]
        query_id = criterion["query_id"]

        logger.info(f"Running query: {query}")
        # Run agent research
        generated_answer = self.agent.research(query)

        # Get internal state for evaluation
        retrieved_docs = self.agent.get_retrieved_documents()
        context_used = self.agent.rag.get_context_for_synthesis(query)

        # Compute metrics
        results = {
            "query_id": query_id,
            "query": query,
            "generated_answer": generated_answer,
            # Metric 1: Pass@1 Accuracy
            "pass_at_1": self.metrics.pass_at_1_accuracy(
                generated_answer=generated_answer,
                reference_answer=reference["reference_answer"],
                key_facts=reference["key_facts"],
            ),
            # Metric 2: Evidence Quality
            "evidence_quality": self.metrics.evidence_quality_score(
                retrieved_docs=retrieved_docs,
                required_sources=reference["required_sources"],
                min_evidence_count=reference["min_evidence_count"],
            ),
            # Metric 3: Subgoal Completion
            "subgoal_completion": self.metrics.subgoal_completion_rate(
                subgoals=criterion["subgoals"],
                rag_system=self.agent.rag,
                llm_client=self.agent.llm,
            ),
            # Metric 4: Hallucination Rate
            "hallucination": self.metrics.hallucination_rate(
                generated_answer=generated_answer,
                retrieved_docs=retrieved_docs,
                llm_client=self.agent.llm,
            ),
            # Metric 5: Context Efficiency
            "context_efficiency": self.metrics.context_efficiency(
                final_answer_length=len(generated_answer),
                total_context_length=len(context_used),
                answer_quality_score=self.metrics.pass_at_1_accuracy(
                    generated_answer,
                    reference["reference_answer"],
                    reference["key_facts"],
                )["score"],
            ),
        }

        return results

    def _calculate_overall_score(self, aggregate_scores: Dict) -> float:
        """
        Compute the final leaderboard-style score from aggregated per-query metric lists.
        
        Calculates a weighted combination of metrics using the leaderboard weights:
        pass_at_1 40%, evidence_quality 25%, subgoal_completion 20%, hallucination_rate 10% (inverted as 1 - mean), and context_efficiency 5% (mean divided by 10 then capped at 1). The result is scaled to a percentage in the range 0–100.
        
        Parameters:
            aggregate_scores (Dict): Mapping of metric names to lists of numeric per-query scores. Expected keys:
                - "pass_at_1": list of values in [0,1] indicating top-answer correctness.
                - "evidence_quality": list of quality scores (same scale as produced by metrics).
                - "subgoal_completion": list of completion rates in [0,1].
                - "hallucination_rate": list of rates in [0,1] (higher means more hallucination; this is inverted).
                - "context_efficiency": list of efficiency values (higher is better; averaged then divided by 10 and capped).
        
        Returns:
            float: Final aggregated leaderboard score as a percentage (0.0 to 100.0).
        """
        weights = {
            "pass_at_1": 0.40,
            "evidence_quality": 0.25,
            "subgoal_completion": 0.20,
            "hallucination_rate": 0.10,  # Inverted
            "context_efficiency": 0.05,
        }

        score = 0.0
        score += np.mean(aggregate_scores["pass_at_1"]) * weights["pass_at_1"]
        score += (
            np.mean(aggregate_scores["evidence_quality"]) * weights["evidence_quality"]
        )
        score += (
            np.mean(aggregate_scores["subgoal_completion"])
            * weights["subgoal_completion"]
        )
        score += (1 - np.mean(aggregate_scores["hallucination_rate"])) * weights[
            "hallucination_rate"
        ]
        score += (
            min(np.mean(aggregate_scores["context_efficiency"]) / 10, 1.0)
            * weights["context_efficiency"]
        )

        return score * 100  # Convert to percentage

    def _print_summary(self, scores: Dict):
        """
        Display a formatted textual summary of evaluation scores.
        
        Parameters:
            scores (Dict): Mapping containing final evaluation metrics with the following keys:
                - 'overall_score' (float): Aggregated overall leaderboard score (percentage).
                - 'pass_at_1_accuracy' (float): Pass@1 accuracy as a percentage.
                - 'evidence_quality' (float): Evidence quality score as a percentage.
                - 'subgoal_completion' (float): Subgoal completion score as a percentage.
                - 'hallucination_rate' (float): Hallucination rate as a percentage.
                - 'context_efficiency' (float): Context efficiency score (unitless or ratio).
                - 'num_queries_evaluated' (int): Number of queries that were evaluated.
        """
        print("\n" + "=" * 60)
        print("DEEPRESEARCH-BENCH EVALUATION RESULTS")
        print("=" * 60)
        print(f"Overall Score: {scores['overall_score']:.2f}%")
        print("\nDetailed Metrics:")
        print(f"  Pass@1 Accuracy:      {scores['pass_at_1_accuracy']:.2f}%")
        print(f"  Evidence Quality:     {scores['evidence_quality']:.2f}%")
        print(f"  Subgoal Completion:   {scores['subgoal_completion']:.2f}%")
        print(f"  Hallucination Rate:   {scores['hallucination_rate']:.2f}%")
        print(f"  Context Efficiency:   {scores['context_efficiency']:.2f}")
        print(f"\nQueries Evaluated: {scores['num_queries_evaluated']}")
        print("=" * 60)
