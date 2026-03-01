import logging
import os
from typing import List

import requests

from ..provider import SearchProvider, SearchResult

logger = logging.getLogger(__name__)


class BingAdapter(SearchProvider):
    """Adapter for Bing Web Search API."""

    def __init__(self, api_key: str | None = None):
        """
        Create a BingAdapter instance configured with an API key and endpoint.
        
        If `api_key` is not provided, it is read from the `BING_API_KEY` environment variable. The `endpoint` is read from `BING_ENDPOINT` with a default of "https://api.bing.microsoft.com/v7.0/search". Logs a warning if no API key is available.
        @param api_key: Optional Bing API key to use; if omitted, the `BING_API_KEY` environment variable will be used.
        """
        self.api_key = api_key or os.getenv("BING_API_KEY")
        self.endpoint = os.getenv(
            "BING_ENDPOINT", "https://api.bing.microsoft.com/v7.0/search"
        )

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
        """
        Perform a web search using the Bing Web Search API and map results to SearchResult objects.
        
        Parameters:
            query (str): Search query string.
            max_results (int): Maximum number of results to request.
            region (str | None): Optional ISO country code sent as the `cc` parameter to bias results.
            time_range (str | None): Optional freshness filter; accepted values are:
                "d" for one day, "w" for one week, "m" for one month.
            safe_search (bool): If True, enables Bing's "Strict" safe search filtering.
            tuned (bool): Present for compatibility; not used by this implementation.
        
        Returns:
            List[SearchResult]: A list of SearchResult objects populated from Bing's webPages response.
        
        Raises:
            Exception: Propagates any exception raised while performing the HTTP request or parsing the response.
        
        Notes:
            If the adapter has no API key configured, this method returns an empty list without performing a request.
        """
        if not self.api_key:
            return []

        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        params = {
            "q": query,
            "count": max_results,
            "textDecorations": True,  # To get bolding in snippets
            "textFormat": "HTML",
        }

        if region:
            params["cc"] = region

        if safe_search:
            params["safeSearch"] = "Strict"

        # Time range logic (Bing uses 'freshness')
        # d/w/m mappings
        if time_range:
            if time_range == "d":
                params["freshness"] = "Day"
            elif time_range == "w":
                params["freshness"] = "Week"
            elif time_range == "m":
                params["freshness"] = "Month"

        try:
            response = requests.get(
                self.endpoint, headers=headers, params=params, timeout=10
            )
            response.raise_for_status()
            data = response.json()

            results = []
            if "webPages" in data and "value" in data["webPages"]:
                for item in data["webPages"]["value"]:
                    results.append(
                        SearchResult(
                            title=item.get("name", "Untitled"),
                            url=item.get("url", ""),
                            content=item.get(
                                "snippet", ""
                            ),  # snippet usually has bolding if textDecorations=True
                            source="bing",
                            metadata={
                                "displayUrl": item.get("displayUrl"),
                                "dateLastCrawled": item.get("dateLastCrawled"),
                            },
                        )
                    )

            return results

        except Exception as e:
            logger.error(f"Bing Search failed: {e}")
            raise e
