import os
import sys
import time
from typing import Any, Dict, List

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from agent.configuration import Configuration
from agent.prompts import (
    answer_instructions,
    get_current_date,
    query_writer_instructions,
    reflection_instructions,
    web_searcher_instructions,
)
from agent.state import (
    OverallState,
    QueryGenerationState,
    ReflectionState,
    WebSearchState,
)
from agent.utils import get_research_topic

load_dotenv()


def check_api_keys() -> None:
    """Ensure at least one LLM key is configured before running the graph."""

    if not any(
        [
            os.getenv("DEEPSEEK_API_KEY"),
            os.getenv("ZHIPUAI_API_KEY"),
            os.getenv("QWEN_API_KEY"),
            os.getenv("OPENAI_API_KEY"),
            os.getenv("LLM_API_KEY"),
            os.getenv("GEMINI_API_KEY"),
        ]
    ):
        raise ValueError(
            "At least one LLM API key must be configured."
            " Provide DEEPSEEK_API_KEY, ZHIPUAI_API_KEY, QWEN_API_KEY, OpenAI API key,"
            " or LLM_API_KEY before invoking the multi-provider graph."
        )


check_api_keys()


try:
    from agent.llm_factory import LLMFactory  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency

    class LLMFactory:  # type: ignore
        """Fallback factory that surfaces a descriptive error when missing."""

        @staticmethod
        def create_llm(*_, **__):
            raise ImportError(
                "LLMFactory module not found. Provide agent.llm_factory with a"
                " create_llm(model_name, temperature, max_retries) helper to enable"
                " the multi-provider graph."
            )


try:
    from agent.web_search_tool import web_search_tool  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency

    class _PlaceholderWebSearchTool:  # type: ignore
        def search(self, *_args, **_kwargs):
            raise ImportError(
                "web_search_tool module not found. Supply agent.web_search_tool"
                " with search() and format_search_results() helpers."
            )

        def format_search_results(self, *_args, **_kwargs):
            return ""

    web_search_tool = _PlaceholderWebSearchTool()


try:
    from agent import rag_nodes  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency

    class rag_nodes:  # type: ignore
        @staticmethod
        def rag_retrieve(state: OverallState, _config: RunnableConfig) -> Dict[str, Any]:
            raise NotImplementedError(
                "rag_nodes.rag_retrieve missing. Provide implementation or remove"
                " rag functionality when using agent._graph."
            )

        @staticmethod
        def should_use_rag(state: OverallState) -> str:
            return "web_research"

        @staticmethod
        def rag_fallback_to_web(state: OverallState) -> str:
            return "web_research"


# Nodes

def generate_query(state: OverallState, config: RunnableConfig) -> Dict[str, Any]:
    """Generate search queries using the configured LLM provider."""

    configurable = Configuration.from_runnable_config(config)

    if state.get("initial_search_query_count") is None:
        state["initial_search_query_count"] = configurable.number_of_initial_queries

    llm = LLMFactory.create_llm(
        model_name=configurable.query_generator_model,
        temperature=1.0,
        max_retries=2,
    )

    current_date = get_current_date()
    messages = state.get("messages", [])
    research_topic = get_research_topic(messages) if messages else "General research topic"
    formatted_prompt = (
        query_writer_instructions.format(
            current_date=current_date,
            research_topic=research_topic,
            number_queries=state["initial_search_query_count"],
        )
        + "\n\nPlease provide search queries as a simple list, one per line."
    )

    result = llm.invoke(formatted_prompt)
    content = getattr(result, "content", str(result))

    print(f"DEBUG: generate_query LLM response: {content}")

    import json
    import re

    queries: List[str] = []
    try:
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        json_content = json_match.group(1) if json_match else content
        parsed_json = json.loads(json_content)
        if isinstance(parsed_json, dict) and "query" in parsed_json:
            query_list = parsed_json["query"]
            if isinstance(query_list, list):
                queries = [str(q).strip() for q in query_list if q]
            elif isinstance(query_list, str):
                queries = [query_list.strip()]
    except (json.JSONDecodeError, KeyError, AttributeError) as exc:
        print(f"DEBUG: JSON parsing failed: {exc}")
        for line in content.strip().split("\n"):
            line = line.strip().lstrip("0123456789.-• ")
            if line and not line.startswith(("#", "//", "{", "}")):
                queries.append(line)

    if not queries:
        queries = [research_topic]

    print(f"DEBUG: Parsed queries: {queries}")

    return {"search_query": queries[: state["initial_search_query_count"]]}


