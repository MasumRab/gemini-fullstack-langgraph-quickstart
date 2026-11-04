"""Search module providing unified search routing and provider abstractions."""

from .provider import SearchProvider, SearchResult
from .router import SearchRouter, search_router

__all__ = ["search_router", "SearchRouter", "SearchProvider", "SearchResult"]
