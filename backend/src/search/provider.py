from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class SearchResult:
    """Standardized search result."""
    title: str
    url: str
    content: str
    raw_content: Optional[str] = None
    source: str = "unknown"

class SearchProvider(ABC):
    """Abstract base class for search providers."""

    @abstractmethod
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
        Execute a search using the provider.
        
        Parameters:
            query (str): Search query string.
            max_results (int): Maximum number of results to return.
            region (Optional[str]): Region code (e.g., "us-en") to localize results.
            time_range (Optional[str]): Time range filter (e.g., "d", "w", "m", "y").
            safe_search (bool): Enable safe search filtering.
            tuned (bool): Apply provider-specific optimizations or relaxed filters.
        
        Returns:
            List[SearchResult]: Search results matching the query, up to `max_results`.
        """
        pass