def web_research(state: OverallState, config: RunnableConfig) -> Dict[str, Any]:
    """Perform web research using the configured search tool and provider."""

    configurable = Configuration.from_runnable_config(config)

    current_query = state["search_query"]
    if isinstance(current_query, list) and current_query:
        query_text = current_query[-1] if isinstance(current_query[-1], str) else str(current_query[-1])
    else:
        query_text = str(current_query)

    print(f"DEBUG: web_research called with query: {query_text}")

    search_results = web_search_tool.search(query_text, max_results=5)
    formatted_results = web_search_tool.format_search_results(search_results)

    llm = LLMFactory.create_llm(
        model_name=configurable.query_generator_model,
        temperature=0,
        max_retries=2,
    )

    analysis_prompt = (
        web_searcher_instructions.format(
            current_date=get_current_date(),
            research_topic=state["search_query"],
        )
        + f"\n\nSearch Results:\n{formatted_results}\n\nPlease provide a comprehensive analysis."
    )

    analysis_result = llm.invoke(analysis_prompt)
    analysis_text = getattr(analysis_result, "content", str(analysis_result))

    sources_gathered = [
        {
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "snippet": result.get("snippet", ""),
        }
        for result in search_results or []
    ]

    return {
        "sources_gathered": sources_gathered,
        "search_query": state["search_query"],
        "web_research_result": [analysis_text],
    }


def reflection(state: OverallState, config: RunnableConfig) -> Dict[str, Any]:
    """Identify knowledge gaps and propose follow-up queries."""

    configurable = Configuration.from_runnable_config(config)
    state["research_loop_count"] = state.get("research_loop_count", 0) + 1
    reasoning_model = state.get("reasoning_model", configurable.reflection_model)

    current_date = get_current_date()
    web_research_result = state.get("web_research_result", [])
    summaries_text = "\n\n---\n\n".join(web_research_result) if web_research_result else "No research content available."

    messages = state.get("messages", [])
    research_topic = get_research_topic(messages) if messages else "General research topic"

    formatted_prompt = reflection_instructions.format(
        current_date=current_date,
        research_topic=research_topic,
        summaries=summaries_text,
    )

    llm = LLMFactory.create_llm(
        model_name=reasoning_model or configurable.reflection_model,
        temperature=1.0,
        max_retries=2,
    )

    result = llm.invoke(formatted_prompt)
    content = getattr(result, "content", str(result))

    import json
    import re

    is_sufficient = False
    knowledge_gap = ""
    follow_up_queries: List[str] = []
    try:
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        json_content = json_match.group(1) if json_match else content
        parsed_json = json.loads(json_content)
        is_sufficient = bool(parsed_json.get("is_sufficient", False))
        knowledge_gap = parsed_json.get("knowledge_gap", "")
        follow_up_raw = parsed_json.get("follow_up_queries", [])
        if isinstance(follow_up_raw, str):
            follow_up_queries = [follow_up_raw]
        elif isinstance(follow_up_raw, list):
            follow_up_queries = [str(item) for item in follow_up_raw if item]
    except (json.JSONDecodeError, KeyError, AttributeError) as exc:
        print(f"DEBUG: reflection JSON parsing failed: {exc}")
        for line in content.strip().split("\n"):
            line = line.strip()
            upper = line.upper()
            if upper.startswith("SUFFICIENT"):
                is_sufficient = "YES" in upper or "TRUE" in upper
            elif upper.startswith("KNOWLEDGE_GAP"):
                knowledge_gap = line.split(":", 1)[-1].strip()
            elif upper.startswith("FOLLOW_UP"):
                rest = line.split(":", 1)[-1]
                follow_up_queries = [seg.strip() for seg in rest.split(",") if seg.strip()]

    query_count = len(state.get("search_query", []) or [])

    return {
        "is_sufficient": is_sufficient,
        "knowledge_gap": knowledge_gap,
        "follow_up_queries": follow_up_queries,
        "research_loop_count": state["research_loop_count"],
        "number_of_ran_queries": query_count,
    }


