"""RAG integration nodes for the LangGraph agent."""

import logging
from typing import Any, Dict

from langchain_core.runnables import RunnableConfig

try:  # Local imports to avoid circular references when optional modules exist
    from agent.rag import (  # type: ignore
        Resource,  # noqa: F401  # exported for type checkers
        create_rag_tool,
        is_rag_enabled,
        rag_config,
    )
except ModuleNotFoundError:  # pragma: no cover - optional dependency

    class _MissingRAGConfig:  # type: ignore
        enabled = False
        enable_fallback = False
        max_documents = 3

    def create_rag_tool(_resources):  # type: ignore
        raise ImportError(
            "agent.rag module is required for rag_nodes. Provide create_rag_tool,"
            " Resource, is_rag_enabled, and rag_config implementations."
        )

    def is_rag_enabled() -> bool:  # type: ignore
        return False

    rag_config = _MissingRAGConfig()  # type: ignore

logger = logging.getLogger(__name__)


def _lazy_import_state_utils():
    """
    Lazily import and return state-related utilities to avoid circular imports.
    
    Returns:
        tuple: (OverallState, create_rag_resources, get_research_topic) —
        the OverallState class, a function to create RAG resources from state,
        and a function that extracts the research topic from messages.
    """
    from agent.state import OverallState, create_rag_resources  # type: ignore
    from agent.utils import get_research_topic  # type: ignore

    return OverallState, create_rag_resources, get_research_topic


def rag_retrieve(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """
    Retrieve relevant documents using configured RAG resources for the current research topic.
    
    Parameters:
        state (dict): Runtime state containing at least:
            - "messages": list of conversation messages used to derive the research topic.
            - "rag_resources" (optional): list of resource URIs to restrict retrieval.
        config (RunnableConfig): Execution configuration for the runnable (not used to determine return shape).
    
    Returns:
        dict: A dictionary with:
            - "rag_documents" (list[str]): Retrieved document texts; empty if none found or on error.
            - "rag_enabled" (bool): `True` if RAG functionality was available/enabled, `False` if RAG is disabled.
    """
    _, create_rag_resources, get_research_topic = _lazy_import_state_utils()

    logger.info("Starting RAG retrieval")

    if not is_rag_enabled():
        logger.info("RAG is not enabled, skipping retrieval")
        return {"rag_documents": [], "rag_enabled": False}

    messages = state.get("messages", [])
    research_topic = get_research_topic(messages)
    if not research_topic:
        logger.warning("No research topic found in messages")
        return {"rag_documents": [], "rag_enabled": True}

    resources = []
    resource_uris = state.get("rag_resources", [])
    if resource_uris:
        resources = create_rag_resources(resource_uris)
        logger.info("Using %s RAG resources", len(resources))
    else:
        logger.info("No specific RAG resources provided, using default search")

    try:
        rag_tool = create_rag_tool(resources)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to create RAG tool: %s", exc)
        return {"rag_documents": [], "rag_enabled": True}

    if not rag_tool:
        logger.error("RAG tool factory returned None")
        return {"rag_documents": [], "rag_enabled": True}

    try:
        logger.info("Performing RAG search for: %s", research_topic)
        result = rag_tool.invoke(
            {"query": research_topic, "max_results": rag_config.max_documents}
        )
    except Exception as exc:
        logger.error("Error during RAG retrieval: %s", exc)
        return {"rag_documents": [], "rag_enabled": True}

    if isinstance(result, str):
        if "No relevant information found" in result or "not configured" in result:
            logger.warning("RAG search returned no results: %s", result)
            return {"rag_documents": [], "rag_enabled": True}
        logger.info("RAG search completed successfully")
        return {"rag_documents": [result], "rag_enabled": True}

    logger.warning("Unexpected RAG tool result type: %s", type(result))
    return {"rag_documents": [], "rag_enabled": True}


def has_rag_resources(state: Dict[str, Any]) -> bool:
    """
    Determine whether state contains a non-empty 'rag_resources' list.
    
    Parameters:
        state (Dict[str, Any]): Execution state that may include the 'rag_resources' key.
    
    Returns:
        bool: `True` if 'rag_resources' exists in state and is non-empty, `False` otherwise.
    """
    return bool(state.get("rag_resources", []))


def should_use_rag(state: Dict[str, Any]) -> str:
    """
    Decides whether to use RAG retrieval or web research based on RAG availability and state.
    
    Parameters:
        state (dict): Agent state used to determine if RAG resources are present.
    
    Returns:
        'rag_retrieve' to invoke RAG retrieval, 'web_research' to invoke web search.
    """
    if not is_rag_enabled():
        logger.info("RAG is not enabled, routing to web research")
        return "web_research"

    if has_rag_resources(state):
        logger.info("RAG resources found, routing to RAG retrieval")
        return "rag_retrieve"

    if getattr(rag_config, "enabled", False):
        logger.info("RAG is enabled for general use, routing to RAG retrieval")
        return "rag_retrieve"

    logger.info("No RAG configuration found, routing to web research")
    return "web_research"


def rag_fallback_to_web(state: Dict[str, Any]) -> str:
    """
    Decide whether to route to a web search or to proceed to reflection after a RAG attempt.
    
    Parameters:
        state (dict): Overall agent state. Expected keys:
            - "rag_documents" (list): Documents returned by the RAG step.
            - "research_loop_count" (int): Number of prior research-loop iterations.
    
    Returns:
        str: The next routing target, either "web_research" to perform a web search or "reflection" to continue with reflection.
    """
    rag_documents = state.get("rag_documents", [])
    research_loop_count = state.get("research_loop_count", 0) or 0
    is_continue_research = research_loop_count > 0

    if is_continue_research:
        logger.info(
            "Continue research iteration – falling back to web search for coverage"
        )
        return "web_research"

    if getattr(rag_config, "enable_fallback", False):
        if rag_documents:
            logger.info(
                "RAG docs found, but fallback enabled – performing web search too"
            )
        else:
            logger.info("No RAG docs found, falling back to web research")
        return "web_research"

    if rag_documents:
        logger.info("RAG documents found, proceeding to reflection (fallback disabled)")
        return "reflection"

    logger.info("No RAG documents and fallback disabled, proceeding to reflection")
    return "reflection"


def continue_research_rag_to_web(_state: Dict[str, Any]) -> str:
    """
    Route continued RAG research iterations to a web search.
    
    Returns:
        str: The route name 'web_research'.
    """
    logger.info(
        "Continue research: performing web search after RAG for comprehensive coverage"
    )
    return "web_research"
