import logging
from typing import List

from duckduckgo_search import DDGS

from ..provider import SearchProvider, SearchResult

logger = logging.getLogger(__name__)


class DuckDuckGoAdapter(SearchProvider):
    """Adapter for DuckDuckGo Search."""

    def __init__(self):
        """Initialize adapter."""
        pass

    def search(
        self,
        query: str,
        max_results: int = 5,
        region: str | None = "wt-wt",
        time_range: str | None = None,
        safe_search: bool = True,
        tuned: bool = True,
    ) -> List[SearchResult]:
        """
        Perform a DuckDuckGo web search and return normalized results.
        
        Parameters:
            query (str): Search keywords.
            max_results (int): Maximum number of results to return.
            region (str | None): DDG region code to use; defaults to "wt-wt" when None or not provided.
            time_range (str | None): DDG timelimit value ('d', 'w', 'm', 'y') to restrict results by age.
            safe_search (bool): If True enable DDG safesearch; if False disable it.
            tuned (bool): When False, ignore `time_range` to relax temporal constraints (used for retries/fallbacks).
        
        Returns:
            List[SearchResult]: A list of SearchResult objects with `title`, `url`, `content`, and `source` set to "duckduckgo".
        """
        # specific DDG region mapping if needed
        ddg_region = region if region else "wt-wt"

        # Time range mapping
        # DDG uses: 'd' (day), 'w' (week), 'm' (month), 'y' (year)

        # Tuned behavior: If not tuned (retry/fallback), maybe relax time range or strictness
        effective_time_range = time_range if tuned else None

        try:
            with DDGS() as ddgs:
                results = list(
                    ddgs.text(
                        keywords=query,
                        region=ddg_region,
                        safesearch="on" if safe_search else "off",
                        timelimit=effective_time_range,
                        max_results=max_results,
                    )
                )

            return [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    content=r.get("body", ""),
                    source="duckduckgo",
                )
                for r in results
            ]
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            raise e
