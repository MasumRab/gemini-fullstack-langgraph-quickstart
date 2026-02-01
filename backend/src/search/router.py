import logging
from typing import List, Optional, Dict, Any
from enum import Enum

from config.app_config import config, AppConfig
from .provider import SearchProvider, SearchResult
from .providers.google_adapter import GoogleSearchAdapter
from .providers.duckduckgo_adapter import DuckDuckGoAdapter
from .providers.brave_adapter import BraveSearchAdapter
from .providers.tavily_adapter import TavilyAdapter
from .providers.bing_adapter import BingAdapter

logger = logging.getLogger(__name__)

class SearchProviderType(Enum):
    GOOGLE = "google"
    DUCKDUCKGO = "duckduckgo"
    BRAVE = "brave"
    TAVILY = "tavily"
    BING = "bing"

class SearchRouter:
    """
    Routes search queries to the appropriate provider with fallback logic.
    """

    _PROVIDER_CLASSES = {
        SearchProviderType.GOOGLE.value: GoogleSearchAdapter,
        SearchProviderType.DUCKDUCKGO.value: DuckDuckGoAdapter,
        SearchProviderType.BRAVE.value: BraveSearchAdapter,
        SearchProviderType.TAVILY.value: TavilyAdapter,
        SearchProviderType.BING.value: BingAdapter,
    }

    def __init__(self, app_config: AppConfig = config):
        """Initialize router with config."""
        self.config = app_config
        self.providers: Dict[str, SearchProvider] = {}

    def _get_provider(self, name: str) -> Optional[SearchProvider]:
        if name in self.providers:
            return self.providers[name]

        provider_cls = self._PROVIDER_CLASSES.get(name)
        if not provider_cls:
            return None

        try:
            instance = provider_cls()
            self.providers[name] = instance
            return instance
        except Exception as e:
            logger.debug(f"Failed to initialize provider {name}: {e}")
            return None

    def search(
        self,
        query: str,
        max_results: int = 5,
        provider_name: Optional[str] = None,
        attempt_fallback: bool = True,
    ) -> List[SearchResult]:
        """
        Execute search with routing and fallback logic.

        Args:
            query: Search query
            max_results: Max results
            provider_name: Override configured provider
            attempt_fallback: Whether to try fallback provider on failure
        """
        # Determine primary provider
        primary_name = provider_name or self.config.search_provider
        provider = self._get_provider(primary_name)

        if not provider:
            logger.warning(f"Provider {primary_name} not available. Using fallback.")
            primary_name = self.config.search_fallback
            provider = self._get_provider(primary_name)

        if not provider:
            raise ValueError("No valid search provider available.")

        # Execute with reliability-first logic
        try:
            # First attempt: Tuned (strict/optimized)
            return provider.search(query, max_results=max_results, tuned=True)
        except Exception as e:
            logger.warning(f"Search failed with {primary_name} (tuned=True): {e}")

            # Second attempt: Untuned (relaxed) on same provider (Transient Error handling)
            try:
                return provider.search(query, max_results=max_results, tuned=False)
            except Exception as e2:
                logger.warning(f"Search failed with {primary_name} (tuned=False): {e2}")

                if attempt_fallback and primary_name != self.config.search_fallback:
                    fallback_name = self.config.search_fallback
                    logger.info(f"Switching to fallback provider: {fallback_name}")
                    fallback_provider = self._get_provider(fallback_name)
                    if fallback_provider:
                        # Fallback gets the same retry logic or just a single shot?
                        # For simplicity, fallback is usually single shot untuned or standard.
                        # Let's try standard (tuned=True default)
                        return fallback_provider.search(query, max_results=max_results)

                # If we get here, all attempts failed
                logger.error("All search attempts failed.")
                return []

# Singleton instance
search_router = SearchRouter()
