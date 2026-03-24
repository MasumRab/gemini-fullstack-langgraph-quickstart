import logging
import os
from typing import List

import requests

from ..provider import SearchProvider, SearchResult

logger = logging.getLogger(__name__)

class BingAdapter(SearchProvider):
    """Adapter for Bing Web Search API."""

    def __init__(self, api_key: str | None = None):
        """Initialize with API key."""
        self.api_key = api_key or os.getenv("BING_API_KEY")
        self.endpoint = os.getenv("BING_ENDPOINT", "https://api.bing.microsoft.com/v7.0/search")

        if not self.api_key:
            logger.warning("BING_API_KEY not found. Bing Search will fail.")

    def search(
        self,
        query: str,
        max_results: int = 5,
        region: str | None = None,
        time_range: str | None = None,
        safe_search: bool = True,
        tuned: bool = True,
    ) -> List[SearchResult]:
        """Execute search using Bing API.
        """
        if not self.api_key:
            return []

        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        params = {
            "q": query,
            "count": max_results,
            "textDecorations": True, # To get bolding in snippets
            "textFormat": "HTML",
        }

        if region:
            params["cc"] = region

        if safe_search:
            params["safeSearch"] = "Strict"

        # Time range logic (Bing uses 'freshness')
        # d/w/m mappings
        if time_range:
            if time_range == 'd':
                params['freshness'] = 'Day'
            elif time_range == 'w':
                params['freshness'] = 'Week'
            elif time_range == 'm':
                params['freshness'] = 'Month'

        try:
            response = requests.get(self.endpoint, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            results = []
            if "webPages" in data and "value" in data["webPages"]:
                for item in data["webPages"]["value"]:
                    results.append(SearchResult(
                        title=item.get("name", "Untitled"),
                        url=item.get("url", ""),
                        content=item.get("snippet", ""), # snippet usually has bolding if textDecorations=True
                        source="bing",
                        metadata={
                            "displayUrl": item.get("displayUrl"),
                            "dateLastCrawled": item.get("dateLastCrawled")
                        }
                    ))

            return results

        except Exception as e:
            logger.error(f"Bing Search failed: {e}")
            raise e
