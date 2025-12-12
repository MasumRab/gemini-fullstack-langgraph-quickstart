from typing import Dict, Any, List
import logging
import re
from config.app_config import config

logger = logging.getLogger(__name__)

# Try to import cognee, fail gracefully
try:
    import cognee
    COGNEE_AVAILABLE = True
except ImportError:
    COGNEE_AVAILABLE = False
    logger.warning("Cognee not installed. Knowledge Graph enrichment will be skipped.")

from agent.state import OverallState
from langchain_core.runnables import RunnableConfig
from agent.registry import graph_registry

@graph_registry.describe(
    "kg_enrich",
    summary="Enriches the knowledge graph with research results for allowlisted domains.",
    tags=["kg", "enrichment"],
    outputs=["artifacts"],
)
async def kg_enrich(state: OverallState, runnable_config: RunnableConfig) -> OverallState:
    """
    Enrich the knowledge graph with allowlisted web research results found in the provided state.
    
    Processes each research result in `state["validated_web_research_result"]` or `state["web_research_result"]`, extracts the URL and domain, filters by the application allowlist, and submits the result text (the portion before the first "[") to the Cognee service for enrichment. Errors during per-result enrichment are logged and do not stop processing.
    
    Parameters:
        state (OverallState): Mutable execution state; expected to contain either
            `"validated_web_research_result"` or `"web_research_result"` as an iterable of result strings.
        runnable_config (RunnableConfig): Execution configuration (not inspected by this function).
    
    Returns:
        dict: If at least one item was successfully processed, returns `{"artifacts": {"kg_enriched_count": <int>}}`
        indicating how many results were enriched; otherwise returns an empty dict.
    """
    from backend.src.config.app_config import config as app_config

    if not app_config.kg_enabled:
        return {}

    if not COGNEE_AVAILABLE:
        return {}

    results = state.get("validated_web_research_result", []) or state.get("web_research_result", [])
    if not results:
        return {}

    processed_count = 0

    for result in results:
        url_match = re.search(r"\((http[s]?://.*?)\)", result)
        if not url_match:
            continue

        url = url_match.group(1)
        domain = url.split("//")[-1].split("/")[0]

        if not any(allowed in domain for allowed in app_config.kg_allowlist):
            continue

        try:
            text_content = result.split("[")[0].strip()
            if not text_content:
                continue

            logger.info(f"Enriching KG with content from {domain}")

            # Uncommented logic
            await cognee.add(text_content)
            await cognee.cognify()

            processed_count += 1
        except Exception as e:
            logger.error(f"Cognee enrichment failed for {url}: {e}")

    if processed_count > 0:
        return {"artifacts": {"kg_enriched_count": processed_count}}

    return {}