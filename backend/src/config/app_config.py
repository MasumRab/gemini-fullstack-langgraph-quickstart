import logging
import os
from dataclasses import dataclass, field
from typing import List, Tuple

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppConfig:
    """Application configuration container with environment variable loading and validation."""

    # RAG Configuration
    rag_store: str = os.getenv("RAG_STORE", "faiss")
    dual_write: bool = os.getenv("DUAL_WRITE", "false").lower() == "true"
    chroma_persist_path: str = os.getenv("CHROMA_PERSIST_PATH", "./chroma_db")

    # Knowledge Graph Configuration
    kg_enabled: bool = os.getenv("KG_ENABLED", "false").lower() == "true"
    kg_allowlist: Tuple[str, ...] = tuple(
        filter(None, os.getenv("KG_ALLOWLIST", "").split(","))
    )

    # Search Configuration
    search_provider: str = os.getenv("SEARCH_PROVIDER", "google")
    search_fallback: str = os.getenv("SEARCH_FALLBACK", "duckduckgo")
    search_routing: str = os.getenv("SEARCH_ROUTING", "hybrid")

    # Validation Configuration
    validation_mode: str = os.getenv("VALIDATION_MODE", "hybrid")
    require_citations: bool = os.getenv("REQUIRE_CITATIONS", "true").lower() == "true"

    # Compression Configuration
    compression_enabled: bool = (
        os.getenv("COMPRESSION_ENABLED", "true").lower() == "true"
    )
    compression_mode: str = os.getenv("COMPRESSION_MODE", "tiered")

    # Budgets & Performance
    token_budget: int = field(
        default_factory=lambda: int(os.getenv("TOKEN_BUDGET", "50000"))
    )
    call_budget: int = field(
        default_factory=lambda: int(os.getenv("CALL_BUDGET", "50"))
    )
    latency_target_ms: int = field(
        default_factory=lambda: int(os.getenv("LATENCY_TARGET_MS", "8000"))
    )

    # Observability
    audit_mode: str = os.getenv("AUDIT_MODE", "off")
    log_level: str = os.getenv("LOG_LEVEL", "info")

    # Security
    cors_origins: Tuple[str, ...] = tuple(
        filter(None, os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","))
    )
    allowed_hosts: Tuple[str, ...] = tuple(
        filter(None, os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(","))
    )

    # Model Selection
    model_planning: str = os.getenv("MODEL_PLANNING", "gemma-3-27b-it")
    model_validation: str = os.getenv("MODEL_VALIDATION", "gemma-3-27b-it")
    model_compression: str = os.getenv("MODEL_COMPRESSION", "gemma-3-27b-it")

    # Security Configuration
    CORS_ORIGINS: List[str] = field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGINS", "http://localhost:5173"
        ).split(",")
    )

    @classmethod
    def load(cls) -> "AppConfig":
        """Load configuration and log the effective settings."""
        try:
            config = cls()
            if config.audit_mode != "off":
                logger.info(f"Loaded AppConfig: {config}")
            return config
        except ValueError as e:
            logger.error(f"Configuration loading failed: {e}")
            raise e


# Singleton instance
config = AppConfig.load()
