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
        threshold: float = 0.7
    ) -> Dict:
        """Measure if the generated answer is correct on first attempt.
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
            None,
            reference_answer.lower(),
            generated_answer.lower()
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
            "total_facts": len(key_facts)
        }

    @staticmethod
    def evidence_quality_score(
        retrieved_docs: List[Dict],
        required_sources: List[str],
        min_evidence_count: int
    ) -> Dict:
        """Evaluate quality of retrieved evidence.
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
        source_coverage = len(covered_sources) / len(required_set) if required_set else 0

        # Evidence count
        evidence_count_score = min(len(retrieved_docs) / min_evidence_count, 1.0) if min_evidence_count > 0 else 1.0

        # Source diversity (Shannon entropy)
        domain_counts = Counter([
            DeepResearchMetrics._extract_domain(doc.get("url", ""))
            for doc in retrieved_docs
        ])
        diversity = DeepResearchMetrics._shannon_entropy(list(domain_counts.values()))

        # Combined score
        quality_score = (
            source_coverage * 0.5 +
            evidence_count_score * 0.3 +
            diversity * 0.2
        )

        return {
            "quality_score": quality_score,
            "source_coverage": source_coverage,
            "covered_sources": list(covered_sources),
            "required_sources": required_sources,
            "evidence_count": len(retrieved_docs),
            "min_required": min_evidence_count,
            "diversity_score": diversity
        }

    @staticmethod
    def subgoal_completion_rate(
        subgoals: List[str],
        rag_system,
        llm_client,
        confidence_threshold: float = 0.7
    ) -> Dict:
        """Measure how well each subgoal was addressed.
        """
        completed = 0
        subgoal_results = []

        for i, subgoal in enumerate(subgoals):
            verification = rag_system.verify_subgoal_coverage(
                subgoal=subgoal,
                subgoal_id=f"sg_{i+1}", # Assuming IDs match generation
                llm_client=llm_client,
                confidence_threshold=confidence_threshold
            )

            # The mocked verification returns a dict
            if verification.get("verified", False):
                completed += 1

            subgoal_results.append({
                "subgoal": subgoal,
                "verified": verification.get("verified", False),
                "confidence": verification.get("confidence", 0.0)
            })

        completion_rate = completed / len(subgoals) if subgoals else 0

        return {
            "completion_rate": completion_rate,
            "completed_count": completed,
            "total_subgoals": len(subgoals),
            "subgoal_details": subgoal_results
        }

    @staticmethod
    def hallucination_rate(
        generated_answer: str,
        retrieved_docs: List[Dict],
        llm_client
    ) -> Dict:
        """Detect factual claims not supported by evidence.
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
                 content = response.content if hasattr(response, "content") else str(response)
            elif hasattr(llm_client, "generate"):
                content = llm_client.generate(claims_prompt)
            else:
                 content = str(llm_client(claims_prompt))

            content = content.replace("```json", "").replace("```", "").strip()
            claims = json.loads(content)["claims"]
        except Exception:
            # Fallback: simple sentence splitting
            claims = [s.strip() for s in generated_answer.split('.') if len(s.strip()) > 10]

        # Build evidence corpus
        evidence_corpus = "\n\n".join([doc.get("content", "") for doc in retrieved_docs])

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
                     resp_text = response.content if hasattr(response, "content") else str(response)
                elif hasattr(llm_client, "generate"):
                    resp_text = llm_client.generate(verification_prompt)
                else:
                    resp_text = str(llm_client(verification_prompt))

                if "NO" in resp_text.upper():
                    hallucinations.append(claim)
                else:
                    supported_claims.append(claim)
            except Exception:
                # Conservative: assume unsupported if verification fails
                hallucinations.append(claim)

        hallucination_rate = len(hallucinations) / len(claims) if claims else 0

        return {
            "hallucination_rate": hallucination_rate,
            "hallucinated_claims": hallucinations,
            "supported_claims": supported_claims,
            "total_claims": len(claims)
        }

    @staticmethod
    def context_efficiency(
        final_answer_length: int,
        total_context_length: int,
        answer_quality_score: float
    ) -> Dict:
        """Measure token efficiency: quality per unit of context used.
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
            "quality_score": answer_quality_score
        }

    # Helper methods

    @staticmethod
    def _extract_facts(text: str) -> List[str]:
        """Extract fact-like sentences from text"""
        sentences = re.split(r'[.!?]+', text)
        facts = []
        for sent in sentences:
            sent = sent.strip()
            # Heuristic: facts are declarative sentences with verbs
            if len(sent) > 20 and any(word in sent.lower() for word in ['is', 'are', 'was', 'were', 'has', 'have']):
                facts.append(sent)
        return facts

    @staticmethod
    def _fact_mentioned(fact: str, text: str) -> bool:
        """Check if fact is mentioned in text (fuzzy match)"""
        fact_words = set(fact.lower().split())
        text_words = set(text.lower().split())
        if not fact_words: return False
        overlap = len(fact_words.intersection(text_words))
        return overlap / len(fact_words) > 0.6

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL"""
        match = re.search(r'(?:https?://)?(?:www\.)?([^/]+)', url)
        return match.group(1) if match else ""

    @staticmethod
    def _shannon_entropy(counts: List[int]) -> float:
        """Calculate Shannon entropy for diversity measurement"""
        if not counts or sum(counts) == 0:
            return 0.0
        total = sum(counts)
        probs = [c / total for c in counts if c > 0]
        return -sum(p * np.log2(p) for p in probs)
