from dataclasses import dataclass
from typing import Tuple
import os
import logging

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class AppConfig:
    # RAG Configuration
    rag_store: str = os.getenv("RAG_STORE", "faiss")
    dual_write: bool = os.getenv("DUAL_WRITE", "false").lower() == "true"

    # Knowledge Graph Configuration
    kg_enabled: bool = os.getenv("KG_ENABLED", "false").lower() == "true"
    kg_allowlist: Tuple[str, ...] = tuple(filter(None, os.getenv("KG_ALLOWLIST", "").split(",")))

    # Search Configuration
    search_provider: str = os.getenv("SEARCH_PROVIDER", "google")
    search_fallback: str = os.getenv("SEARCH_FALLBACK", "duckduckgo")
    search_routing: str = os.getenv("SEARCH_ROUTING", "hybrid")

    # Validation Configuration
    validation_mode: str = os.getenv("VALIDATION_MODE", "hybrid")
    require_citations: bool = os.getenv("REQUIRE_CITATIONS", "true").lower() == "true"

    # Compression Configuration
    compression_enabled: bool = os.getenv("COMPRESSION_ENABLED", "true").lower() == "true"
    compression_mode: str = os.getenv("COMPRESSION_MODE", "tiered")

    # Budgets & Performance
    token_budget: int = int(os.getenv("TOKEN_BUDGET", "50000"))
    call_budget: int = int(os.getenv("CALL_BUDGET", "50"))
    latency_target_ms: int = int(os.getenv("LATENCY_TARGET_MS", "8000"))

    # Observability
    audit_mode: str = os.getenv("AUDIT_MODE", "off")
    log_level: str = os.getenv("LOG_LEVEL", "info")

    # Model Selection
    model_planning: str = os.getenv("MODEL_PLANNING", "primary_llm")
    model_validation: str = os.getenv("MODEL_VALIDATION", "cheaper_llm")
    model_compression: str = os.getenv("MODEL_COMPRESSION", "cheaper_summarizer")

    @classmethod
    def load(cls) -> "AppConfig":
        """Load configuration and log the effective settings."""
        config = cls()
        if config.audit_mode != "off":
            logger.info(f"Loaded AppConfig: {config}")
        return config

# Singleton instance
config = AppConfig.load()
