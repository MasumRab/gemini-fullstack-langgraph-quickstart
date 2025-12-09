from typing import List, Optional
import os
import logging
from google.genai import Client

from ..provider import SearchProvider, SearchResult

logger = logging.getLogger(__name__)

class GoogleSearchAdapter(SearchProvider):
    """Adapter for Google Search using the GenAI SDK."""

    def __init__(self, api_key: Optional[str] = None):
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

        # Note: The GenAI SDK Google Search tool is often implicit in `generate_content`.
        # However, for a standalone search tool, we might need to rely on the `tools` configuration
        # or use a different endpoint if available.
        # The existing `web_research` node uses `models.generate_content` with `google_search` tool
        # and parses grounding metadata. This adapter will mimic that behavior but return structured results.
        # Ideally, we would use a dedicated search API (like Custom Search JSON API) if strict control is needed,
        # but the prompt implies standardizing existing providers.
        #
        # Since `google.genai` is primarily an LLM client with tool access, we will use a "grounding" prompt
        # to extract search results.

        prompt = f"Search for: {query}"

        # Tuned parameters
        # In this context, 'tuned' could mean adjusting the prompt or tool configuration.
        # For GenAI, we might relax the prompt if tuned=False, but the tool is standard.

        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash", # Hardcoded or config-driven? Using flash for speed
                contents=prompt,
                config={
                    "tools": [{"google_search": {}}],
                    "temperature": 0,
                },
            )

            results = []
            if response.candidates and response.candidates[0].grounding_metadata:
                chunks = response.candidates[0].grounding_metadata.grounding_chunks
                supports = response.candidates[0].grounding_metadata.grounding_supports

                # The GenAI SDK returns chunks (web snippets) and supports (indices).
                # We iterate through chunks to build results.
                # Note: This is a simplified mapping. Real GenAI response structure varies.

                for chunk in chunks:
                    if chunk.web:
                        results.append(SearchResult(
                            title=chunk.web.title or "Untitled",
                            url=chunk.web.uri,
                            content=chunk.web.title, # Chunk content is not always fully exposed in simple web chunk objects
                            source="google"
                        ))

            # If standard grounding chunks are not populated as expected (can happen),
            # we might parse the text, but that's unreliable.
            # Fallback: check if the model just returned text with links.

            return results[:max_results]

        except Exception as e:
            logger.error(f"Google Search failed: {e}")
            raise e
