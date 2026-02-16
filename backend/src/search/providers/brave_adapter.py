import logging
import os
from typing import List

import requests

from ..provider import SearchProvider, SearchResult

logger = logging.getLogger(__name__)

class BraveSearchAdapter(SearchProvider):
    """Adapter for Brave Search."""

    def __init__(self, api_key: str | None = None):
        """Initialize with API key."""
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        if not self.api_key:
             # We don't raise here to allow instantiation, but search will fail/warn
             logger.warning("BRAVE_API_KEY not found. Brave Search will fail.")

    def search(
        self,
        query: str,
        max_results: int = 5,
        region: str | None = None,
        time_range: str | None = None,
        safe_search: bool = True,
        tuned: bool = True,
    ) -> List[SearchResult]:
        """Execute search via Brave API."""
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
