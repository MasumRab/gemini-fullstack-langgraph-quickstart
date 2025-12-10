from typing import List
from pydantic import BaseModel, Field


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

def get_tools_from_mcp(mcp_config=None):
    """
    Placeholder to load tools via langchain-mcp-adapters.
    In the future, this will connect to the MCP server defined in mcp_config.
    """
    # Example integration:
    # from langchain_mcp_adapters import MCPToolAdapter
    # return MCPToolAdapter.load_tools(mcp_config)
    return []
