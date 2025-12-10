from backend.src.search.router import SearchRouter
from backend.src.config.app_config import AppConfig

def test_router():
    """Verify SearchRouter functionality."""
    # Mock config to force DuckDuckGo (since we might not have API keys in sandbox)
    # We can rely on DDG being available without keys.
    mock_config = AppConfig(
        search_provider="duckduckgo",
        search_fallback="duckduckgo"
    )

    router = SearchRouter(app_config=mock_config)
    results = router.search("LangChain", max_results=3)

    print(f"Found {len(results)} results.")
    for r in results:
        print(f"- {r.title} ({r.url}) [{r.source}]")

if __name__ == "__main__":
    test_router()
