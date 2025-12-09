from typing import List, Optional
import logging
from duckduckgo_search import DDGS

from ..provider import SearchProvider, SearchResult

logger = logging.getLogger(__name__)

class DuckDuckGoAdapter(SearchProvider):
    """Adapter for DuckDuckGo Search."""

    def __init__(self):
        pass

    def search(
        self,
        query: str,
        max_results: int = 5,
        region: Optional[str] = "wt-wt",
        time_range: Optional[str] = None,
        safe_search: bool = True,
        tuned: bool = True,
    ) -> List[SearchResult]:

        # specific DDG region mapping if needed
        ddg_region = region if region else "wt-wt"

        # Time range mapping
        # DDG uses: 'd' (day), 'w' (week), 'm' (month), 'y' (year)

        # Tuned behavior: If not tuned (retry/fallback), maybe relax time range or strictness
        # For DDG, safe_search off could be a 'tuned' relaxation if safe_search was requested but failed?
        # Or here 'tuned' means standard optimization.
        # If `tuned=False` (transient retry), we might clear the time_range.

        effective_time_range = time_range if tuned else None

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    keywords=query,
                    region=ddg_region,
                    safesearch='on' if safe_search else 'off',
                    timelimit=effective_time_range,
                    max_results=max_results
                ))

            return [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    content=r.get("body", ""),
                    source="duckduckgo"
                )
                for r in results
            ]
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            raise e
