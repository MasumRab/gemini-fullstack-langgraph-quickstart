from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class SearchResult:
    """Standardized search result."""

    title: str
    url: str
    content: str
    raw_content: str | None = None
    source: str = "unknown"
    metadata: dict | None = None


class SearchProvider(ABC):
    """Abstract base class for search providers."""

    @abstractmethod
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
        Run a search query against the provider and return matching results.
        
        Parameters:
            query (str): The search query string.
            max_results (int): Maximum number of results to return.
            region (str | None): Optional region code (e.g., "us-en") to bias or filter results.
            time_range (str | None): Optional time range specifier (e.g., "d", "w", "m", "y") to restrict results by recency.
            safe_search (bool): Whether to enable safe-search filtering.
            tuned (bool): Whether to apply provider-specific optimizations or tuning for result relevance.
        
        Returns:
            List[SearchResult]: A list of SearchResult objects matching the query, limited to at most `max_results`.
        """
        pass
