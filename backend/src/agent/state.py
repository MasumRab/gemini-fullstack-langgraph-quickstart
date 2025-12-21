from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, TypedDict

from langgraph.graph import add_messages
from typing_extensions import Annotated


import operator


# TODO(priority=High, complexity=Low): [SOTA Deep Research] Define 'Evidence' object/TypedDict for ManuSearch (Claim, Source, Context).
# See docs/tasks/04_SOTA_DEEP_RESEARCH_TASKS.md
# Subtask: Define fields: claim (str), source_url (str), context_snippet (str).

class Todo(TypedDict, total=False):
    """
    Represents a single unit of work in the plan.
    Use total=False to allow for partial updates and backward compatibility.
    """
    id: str
    title: str
    description: str | None
    done: bool
    status: str | None  # pending/done/in_progress
    result: str | None


class Artifact(TypedDict):
    id: str
    content: str
    type: str  # "markdown", "code", "html", "json"
    title: str
    version: int


class ScopingState(TypedDict, total=False):
    """
    Scoping fields used during the agent's initial question scoping phase.
    See docs/tasks/04_SOTA_DEEP_RESEARCH_TASKS.md
    """
    query: str
    clarifications_needed: List[str]
    user_answers: List[str]


class Subsection(TypedDict):
    title: str
    description: str | None  # Optional description of what to cover


class Section(TypedDict):
    title: str
    subsections: List[Subsection]


class Outline(TypedDict):
    title: str  # Overall title of the report/outline
    sections: List[Section]


class OverallState(ScopingState, TypedDict, total=False):
    """
    Overall agent state. Extends ScopingState and adds plan and other fields.
    Inheritance from ScopingState ensures scoping fields are available.
    """
    messages: Annotated[list, add_messages]
    search_query: Annotated[list, operator.add]
    web_research_result: Annotated[list, operator.add]
    validated_web_research_result: Annotated[list, operator.add]
    validation_notes: Annotated[list, operator.add]
    sources_gathered: Annotated[list, operator.add]

    # Planning & Scoping
    scoping_status: str | None  # "pending", "active", "complete"
    clarification_questions: List[str] | None
    clarification_answers: Annotated[list, operator.add] # Stores user replies

    plan: List[Todo]
    planning_steps: List[dict] | None
    planning_status: str | None
    planning_feedback: Annotated[list, operator.add]

    outline: Outline | None

    # TODO(priority=High, complexity=Low): [SOTA Deep Research] Add 'evidence_bank' (List[Evidence]) for ManuSearch.
    # Subtask: Add `evidence_bank: Annotated[list, operator.add]` to OverallState.
    initial_search_query_count: int
    max_research_loops: int
    research_loop_count: int
    reasoning_model: str
    todo_list: List[dict] | None  # Deprecated: Migration to 'plan' in progress. See docs/tasks/02_OPEN_SWE_TASKS.md
    artifacts: Dict[str, Artifact] | None


class ReflectionState(TypedDict):
    is_sufficient: bool
    knowledge_gap: str
    follow_up_queries: Annotated[list, operator.add]
    research_loop_count: int
    number_of_ran_queries: int


class Query(TypedDict):
    query: str
    rationale: str


class QueryGenerationState(TypedDict):
    search_query: list[Query]


class WebSearchState(TypedDict):
    search_query: str
    id: str


def validate_scoping(state: OverallState) -> bool:
    """
    Runtime validation helper to check if required scoping fields are present.
    Returns True if valid, False otherwise.
    """
    required_fields = ["query", "clarifications_needed", "user_answers"]
    return all(field in state for field in required_fields)


@dataclass(kw_only=True)
class SearchStateOutput:
    running_summary: str | None = field(default=None)  # Final report


def create_rag_resources(resource_uris: list[str]):
    """Placeholder factory for RAG resources until a concrete implementation exists.
    
    This is an intentional extension point. Users should override this function
    to convert resource URIs into Resource objects for their specific RAG backend.
    
    Example implementation:
        def create_rag_resources(resource_uris: list[str]) -> list[Resource]:
            return [Resource(uri=uri, metadata={}) for uri in resource_uris]
    
    Raises:
        NotImplementedError: Always raised - this must be implemented by the user.
    """
    raise NotImplementedError(
        "create_rag_resources is not implemented. Provide agent.state.create_rag_resources"
        " to convert resource URIs into Resource objects consumed by rag_nodes."
    )
