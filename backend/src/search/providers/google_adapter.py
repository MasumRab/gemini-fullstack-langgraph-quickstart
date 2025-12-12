from typing import List, Optional
import os
import logging
from google.genai import Client

from ..provider import SearchProvider, SearchResult

logger = logging.getLogger(__name__)

class GoogleSearchAdapter(SearchProvider):
    """Adapter for Google Search using the GenAI SDK."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the adapter and create a GenAI Client.
        
        If `api_key` is not provided, the constructor reads `GEMINI_API_KEY` from the environment and logs a warning when no key is found. Sets `self.api_key` to the resolved value and initializes `self.client` with that key.
        
        Parameters:
            api_key (Optional[str]): API key for the GenAI SDK. If omitted, `GEMINI_API_KEY` environment variable is used.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found. Google Search may fail.")
        self.client = Client(api_key=self.api_key)

    def search(
        self,
        query: str,
        max_results: int = 5,
        region: Optional[str] = None,
        time_range: Optional[str] = None,
        safe_search: bool = True,
        tuned: bool = True,
    ) -> List[SearchResult]:
        """
        Perform a Google-style web search using the adapter's configured GenAI client and return matching search results.
        
        Parameters:
            query (str): Search query text.
            max_results (int): Maximum number of SearchResult objects to return.
            region (Optional[str]): Ignored; not supported by the underlying SDK.
            time_range (Optional[str]): Ignored; not supported by the underlying SDK.
            safe_search (bool): Ignored; not supported by the underlying SDK.
            tuned (bool): Ignored; not supported by the underlying SDK.
        
        Returns:
            List[SearchResult]: A list of search results (each with title, url, content, and source). The list contains at most `max_results` items.
        """
        prompt = f"Search for: {query}"

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
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
                        content = getattr(chunk.web, 'snippet', None) or chunk.web.title or ""
                        results.append(SearchResult(
                            title=chunk.web.title or "Untitled",
                            url=chunk.web.uri,
                            content=content,
                            source="google"
                        ))

            return results[:max_results]

        except Exception as e:
            logger.error(f"Google Search failed: {e}")
            raise e