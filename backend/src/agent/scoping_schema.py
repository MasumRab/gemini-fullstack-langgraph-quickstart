from pydantic import BaseModel, Field
from typing import List, Optional

class ScopingAssessment(BaseModel):
    """
    Assessment of whether the user's query requires clarification.
    """
    is_ambiguous: bool = Field(
        description="True if the query is too vague to form a solid research plan."
    )
    clarifying_questions: List[str] = Field(
        description="List of 3-5 questions to ask the user if ambiguous. Empty if clear.",
        default_factory=list
    )
    reasoning: str = Field(
        description="Brief explanation of why clarification is needed or not."
    )
