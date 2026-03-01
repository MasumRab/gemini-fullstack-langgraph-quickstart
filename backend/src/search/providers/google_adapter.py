import logging
import os
from typing import List

from google.genai import Client

from ..provider import SearchProvider, SearchResult

logger = logging.getLogger(__name__)


class GoogleSearchAdapter(SearchProvider):
    """Adapter for Google Search using the GenAI SDK."""

    def __init__(self, api_key: str | None = None):
        """
        Create a GoogleSearchAdapter with an API key and initialize the GenAI client.
        
        Parameters:
            api_key (str | None): API key to use; if None, GEMINI_API_KEY is read from the environment. If no key is found, a warning is logged.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found. Google Search may fail.")
        self.client = Client(api_key=self.api_key)

    def search(
        self,
        query: str,
        max_results: int = 5,
        region: str | None = None,
        time_range: str | None = None,
        safe_search: bool = True,
        tuned: bool = True,
    ) -> List[SearchResult]:
        """
        Perform a Google-backed search for the given query.
        
        Parameters:
        	query (str): The search query.
        	max_results (int): Maximum number of results to return.
        	region (str | None): Optional region hint; currently ignored by the GenAI SDK wrapper.
        	time_range (str | None): Optional time-range hint; currently ignored by the GenAI SDK wrapper.
        	safe_search (bool): Safe-search toggle; currently ignored by the GenAI SDK wrapper.
        	tuned (bool): Tuning hint for results; currently ignored by the GenAI SDK wrapper.
        
        Returns:
        	List[SearchResult]: A list of SearchResult objects sourced from Google, limited to `max_results`.
        """
        from agent.models import GEMINI_FLASH

        prompt = f"Search for: {query}"

        try:
            response = self.client.models.generate_content(
                model=GEMINI_FLASH,
                contents=prompt,
                config={
                    "tools": [{"google_search": {}}],
                    "temperature": 0,
                },
            )

            results = []
            if response.candidates and response.candidates[0].grounding_metadata:
                chunks = response.candidates[0].grounding_metadata.grounding_chunks

                for chunk in chunks:
                    if chunk.web:
                        # Extract snippet or title fallback
                        content = (
                            getattr(chunk.web, "snippet", None) or chunk.web.title or ""
                        )
                        results.append(
                            SearchResult(
                                title=chunk.web.title or "Untitled",
                                url=chunk.web.uri,
                                content=content,
                                source="google",
                            )
                        )

            return results[:max_results]

        except Exception as e:
            logger.error(f"Google Search failed: {e}")
            raise e
