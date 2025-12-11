from typing import List, Optional
import os
import logging
import requests

from ..provider import SearchProvider, SearchResult

logger = logging.getLogger(__name__)

class BraveSearchAdapter(SearchProvider):
    """Adapter for Brave Search."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Create a BraveSearchAdapter and set its API key.
        
        If an explicit api_key is provided, it is stored; otherwise the BRAVE_API_KEY environment variable is used. Logs a warning if no API key is found.
        
        Parameters:
            api_key (Optional[str]): Optional Brave Search API key to use for requests. If omitted, the adapter will attempt to read BRAVE_API_KEY from the environment.
        """
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        if not self.api_key:
             # We don't raise here to allow instantiation, but search will fail/warn
             logger.warning("BRAVE_API_KEY not found. Brave Search will fail.")

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
        Perform a web search using the Brave Search API and return results mapped to SearchResult objects.
        
        Parameters:
            region (Optional[str]): Region code for restricting results (currently unused).
            time_range (Optional[str]): Time filter shorthand: 'd' = day, 'w' = week, 'm' = month, 'y' = year. When `tuned` is true and a valid shorthand is provided, it is mapped to Brave's freshness parameter.
            safe_search (bool): If true, enable strict safesearch filtering.
            tuned (bool): If true, apply `time_range` mapping to the request; if false, `time_range` is ignored.
        
        Returns:
            List[SearchResult]: A list of search results with title, url, content (description), and source set to "brave".
        
        Raises:
            ValueError: If no API key is configured (BRAVE_API_KEY).
        """

        if not self.api_key:
            raise ValueError("BRAVE_API_KEY is missing")

        try:
            headers = {
                "X-Subscription-Token": self.api_key,
                "Accept": "application/json",
            }
            url = "https://api.search.brave.com/res/v1/web/search"
            params = {"q": query, "count": max_results}
            if safe_search:
                params["safesearch"] = "strict"

            # Map time_range to Brave freshness
            if tuned and time_range:
                freshness_map = {"d": "pd", "w": "pw", "m": "pm", "y": "py"}
                if time_range in freshness_map:
                    params["freshness"] = freshness_map[time_range]

            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            results = []
            if "web" in data and "results" in data["web"]:
                for item in data["web"]["results"]:
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        content=item.get("description", ""),
                        source="brave"
                    ))

            return results

        except Exception as e:
            logger.error(f"Brave Search failed: {e}")
            raise e