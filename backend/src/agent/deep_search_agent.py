import json
import logging
from typing import Any, Dict, List

from agent.mcp_client import MCPToolUser
from agent.rag import DeepSearchRAG

# Mock/Simple interfaces for Planner, Searcher, Refiner to make it self-contained
# In a real app, these might come from `backend/src/agent/graph.py` or `nodes.py`
# but we need a clean class for the Notebooks.

logger = logging.getLogger(__name__)

class QueryPlanner:
    def __init__(self, llm):
        self.llm = llm

    def decompose(self, query: str) -> List[Any]:
        prompt = f"""Decompose the following research query into 3-5 distinct sub-questions (sub-goals) for a research agent.
        Query: {query}
        Return JSON list of objects: [{{"id": "sg_1", "query": "sub question 1"}}, ...]
        """
        try:
             # Adapt to llm_client interface
            if hasattr(self.llm, "invoke"):
                 response = self.llm.invoke(prompt)
                 content = response.content if hasattr(response, "content") else str(response)
            elif hasattr(self.llm, "generate"):
                content = self.llm.generate(prompt)
            else:
                content = str(self.llm(prompt))

            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            # Fallback
            return [{"id": "sg_1", "query": query}]

class WebSearcher:
    """Mock Web Searcher using DuckDuckGo or Tavily if available, else Mock"""
    def __init__(self):
        try:
            from langchain_community.tools import TavilySearchResults
            self.tool = TavilySearchResults(max_results=3)
        except ImportError:
            self.tool = None
        except Exception:
             self.tool = None

    def search(self, query: str) -> List[Dict]:
        if self.tool:
            try:
                results = self.tool.invoke({"query": query})
                # Normalize to list of dicts {content, url, score}
                normalized = []
                for r in results:
                    normalized.append({
                        "content": r.get("content", ""),
                        "url": r.get("url", ""),
                        "score": 0.8 # Dummy score
                    })
                return normalized
            except Exception as e:
                logger.warning(f"Search tool failed: {e}")

        # Fallback Mock
        return [
            {"content": f"Mock content about {query}. This is a simulated search result.", "url": "http://mock-source.com", "score": 0.5},
            {"content": f"More details on {query} found here.", "url": "http://wiki-mock.org", "score": 0.6}
        ]

class AnswerRefiner:
    def __init__(self, llm):
        self.llm = llm

    def synthesize(self, query: str, context: str) -> str:
        prompt = f"""Answer the following query based on the provided context.
        Query: {query}

        Context:
        {context}

        Answer:"""

        if hasattr(self.llm, "invoke"):
             response = self.llm.invoke(prompt)
             return response.content if hasattr(response, "content") else str(response)
        elif hasattr(self.llm, "generate"):
            return self.llm.generate(prompt)
        else:
            return str(self.llm(prompt))

class DeepSearchAgent:
    def __init__(self, llm_client, mcp_servers: List = None):
        self.llm = llm_client
        self.rag = DeepSearchRAG()
        self.planner = QueryPlanner(llm_client)
        self.searcher = WebSearcher()
        self.refiner = AnswerRefiner(llm_client)

        if mcp_servers:
            self.mcp = MCPToolUser(mcp_servers)
        else:
            self.mcp = None

    def research(self, query: str) -> str:
        logger.info(f"Starting research on: {query}")

        # 1. Plan
        subgoals_data = self.planner.decompose(query)
        # Convert dicts to objects for easier handling if needed, or just use dicts
        # Using simple objects
        class SubGoal:
            def __init__(self, id, query):
                self.id = id
                self.query = query

        subgoals = [SubGoal(sg["id"], sg["query"]) for sg in subgoals_data]

        # 2. Research each subgoal
        for sg in subgoals:
            logger.info(f"Processing subgoal: {sg.query}")
            docs = self.searcher.search(sg.query)

            # 3. Ingest into RAG
            self.rag.ingest_research_results(
                documents=docs,
                subgoal_id=sg.id,
                metadata={"subgoal": sg.query}
            )

            # 4. Audit evidence
            audit_result = self.rag.audit_and_prune(sg.id)
            logger.info(f"Audit result for {sg.id}: {audit_result}")

            # 5. Verify coverage
            verification = self.rag.verify_subgoal_coverage(
                subgoal=sg.query,
                subgoal_id=sg.id,
                llm_client=self.llm
            )
            logger.info(f"Verification for {sg.id}: {verification.get('verified')}")

            if not verification.get("verified"):
                # Simple Refinement: Try one more search (mocked here)
                # In real app, we would expand query
                logger.info("Subgoal not verified, retrying...")
                more_docs = self.searcher.search(sg.query + " detailed analysis")
                self.rag.ingest_research_results(more_docs, sg.id)

        # 6. Synthesize final answer
        context = self.rag.get_context_for_synthesis(
            query=query,
            subgoal_ids=[sg.id for sg in subgoals]
        )

        final_answer = self.refiner.synthesize(query, context)
        return final_answer

    def get_retrieved_documents(self) -> List[Dict]:
        """Helper for evaluation to see what's in RAG"""
        docs = []
        for idx, chunk in self.rag.doc_store.items():
            docs.append({
                "content": chunk.content,
                "url": chunk.source_url,
                "score": chunk.relevance_score
            })
        return docs

    async def research_with_artifacts(self, query: str, save_path: str):
        """Research and save artifacts using MCP tools"""
        if not self.mcp:
            raise ValueError("No MCP servers configured")

        # 1. Regular research
        answer = self.research(query)

        # 2. Plan artifact saving
        save_plan = self.mcp.plan_tool_sequence(
            task_description=f"Save research results to {save_path}",
            llm_client=self.llm
        )

        # 3. Execute plan
        # We need to pass the content to write. The plan usually just says "write_file",
        # but the content needs to be injected if the LLM didn't hallucinate it perfectly.
        # Ideally the LLM is given the content in context or we intervene.
        # For this demo, we assume the LLM might write the content if it fits context,
        # OR we manually add a step to write the answer.

        # Let's manually ensure the answer is written if the plan is just "prepare file"
        # Often the planner will say {"tool": "write_file", "params": {"path": "...", "content": "..."}}
        # But it doesn't know 'answer' variable.
        # So we might need to update the params.

        # Better approach: We expose a specific tool to "save_research" or we accept that
        # this method is a high-level orchestration.

        # We will iterate the plan and inject 'answer' if content is placeholder or missing
        for step in save_plan:
             if step.get("tool", "").endswith("write_file"):
                 params = step.get("params", {})
                 if "content" not in params or params["content"] in ["<content>", "RESULT"]:
                     params["content"] = answer

        save_results = await self.mcp.execute_plan(save_plan)

        return {
            "answer": answer,
            "artifacts_saved": save_results
        }
