import logging
from typing import List, Optional, Dict, Any
from enum import Enum

from config.app_config import config, AppConfig
from .provider import SearchProvider, SearchResult

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

    def __init__(self, app_config: AppConfig = config):
        """Initialize router with config."""
        self.config = app_config
        self.providers: Dict[str, SearchProvider] = {}

    def _load_provider(self, name: str) -> Optional[SearchProvider]:
        """Lazily load provider class and instantiate."""
        if name in self.providers:
            return self.providers[name]

        provider = None
        try:
            if name == SearchProviderType.GOOGLE.value:
                from .providers.google_adapter import GoogleSearchAdapter
                provider = GoogleSearchAdapter()
            elif name == SearchProviderType.DUCKDUCKGO.value:
                from .providers.duckduckgo_adapter import DuckDuckGoAdapter
                provider = DuckDuckGoAdapter()
            elif name == SearchProviderType.BRAVE.value:
                from .providers.brave_adapter import BraveSearchAdapter
                provider = BraveSearchAdapter()
            elif name == SearchProviderType.TAVILY.value:
                from .providers.tavily_adapter import TavilyAdapter
                provider = TavilyAdapter()
            elif name == SearchProviderType.BING.value:
                from .providers.bing_adapter import BingAdapter
                provider = BingAdapter()

            if provider:
                self.providers[name] = provider

        except Exception as e:
            logger.debug(f"Failed to lazy load provider {name}: {e}")

        return provider

    def _get_provider(self, name: str) -> Optional[SearchProvider]:
        return self._load_provider(name)

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
            # Fallback was also unavailable or failed to init
            logger.error("No valid search provider available.")
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
