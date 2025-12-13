import logging
from typing import List, Optional, Dict, Any
from enum import Enum

from config.app_config import config, AppConfig
from .provider import SearchProvider, SearchResult
from .providers.google_adapter import GoogleSearchAdapter
from .providers.duckduckgo_adapter import DuckDuckGoAdapter
from .providers.brave_adapter import BraveSearchAdapter

logger = logging.getLogger(__name__)

class SearchProviderType(Enum):
    GOOGLE = "google"
    DUCKDUCKGO = "duckduckgo"
    BRAVE = "brave"

class SearchRouter:
    """
    Routes search queries to the appropriate provider with fallback logic.
    """

    def __init__(self, app_config: AppConfig = config):
        """Initialize router with config."""
        self.config = app_config
        self.providers: Dict[str, SearchProvider] = {}
        self._init_providers()

    def _init_providers(self):
        """Initialize providers based on availability and config."""
        # Google
        try:
            self.providers[SearchProviderType.GOOGLE.value] = GoogleSearchAdapter()
        except Exception as e:
            logger.debug(f"Google adapter failed to init: {e}")

        # Brave
        try:
            self.providers[SearchProviderType.BRAVE.value] = BraveSearchAdapter()
        except Exception as e:
            logger.debug(f"Brave adapter failed to init: {e}")

        # DuckDuckGo
        try:
            self.providers[SearchProviderType.DUCKDUCKGO.value] = DuckDuckGoAdapter()
        except Exception as e:
            logger.debug(f"DuckDuckGo adapter failed to init: {e}")

    def _get_provider(self, name: str) -> Optional[SearchProvider]:
        """
        Retrieve a registered search provider by name.
        
        Parameters:
            name (str): Provider identifier (for example "google", "duckduckgo", or "brave").
        
        Returns:
            SearchProvider or None: `SearchProvider` if a provider with the given name is registered, `None` otherwise.
        """
        return self.providers.get(name)

    def search(
        self,
        query: str,
        max_results: int = 5,
        provider_name: Optional[str] = None,
        attempt_fallback: bool = True,
    ) -> List[SearchResult]:
        """
        Route the query to an available search provider using retry and optional fallback logic.
        
        Performs up to two attempts on the selected provider (first with tuned=True, then with tuned=False) and, if enabled, switches to the configured fallback provider for a final attempt. Returns the results from the first successful attempt or an empty list if all attempts fail.
        
        Parameters:
            provider_name (Optional[str]): If provided, use this provider instead of the configured default.
            attempt_fallback (bool): If True, when the primary provider fails on both attempts, try the configured fallback provider.
        
        Returns:
            List[SearchResult]: Search results from the successful provider call, or an empty list if all attempts fail.
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