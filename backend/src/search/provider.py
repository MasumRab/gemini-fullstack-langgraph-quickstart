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
    metadata: Optional[dict] = None

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
        Execute a search query.

        Args:
            query: The search query string.
            max_results: Maximum number of results to return.
            region: Region code (e.g., "us-en").
            time_range: Time range (e.g., "d", "w", "m", "y").
            safe_search: Whether to enable safe search.
            tuned: Whether to use provider-specific optimizations (e.g. relaxed filters).
        """
        pass
