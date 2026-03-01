import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from agent.llm_client import call_llm_robust, GemmaAdapter

# Placeholder imports for search and RAG - integrate with existing modules
try:
    from langchain_community.tools.tavily_search import TavilySearchResults
except ImportError:
    TavilySearchResults = None

logger = logging.getLogger(__name__)

# System prompts inspired by ODR / ThinkDepthAI
RESEARCH_PLAN_PROMPT = """You are an expert research planner. Given a topic, create a plan with 2-4 specific, actionable search queries to gather comprehensive information.
Respond with ONLY a JSON list of strings."""

SYNTHESIS_PROMPT = """You are an expert synthesizer. Given a topic and a set of research notes, write a comprehensive, well-structured report.
Topic: {topic}
Notes:
{notes}
"""

class WebSearcher:
    """Wrapper for web search."""
    def __init__(self):
        """
        Initialize the web search wrapper and attempt to create a TavilySearchResults tool.
        
        Attempts to instantiate TavilySearchResults(max_results=3) and assigns it to `self.tool`. If the TavilySearchResults import is unavailable or initialization fails, `self.tool` is set to `None` and a warning is logged. Requires the TAVILY_API_KEY environment variable for successful initialization.
        """
        try:
            # Requires TAVILY_API_KEY environment variable
            self.tool = TavilySearchResults(max_results=3)
        except ImportError:
            self.tool = None
        except Exception as e:
            logger.warning(f"Failed to initialize TavilySearchResults: {e}")
            self.tool = None

    def search(self, query: str) -> List[Dict]:
        """
        Perform a web search for the given query and return collected results.
        
        Parameters:
        	query (str): The search query string.
        
        Returns:
        	List[Dict]: A list of result dictionaries, each typically containing keys like `'url'` and `'content'`. If the underlying search tool is not initialized, returns a single dummy result. If an error occurs during searching, returns an empty list.
        """
        if not self.tool:
            logger.warning("Search tool not initialized. Returning dummy results.")
            return [{"url": "dummy", "content": f"Dummy result for '{query}'"}]
        try:
            return self.tool.invoke({"query": query})
        except Exception as e:
            logger.error(f"Search failed for '{query}': {e}")
            return []

class DeepResearchAgent:
    """A minimal, standalone implementation of a deep research workflow."""

    def __init__(self, llm_client: Any):
        """
        Create a DeepResearchAgent with a provided LLM client, a WebSearcher instance, and a default recursion depth.
        
        Parameters:
            llm_client (Any): Language model client used to generate planning and synthesis responses.
        """
        self.llm = llm_client
        self.searcher = WebSearcher()
        self.max_depth = 2

    async def _plan_queries(self, topic: str) -> List[str]:
        """
        Create a short list of focused web search queries for a research topic.
        
        Attempts to produce a JSON list of 2–4 actionable search queries using the research planning prompt. If the LLM output cannot be parsed or an error occurs, returns a single-item list containing the original `topic`.
        
        Returns:
            List[str]: Search query strings; typically 2–4 actionable queries. Returns `[topic]` as a fallback if planning or parsing fails.
        """
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", RESEARCH_PLAN_PROMPT),
                ("user", topic)
            ])
            # For simplicity, using robust call
            formatted = prompt.format()
            response = call_llm_robust(self.llm, formatted)

            # Very basic JSON extraction
            # In production, use structured output parsing
            start = response.find('[')
            end = response.rfind(']') + 1
            if start != -1 and end != -1:
                return json.loads(response[start:end])
            return [topic] # Fallback
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            return [topic]

    async def _research_topic(self, topic: str, depth: int = 1) -> str:
        """
        Gather notes for a topic by planning search queries and collecting results from the web searcher.
        
        Parameters:
        	topic (str): The research subject or query to investigate.
        	depth (int): Current recursion depth; used to stop deeper research when it exceeds the agent's max_depth.
        
        Returns:
        	notes (str): Concatenated notes where each entry contains a source URL and its content. If the provided depth is greater than the agent's max_depth, returns the literal string "Max depth reached.".
        """
        logger.info(f"Researching at depth {depth}: {topic}")
        if depth > self.max_depth:
            return "Max depth reached."

        queries = await self._plan_queries(topic)
        notes = []

        # Parallel search
        for query in queries:
            results = self.searcher.search(query)
            for r in results:
                notes.append(f"Source: {r.get('url', 'unknown')}\n{r.get('content', '')}")

        joined_notes = "\n\n".join(notes)
        return joined_notes

    async def run(self, topic: str, config: Optional[RunnableConfig] = None) -> str:
        """
        Run the end-to-end deep research workflow for a given topic.
        
        Performs planning, web search note collection, and synthesis to produce a single comprehensive report.
        
        Parameters:
            topic (str): The research subject or query to investigate.
            config (Optional[RunnableConfig]): Optional runtime configuration that may influence LLM or workflow behavior.
        
        Returns:
            report (str): A synthesized, structured research report generated from the gathered notes.
        """
        logger.info(f"Starting deep research on: {topic}")

        # 1. Gather notes
        notes = await self._research_topic(topic, depth=1)

        # 2. Synthesize
        prompt = ChatPromptTemplate.from_messages([
             ("system", "You are a helpful research assistant."),
             ("user", SYNTHESIS_PROMPT)
        ])
        formatted = prompt.format(topic=topic, notes=notes)

        report = call_llm_robust(self.llm, formatted)
        return report

# Example usage function
async def main():
    # To run this, you need GEMINI_API_KEY and TAVILY_API_KEY
    """
    Demonstrates usage of DeepResearchAgent to run a sample deep-research workflow and print the synthesized report.
    
    Runs a simple example that instantiates a Google GenAI LLM, creates a DeepResearchAgent, performs research on the given sample topic, and prints the final synthesized report. Requires the environment variables GEMINI_API_KEY and TAVILY_API_KEY to be set for the LLM and web search tool to function.
    
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")

    agent = DeepResearchAgent(llm)
    report = await agent.run("What are the main findings in the 'Attention Is All You Need' paper?")
    print(report)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
