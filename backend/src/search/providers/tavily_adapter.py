import logging
import os
from typing import List

from ..provider import SearchProvider, SearchResult

logger = logging.getLogger(__name__)

# Try to import Tavily client, fall back to None if not available
try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None


class TavilyAdapter(SearchProvider):
    """Adapter for Tavily Search API."""

    def __init__(self, api_key: str | None = None):
        """
        Initialize the adapter with an API key and prepare the Tavily client if available.
        
        If `api_key` is not provided, the `TAVILY_API_KEY` environment variable is used. Logs a warning when no API key is found. When a Tavily client implementation is importable and an API key is present, `self.client` is set to a TavilyClient instance; otherwise `self.client` is set to `None`.
        
        Parameters:
            api_key (str | None): Explicit API key to use for Tavily; if `None`, the `TAVILY_API_KEY` environment variable will be checked.
        """
        # Avoid circular import by using os.getenv directly or checking config later
        # We will follow the pattern of checking env var in init
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            logger.warning("TAVILY_API_KEY not found. Tavily Search will fail.")

        if TavilyClient and self.api_key:
            self.client = TavilyClient(api_key=self.api_key)
        else:
            self.client = None

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
        Perform a search using the Tavily Search API and return normalized search results.
        
        Parameters:
        	query: The search query text.
        	max_results: Maximum number of results to request.
        	region: Optional region filter (not used when calling the Tavily client).
        	time_range: Optional time range filter (not used when calling the Tavily client).
        	safe_search: Whether to request safe-search filtering (not passed to the Tavily client).
        	tuned: If true, use a more detailed search depth ("advanced"); otherwise use "basic".
        
        Returns:
        	A list of SearchResult objects constructed from the Tavily response.
        
        Raises:
        	Exception: Propagates any exception raised by the underlying Tavily client.
        """
        if not self.client:
            if not TavilyClient:
                logger.error("Tavily python package not installed.")
            elif not self.api_key:
                logger.error("Tavily API Key missing.")
            return []

        try:
            # search_depth="advanced" is generally better for detailed results
            # max_results is supported
            response = self.client.search(
                query=query,
                search_depth="advanced" if tuned else "basic",
                max_results=max_results,
                # Tavily doesn't support 'safe_search' param directly in basic search usually,
                # but has include_domains/exclude_domains etc. We'll stick to basics.
            )

            results = []
            # Tavily returns {'results': [...]}
            for item in response.get("results", []):
                results.append(
                    SearchResult(
                        title=item.get("title", "Untitled"),
                        url=item.get("url", ""),
                        content=item.get("content", ""),
                        source="tavily",
                        metadata={
                            "score": item.get("score"),
                            "raw_content": item.get(
                                "raw_content"
                            ),  # sometimes available
                        },
                    )
                )

            return results

        except Exception as e:
            logger.error(f"Tavily Search failed: {e}")
            # If tuned failed, we could try basic, but the router handles fallback.
            raise e