def evaluate_research(state: ReflectionState, config: RunnableConfig) -> str:
    """Decide whether to continue researching or finalize the answer."""

    configurable = Configuration.from_runnable_config(config)
    max_research_loops = state.get("max_research_loops", configurable.max_research_loops)
    research_loop_count = state.get("research_loop_count", 0)

    if state.get("is_sufficient") or research_loop_count >= max_research_loops:
        return "finalize_answer"
    return "continue_research"


def continue_research(state: OverallState) -> Dict[str, Any]:
    """Route follow-up queries back into the research loop."""

    follow_up_queries = state.get("follow_up_queries", [])
    if not follow_up_queries:
        return {}

    next_query = follow_up_queries[0]
    return {
        "search_query": [next_query],
        "follow_up_queries": follow_up_queries[1:],
    }


def finalize_answer(state: OverallState, config: RunnableConfig) -> Dict[str, Any]:
    """Combine RAG documents and web research into the final answer."""

    configurable = Configuration.from_runnable_config(config)
    reasoning_model = state.get("reasoning_model") or configurable.answer_model

    all_summaries: List[str] = []

    rag_documents = state.get("rag_documents")
    if rag_documents:
        for idx, doc in enumerate(rag_documents):
            labeled_doc = f"=== KNOWLEDGE BASE SOURCE {idx + 1} ===\n{doc}\n=== END KNOWLEDGE BASE SOURCE {idx + 1} ==="
            all_summaries.append(labeled_doc)

    web_research_result = state.get("web_research_result")
    if web_research_result:
        for idx, result in enumerate(web_research_result):
            labeled_result = f"=== WEB RESEARCH SOURCE {idx + 1} ===\n{result}\n=== END WEB RESEARCH SOURCE {idx + 1} ==="
            all_summaries.append(labeled_result)

    summaries_text = "\n\n".join(all_summaries) if all_summaries else "No research content available."

    messages = state.get("messages", [])
    research_topic = get_research_topic(messages) if messages else "General research topic"

    formatted_prompt = answer_instructions.format(
        current_date=get_current_date(),
        research_topic=research_topic,
        summaries=summaries_text,
    )

    llm = LLMFactory.create_llm(
        model_name=reasoning_model or configurable.answer_model,
        temperature=0,
        max_retries=2,
    )

    result = llm.invoke(formatted_prompt)
    final_answer = getattr(result, "content", str(result))

    response_metadata = getattr(result, "response_metadata", {})
    finish_reason = response_metadata.get("finish_reason")
    while finish_reason == "length":
        continuation = llm.invoke("请继续上文接着写，\n 上文：" + final_answer)
        final_answer = final_answer + "\n" + getattr(continuation, "content", str(continuation))
        response_metadata = getattr(continuation, "response_metadata", {})
        finish_reason = response_metadata.get("finish_reason")
        time.sleep(2)

    return {
        "messages": [AIMessage(content=final_answer)],
    }


def build_graph():
    """Build the experimental multi-provider LangGraph workflow."""

    workflow = StateGraph(OverallState)

    workflow.add_node("generate_query", generate_query)
    workflow.add_node("web_research", web_research)
    workflow.add_node("reflection", reflection)
    workflow.add_node("continue_research", continue_research)
    workflow.add_node("finalize_answer", finalize_answer)
    workflow.add_node("rag_retrieve", rag_nodes.rag_retrieve)

    workflow.add_edge(START, "generate_query")

    workflow.add_conditional_edges(
        "generate_query",
        rag_nodes.should_use_rag,
        {
            "rag_retrieve": "rag_retrieve",
            "web_research": "web_research",
        },
    )

    workflow.add_conditional_edges(
        "rag_retrieve",
        rag_nodes.rag_fallback_to_web,
        {
            "web_research": "web_research",
            "reflection": "reflection",
        },
    )

    workflow.add_edge("web_research", "reflection")

    workflow.add_conditional_edges(
        "reflection",
        evaluate_research,
        {
            "finalize_answer": "finalize_answer",
            "continue_research": "continue_research",
        },
    )

    workflow.add_conditional_edges(
        "continue_research",
        rag_nodes.should_use_rag,
        {
            "rag_retrieve": "rag_retrieve",
            "web_research": "web_research",
        },
    )

    workflow.add_edge("finalize_answer", END)

    return workflow.compile()


research_graph = build_graph()
