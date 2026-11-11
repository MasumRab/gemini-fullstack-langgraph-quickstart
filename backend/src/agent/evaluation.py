"""Evaluators for Research Agent Benchmarking.

This module defines Pydantic models and evaluation functions for
structured grading of agent outputs using a Judge LLM (Gemini 2.5 Pro).
"""

import os
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from agent.models import GEMINI_PRO

# Module-level cache for the judge model instance
_judge_model_cache: ChatGoogleGenerativeAI | None = None


def _get_judge_model() -> ChatGoogleGenerativeAI:
    """Lazy getter for the judge model.

    Validates API key and constructs the judge model only when called,
    not at import time. This prevents breaking pytest collection when
    the API key is not set.

    Returns:
        ChatGoogleGenerativeAI: The judge model instance.

    Raises:
        ValueError: If GEMINI_API_KEY environment variable is not set.
    """
    global _judge_model_cache

    if _judge_model_cache is not None:
        return _judge_model_cache

    # Validate API key at runtime, not import time
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is required for evaluators"
        )

    # Initialize Judge Model
    # We use Gemini 2.5 Pro for high-quality evaluation
    _judge_model_cache = ChatGoogleGenerativeAI(
        model=GEMINI_PRO, temperature=0, api_key=gemini_api_key
    )

    return _judge_model_cache


class QualityScore(BaseModel):
    """Overall quality and utility score."""

    score: int = Field(..., ge=1, le=5, description="Numerical score from 1 to 5.")
    reasoning: str = Field(..., description="Step-by-step justification for the score.")


class GroundednessScore(BaseModel):
    """Verification of factual claims against provided sources."""

    claims_verified: int = Field(
        ..., description="Number of claims supported by citations."
    )
    total_claims: int = Field(
        ..., description="Total number of major claims identified."
    )
    hallucinations: list[str] = Field(
        default_factory=list, description="List of claims that are not supported."
    )
    reasoning: str


def eval_quality(request: str, report: str) -> dict[str, Any]:
    """Evaluates the overall quality of a research report.

    Args:
        request: The original user research request.
        report: The final generated report.
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert research auditor. Evaluate the report for depth, clarity, and adherence to the user's request. Rate from 1 to 5.",
            ),
            ("user", f"User Request: {request}\n\nFinal Report:\n{report}"),
        ]
    )

    # Use with_structured_output for reliable scoring (available in recent LangChain Google GenAI)
    try:
        grader = _get_judge_model().with_structured_output(QualityScore)
        result = grader.invoke(prompt.format_messages())

        return {
            "key": "quality_score",
            "score": result.score / 5.0,  # Normalize to 0-1
            "metadata": {"reasoning": result.reasoning},
        }
    except Exception as e:
        return {"key": "quality_score", "score": 0, "error": str(e)}


def eval_groundedness(report: str, sources: list[str]) -> dict[str, Any]:
    """Evaluates how well the report is grounded in the provided sources.

    The judge returns a ``GroundednessScore``: how many of the report's claims it could
    verify, how many it found in total, and the claims it could not support. The score is
    the verified fraction, clamped to ``[0, 1]``.
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a fact-checker. Compare the report against the research findings and identify if citations are accurate and claims are supported.",
            ),
            ("user", f"Findings:\n{' '.join(sources)}\n\nReport:\n{report}"),
        ]
    )

    try:
        grader = _get_judge_model().with_structured_output(GroundednessScore)
        result = grader.invoke(prompt.format_messages())
        metadata = {
            "reasoning": result.reasoning,
            "hallucinations": result.hallucinations,
            "claims_verified": result.claims_verified,
            "total_claims": result.total_claims,
        }
        if result.total_claims <= 0:
            # No checkable claim means the ratio is undefined; report zero rather than
            # dividing by zero, and say so, so a caller can tell it apart from "none verified".
            metadata["note"] = (
                "no checkable claims were identified; score is 0 by definition"
            )
            return {"key": "groundedness_score", "score": 0.0, "metadata": metadata}
        fraction = result.claims_verified / result.total_claims
        return {
            "key": "groundedness_score",
            "score": min(max(fraction, 0.0), 1.0),
            "metadata": metadata,
        }
    except Exception as e:
        return {"key": "groundedness_score", "score": 0, "error": str(e)}
