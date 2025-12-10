from typing import List, Optional
import os
import logging
from google.genai import Client

from ..provider import SearchProvider, SearchResult

logger = logging.getLogger(__name__)

class GoogleSearchAdapter(SearchProvider):
    """Adapter for Google Search using the GenAI SDK."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key."""
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
        Execute search.
        Note: region, time_range, safe_search, tuned are not currently supported by the GenAI SDK tool wrapper.
        """
        prompt = f"Search for: {query}"

        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={
                    "tools": [{"google_search": {}}],
                    "temperature": 0,
                },
            )

            results = []
            if response.candidates and response.candidates[0].grounding_metadata:
                chunks = response.candidates[0].grounding_metadata.grounding_chunks
                # supports = response.candidates[0].grounding_metadata.grounding_supports # Unused

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
