from typing import List
from pydantic import BaseModel, Field
from agent.mcp_config import McpConnectionManager

class SearchQueryList(BaseModel):
    query: List[str] = Field(
        description="A list of search queries to be used for web research."
    )
    rationale: str = Field(
        description="A brief explanation of why these queries are relevant to the research topic."
    )


class Reflection(BaseModel):
    is_sufficient: bool = Field(
        description="Whether the provided summaries are sufficient to answer the user's question."
    )
    knowledge_gap: str = Field(
        description="A description of what information is missing or needs clarification."
    )
    follow_up_queries: List[str] = Field(
        description="A list of follow-up queries to address the knowledge gap."
    )

def get_mcp_tools() -> List:
    """
    Return MCP persistence tools for thread plan operations.
    
    Returns:
        tools (List): A list of MCP persistence tool callables (e.g., `load_thread_plan`, `save_thread_plan`) obtained from the MCP connection manager.
    """
    manager = McpConnectionManager()
    # In a sync context, we might need to be careful with async tools,
    # but LangGraph handles async tools fine.
    return manager.get_persistence_tools()