from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, TypedDict

from langgraph.graph import add_messages
from typing_extensions import Annotated


import operator


class OverallState(TypedDict):
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

    planning_steps: List[dict] | None
    planning_status: str | None
    planning_feedback: Annotated[list, operator.add]

    initial_search_query_count: int
    max_research_loops: int
    research_loop_count: int
    reasoning_model: str
    todo_list: List[dict] | None
    artifacts: dict | None


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


@dataclass(kw_only=True)
class SearchStateOutput:
    running_summary: str = field(default=None)  # Final report


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
