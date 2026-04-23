"""Search module providing unified search routing and provider abstractions."""
from .router import search_router, SearchRouter
from .provider import SearchProvider, SearchResult

__all__ = ["search_router", "SearchRouter", "SearchProvider", "SearchResult"]
