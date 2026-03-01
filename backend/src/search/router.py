import logging
import threading
from enum import Enum
from typing import Dict, List

from config.app_config import AppConfig, config

from .provider import SearchProvider, SearchResult

logger = logging.getLogger(__name__)


class SearchProviderType(Enum):
    GOOGLE = "google"
    DUCKDUCKGO = "duckduckgo"
    BRAVE = "brave"
    TAVILY = "tavily"
    BING = "bing"


class SearchRouter:
    """Routes search queries to the appropriate provider with fallback logic."""

    def __init__(self, app_config: AppConfig = config):
        """
        Create a SearchRouter configured with the given application settings.
        
        Parameters:
            app_config (AppConfig): Application configuration used to determine the default search provider and fallback behavior.
        
        Description:
            Stores the provided configuration, prepares an empty provider cache, and creates a lock for thread-safe lazy initialization of providers.
        """
        self.config = app_config
        self.providers: Dict[str, SearchProvider] = {}
        self._providers_lock = threading.Lock()

    def _get_provider(self, name: str) -> SearchProvider | None:
        # Quick check without lock
        """
        Retrieve a cached search provider by name or instantiate and cache it if available.
        
        Parameters:
            name (str): The provider identifier (e.g., "google", "duckduckgo", "brave", "tavily", "bing").
        
        Returns:
            SearchProvider | None: The provider instance for the given name, or `None` if the provider could not be instantiated or is unrecognized.
        """
        if name in self.providers:
            return self.providers[name]

        with self._providers_lock:
            # Double-checked locking
            if name in self.providers:
                return self.providers[name]

            try:
                if name == SearchProviderType.GOOGLE.value:
                    from .providers.google_adapter import GoogleSearchAdapter

                    self.providers[name] = GoogleSearchAdapter()
                elif name == SearchProviderType.BRAVE.value:
                    from .providers.brave_adapter import BraveSearchAdapter

                    self.providers[name] = BraveSearchAdapter()
                elif name == SearchProviderType.DUCKDUCKGO.value:
                    from .providers.duckduckgo_adapter import DuckDuckGoAdapter

                    self.providers[name] = DuckDuckGoAdapter()
                elif name == SearchProviderType.TAVILY.value:
                    from .providers.tavily_adapter import TavilyAdapter

                    self.providers[name] = TavilyAdapter()
                elif name == SearchProviderType.BING.value:
                    from .providers.bing_adapter import BingAdapter

                    self.providers[name] = BingAdapter()
            except Exception as e:
                logger.debug(f"Provider {name} failed to init: {e}")
                return None

            # Log warning for unrecognized provider
            if name not in self.providers:
                valid_providers = [p.value for p in SearchProviderType]
                logger.warning(
                    f"Unknown provider '{name}'. Valid providers: {valid_providers}"
                )

            return self.providers.get(name)

    def search(
        self,
        query: str,
        max_results: int = 5,
        provider_name: str | None = None,
        attempt_fallback: bool = True,
    ) -> List[SearchResult]:
        """
        Route a query to the selected search provider and return matching results.
        
        Selects the explicit provider_name if given, otherwise uses the configured primary provider; if that provider is unavailable and attempt_fallback is True, the configured fallback provider will be used. The method returns results from the first successful provider attempt or an empty list if all attempts fail.
        
        Parameters:
            query (str): Search query text.
            max_results (int): Maximum number of results to return.
            provider_name (str | None): Optional provider identifier to override the configured primary provider.
            attempt_fallback (bool): Whether to try the configured fallback provider when the primary provider fails.
        
        Returns:
            List[SearchResult]: Search results from the chosen provider; an empty list if no provider can successfully return results.
        
        Raises:
            ValueError: If no valid search provider is available.
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
