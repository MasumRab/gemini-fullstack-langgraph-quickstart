from typing import Dict, Any, List
import logging
import re
from backend.src.config.app_config import config

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
        logger.info(f"Enriched {processed_count} items in KG.")
        # Do not return 'artifacts' here as it violates the Artifact TypedDict schema.
        # The enrichment is a side-effect.
        return {}

    return {}
