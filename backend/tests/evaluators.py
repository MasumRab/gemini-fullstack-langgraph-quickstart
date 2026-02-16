"""Evaluators for Research Agent Benchmarking.

This module defines Pydantic models and evaluation functions for 
structured grading of agent outputs using a Judge LLM (Gemini 2.5 Pro).
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from agent.models import GEMINI_PRO
import os

# Initialize Judge Model
# We use Gemini 2.5 Pro for high-quality evaluation
judge_model = ChatGoogleGenerativeAI(
    model=GEMINI_PRO,
    temperature=0,
    api_key=os.getenv("GEMINI_API_KEY")
)

class QualityScore(BaseModel):
    """Overall quality and utility score."""
    score: int = Field(..., description="Numerical score from 1 to 5.")
    reasoning: str = Field(..., description="Step-by-step justification for the score.")

class GroundednessScore(BaseModel):
    """Verification of factual claims against provided sources."""
    claims_verified: int = Field(..., description="Number of claims supported by citations.")
    total_claims: int = Field(..., description="Total number of major claims identified.")
    hallucinations: List[str] = Field(default_factory=list, description="List of claims that are not supported.")
    reasoning: str

def eval_quality(request: str, report: str) -> Dict[str, Any]:
    """
    Evaluates the overall quality of a research report.
    
    Args:
        request: The original user research request.
        report: The final generated report.
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert research auditor. Evaluate the report for depth, clarity, and adherence to the user's request. Rate from 1 to 5."),
        ("user", f"User Request: {request}\n\nFinal Report:\n{report}")
    ])
    
    # Use with_structured_output for reliable scoring (available in recent LangChain Google GenAI)
    try:
        grader = judge_model.with_structured_output(QualityScore)
        result = grader.invoke(prompt.format_messages())
        
        return {
            "key": "quality_score",
            "score": result.score / 5.0, # Normalize to 0-1
            "metadata": {"reasoning": result.reasoning}
        }
    except Exception as e:
        return {"key": "quality_score", "score": 0, "error": str(e)}

def eval_groundedness(report: str, sources: List[str]) -> Dict[str, Any]:
    """
    Evaluates how well the report is grounded in the provided sources.
    """
    # Simplified placeholder for groundedness logic
    # In a real scenario, this would involve extracting claims and checking them against summaries
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a fact-checker. Compare the report against the research findings and identify if citations are accurate and claims are supported."),
        ("user", f"Findings:\n{' '.join(sources)}\n\nReport:\n{report}")
    ])
    
    try:
        grader = judge_model.with_structured_output(QualityScore) # Reusing QualityScore schema for simplicity
        result = grader.invoke(prompt.format_messages())
        return {
            "key": "groundedness_score",
            "score": result.score / 5.0,
            "metadata": {"reasoning": result.reasoning}
        }
    except Exception as e:
        return {"key": "groundedness_score", "score": 0, "error": str(e)}
