import json
import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Dict, List

import numpy as np


class DeepResearchMetrics:
    """Implementation of DeepResearch-Bench evaluation metrics.
    Based on SOTA frameworks: RhinoInsight, FlowSearch, TTD-DR
    """

    @staticmethod
    def pass_at_1_accuracy(
        generated_answer: str,
        reference_answer: str,
        key_facts: List[Dict],
        threshold: float = 0.7,
    ) -> Dict:
        """
        Evaluate whether a generated answer passes on the first attempt by combining coverage of required key facts and semantic similarity to a reference answer.
        
        Parameters:
            generated_answer (str): The model-generated answer to evaluate.
            reference_answer (str): The reference or ground-truth answer used for semantic comparison.
            key_facts (List[Dict]): List of required facts where each dict should contain a "fact" string (and may include a "source"). Coverage is measured against these facts.
            threshold (float): Score threshold in [0, 1] above which the answer is considered to have passed. Default is 0.7.
        
        Returns:
            dict: A summary of the evaluation containing:
                - "passed" (bool): `true` if combined score >= threshold, `false` otherwise.
                - "score" (float): Combined pass score (weighted sum of fact coverage and similarity).
                - "fact_coverage" (float): Proportion of key facts found in the generated answer.
                - "similarity" (float): Semantic similarity score between reference and generated answers.
                - "covered_facts" (List[str]): List of key fact strings detected in the generated answer.
                - "total_facts" (int): Total number of key facts provided.
        """
        # Extract facts from generated answer
        generated_facts = DeepResearchMetrics._extract_facts(generated_answer)

        # Check key fact coverage
        fact_coverage = 0
        covered_facts = []
        for kf in key_facts:
            # key_facts is list of dicts {"fact": "...", "source": "..."}
            fact_text = kf.get("fact", "")
            if DeepResearchMetrics._fact_mentioned(fact_text, generated_answer):
                fact_coverage += 1
                covered_facts.append(fact_text)

        fact_coverage_ratio = fact_coverage / len(key_facts) if key_facts else 0

        # Semantic similarity (simple approach)
        similarity = SequenceMatcher(
            None, reference_answer.lower(), generated_answer.lower()
        ).ratio()

        # Combined score
        pass_score = (fact_coverage_ratio * 0.7) + (similarity * 0.3)
        passed = pass_score >= threshold

        return {
            "passed": passed,
            "score": pass_score,
            "fact_coverage": fact_coverage_ratio,
            "similarity": similarity,
            "covered_facts": covered_facts,
            "total_facts": len(key_facts),
        }

    @staticmethod
    def evidence_quality_score(
        retrieved_docs: List[Dict], required_sources: List[str], min_evidence_count: int
    ) -> Dict:
        """
        Assess the quality and diversity of retrieved evidence against a set of required sources.
        
        Computes a combined quality score from three components: proportion of required sources covered by the retrieved documents, sufficiency of the retrieved document count relative to min_evidence_count, and domain diversity of the retrieved documents.
        
        Parameters:
            retrieved_docs (List[Dict]): Retrieved documents, each expected to contain a "url" key and optional other metadata.
            required_sources (List[str]): Domains or source identifiers that should be present among retrieved documents.
            min_evidence_count (int): Minimum desirable number of retrieved documents used to scale the evidence count component.
        
        Returns:
            Dict: A dictionary with the following keys:
                quality_score (float): Combined quality score (0.0–1.0) derived from source coverage, evidence count sufficiency, and diversity.
                source_coverage (float): Fraction of required_sources that were found among retrieved documents (0.0–1.0).
                covered_sources (List[str]): List of required sources present in the retrieved documents.
                required_sources (List[str]): The input required_sources list (returned for convenience).
                evidence_count (int): Number of retrieved documents.
                min_required (int): The input min_evidence_count value.
                diversity_score (float): Shannon-entropy-based diversity score computed over retrieved document domains.
        """
        # Extract domains from retrieved docs
        retrieved_domains = set()
        for doc in retrieved_docs:
            domain = DeepResearchMetrics._extract_domain(doc.get("url", ""))
            if domain:
                retrieved_domains.add(domain)

        # Source coverage
        required_set = set(required_sources)
        covered_sources = retrieved_domains.intersection(required_set)
        source_coverage = (
            len(covered_sources) / len(required_set) if required_set else 0
        )

        # Evidence count
        evidence_count_score = (
            min(len(retrieved_docs) / min_evidence_count, 1.0)
            if min_evidence_count > 0
            else 1.0
        )

        # Source diversity (Shannon entropy)
        domain_counts = Counter(
            [
                DeepResearchMetrics._extract_domain(doc.get("url", ""))
                for doc in retrieved_docs
            ]
        )
        diversity = DeepResearchMetrics._shannon_entropy(list(domain_counts.values()))

        # Combined score
        quality_score = (
            source_coverage * 0.5 + evidence_count_score * 0.3 + diversity * 0.2
        )

        return {
            "quality_score": quality_score,
            "source_coverage": source_coverage,
            "covered_sources": list(covered_sources),
            "required_sources": required_sources,
            "evidence_count": len(retrieved_docs),
            "min_required": min_evidence_count,
            "diversity_score": diversity,
        }

    @staticmethod
    def subgoal_completion_rate(
        subgoals: List[str], rag_system, llm_client, confidence_threshold: float = 0.7
    ) -> Dict:
        """
        Assess which subgoals were verified and compute the overall completion rate.
        
        Parameters:
            subgoals (List[str]): Ordered list of subgoal descriptions to verify.
            confidence_threshold (float): Minimum confidence required from the verification step to consider a subgoal verified.
        
        Returns:
            dict: {
                "completion_rate": float,       # fraction of subgoals marked verified (0.0–1.0)
                "completed_count": int,         # number of subgoals verified
                "total_subgoals": int,          # total number of subgoals provided
                "subgoal_details": List[dict],  # per-subgoal records with keys:
                                               #   "subgoal" (str): original subgoal text,
                                               #   "verified" (bool): whether verification succeeded,
                                               #   "confidence" (float): reported verification confidence
            }
        """
        completed = 0
        subgoal_results = []

        for i, subgoal in enumerate(subgoals):
            verification = rag_system.verify_subgoal_coverage(
                subgoal=subgoal,
                subgoal_id=f"sg_{i + 1}",  # Assuming IDs match generation
                llm_client=llm_client,
                confidence_threshold=confidence_threshold,
            )

            # The mocked verification returns a dict
            if verification.get("verified", False):
                completed += 1

            subgoal_results.append(
                {
                    "subgoal": subgoal,
                    "verified": verification.get("verified", False),
                    "confidence": verification.get("confidence", 0.0),
                }
            )

        completion_rate = completed / len(subgoals) if subgoals else 0

        return {
            "completion_rate": completion_rate,
            "completed_count": completed,
            "total_subgoals": len(subgoals),
            "subgoal_details": subgoal_results,
        }

    @staticmethod
    def hallucination_rate(
        generated_answer: str, retrieved_docs: List[Dict], llm_client
    ) -> Dict:
        """
        Identify claims in a generated answer that are not supported by provided evidence.
        
        Attempts to extract factual claims from `generated_answer` using `llm_client`; if extraction fails it falls back to splitting the answer into sentences. Each claim is then checked against the concatenated contents of `retrieved_docs` via `llm_client`; verification failures are treated conservatively as unsupported.
        
        Parameters:
            generated_answer (str): The model-generated answer to inspect for factual claims.
            retrieved_docs (List[Dict]): Retrieved documents; each dict may contain a "content" field used as evidence.
            llm_client: A callable or client object used to (1) extract claims and (2) verify claims against evidence. May be an object exposing `invoke` or `generate`, or a plain callable.
        
        Returns:
            dict: {
                "hallucination_rate": float,            # fraction of claims marked unsupported (0.0–1.0)
                "hallucinated_claims": List[str],       # claims judged unsupported
                "supported_claims": List[str],          # claims judged supported
                "total_claims": int                     # number of claims evaluated
            }
        """
        # Extract claims using LLM
        claims_prompt = f"""
Extract factual claims from this answer. Return as JSON list of strings.

Answer: {generated_answer}

Format: {{"claims": ["claim1", "claim2", ...]}}
"""

        try:
            if hasattr(llm_client, "invoke"):
                response = llm_client.invoke(claims_prompt)
                content = (
                    response.content if hasattr(response, "content") else str(response)
                )
            elif hasattr(llm_client, "generate"):
                content = llm_client.generate(claims_prompt)
            else:
                content = str(llm_client(claims_prompt))

            content = content.replace("```json", "").replace("```", "").strip()
            claims = json.loads(content)["claims"]
        except Exception as e:
            logger.warning(f"Failed to extract claims via LLM; falling back to sentence split: {e}")
            # Fallback: simple sentence splitting
            claims = [
                s.strip() for s in generated_answer.split(".") if len(s.strip()) > 10
            ]

        # Build evidence corpus
        evidence_corpus = "\n\n".join(
            [doc.get("content", "") for doc in retrieved_docs]
        )

        # Check each claim
        hallucinations = []
        supported_claims = []

        for claim in claims:
            verification_prompt = f"""
Is this claim supported by the evidence? Answer YES or NO.

Claim: {claim}

Evidence:
{evidence_corpus[:2000]}  # Limit for token budget

Answer:
"""

            try:
                if hasattr(llm_client, "invoke"):
                    response = llm_client.invoke(verification_prompt)
                    resp_text = (
                        response.content
                        if hasattr(response, "content")
                        else str(response)
                    )
                elif hasattr(llm_client, "generate"):
                    resp_text = llm_client.generate(verification_prompt)
                else:
                    resp_text = str(llm_client(verification_prompt))

                if "NO" in resp_text.upper():
                    hallucinations.append(claim)
                else:
                    supported_claims.append(claim)
            except Exception as e:
                logger.warning(f"Claim verification failed; treating as unsupported: {e}")
                # Conservative: assume unsupported if verification fails
                hallucinations.append(claim)

        hallucination_rate = len(hallucinations) / len(claims) if claims else 0

        return {
            "hallucination_rate": hallucination_rate,
            "hallucinated_claims": hallucinations,
            "supported_claims": supported_claims,
            "total_claims": len(claims),
        }

    @staticmethod
    def context_efficiency(
        final_answer_length: int, total_context_length: int, answer_quality_score: float
    ) -> Dict:
        """
        Estimate how efficiently a final answer uses provided context by relating answer quality to approximate context token usage.
        
        Parameters:
            final_answer_length (int): Length of the final answer in characters (used to approximate tokens).
            total_context_length (int): Length of the available context in characters (used to approximate tokens).
            answer_quality_score (float): Scalar quality score for the final answer.
        
        Returns:
            dict: {
                "efficiency_score" (float): Quality per 1000 context tokens (higher is better).
                "answer_tokens" (float): Estimated tokens in the answer (characters / 4).
                "context_tokens" (float): Estimated tokens in the context (characters / 4).
                "context_usage_ratio" (float): Ratio of answer tokens to context tokens.
                "quality_score" (float): The input answer_quality_score.
            }
        """
        # Approximate token counts (4 chars ≈ 1 token)
        answer_tokens = final_answer_length / 4
        context_tokens = total_context_length / 4

        # Efficiency ratio
        if context_tokens > 0:
            efficiency = (answer_quality_score / context_tokens) * 1000
        else:
            efficiency = 0

        # Context usage ratio
        context_usage = answer_tokens / context_tokens if context_tokens > 0 else 0

        return {
            "efficiency_score": efficiency,
            "answer_tokens": answer_tokens,
            "context_tokens": context_tokens,
            "context_usage_ratio": context_usage,
            "quality_score": answer_quality_score,
        }

    # Helper methods

    @staticmethod
    def _extract_facts(text: str) -> List[str]:
        """
        Identify and return fact-like sentences from the input text.
        
        Uses simple heuristics to select declarative sentences that are likely factual (for example, longer sentences containing common copular/auxiliary verbs). The original sentence order is preserved.
        
        Parameters:
            text (str): Input text to analyze.
        
        Returns:
            List[str]: Extracted sentences that resemble factual statements; an empty list if none are found.
        """
        sentences = re.split(r"[.!?]+", text)
        facts = []
        for sent in sentences:
            sent = sent.strip()
            # Heuristic: facts are declarative sentences with verbs
            if len(sent) > 20 and any(
                word in sent.lower()
                for word in ["is", "are", "was", "were", "has", "have"]
            ):
                facts.append(sent)
        return facts

    @staticmethod
    def _fact_mentioned(fact: str, text: str) -> bool:
        """
        Determine whether a candidate fact is mentioned in a text by measuring token overlap.
        
        Returns:
            `True` if more than 60% of the words in `fact` appear in `text`, `False` otherwise.
            Returns `False` when `fact` is empty.
        """
        fact_words = set(fact.lower().split())
        text_words = set(text.lower().split())
        if not fact_words:
            return False
        overlap = len(fact_words.intersection(text_words))
        return overlap / len(fact_words) > 0.6

    @staticmethod
    def _extract_domain(url: str) -> str:
        """
        Extract the domain hostname from a URL string.
        
        Parameters:
            url (str): The URL to parse; may include scheme (http/https), "www." prefix, and path.
        
        Returns:
            str: The domain portion of the URL (e.g., "example.com"), or an empty string if no domain can be found.
        """
        match = re.search(r"(?:https?://)?(?:www\.)?([^/]+)", url)
        return match.group(1) if match else ""

    @staticmethod
    def _shannon_entropy(counts: List[int]) -> float:
        """Calculate Shannon entropy for diversity measurement"""
        if not counts or sum(counts) == 0:
            return 0.0
        total = sum(counts)
        probs = [c / total for c in counts if c > 0]
        return -sum(p * np.log2(p) for p in probs)
