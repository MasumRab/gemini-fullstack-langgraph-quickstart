import argparse
import logging
import sys
import os
from typing import Optional

# Ensure backend path is in pythonpath
sys.path.append(os.getcwd())

from config.app_config import AppConfig
from agent.rag import DeepSearchRAG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_parity(test_config: Optional[AppConfig] = None):
    """
    Ingest sample data and verify that both FAISS and Chroma return similar results.
    """
    # Create test configuration
    if test_config is None:
        try:
            test_config = AppConfig(
                rag_store="faiss",
                dual_write=True,
            )
        except ValueError:
            logger.warning("Failed to create complete AppConfig, falling back to defaults")
            # Fallback for environments where env vars might be strict
            pass

    logger.info("Initializing RAG with Dual Write...")
    try:
        rag = DeepSearchRAG(config=test_config)
    except ImportError:
        logger.error("Skipping parity check: Dependencies missing")
        return

    # Ingest
    sample_docs = [
        {"content": "Python is a high-level programming language.", "url": "http://python.org", "score": 1.0},
        {"content": "Java is a class-based, object-oriented programming language.", "url": "http://java.com", "score": 1.0},
        {"content": "The sky is blue and the grass is green.", "url": "http://nature.com", "score": 0.5},
    ]

    logger.info("Ingesting documents...")
    rag.ingest_research_results(sample_docs, subgoal_id="test_subgoal")

    query = "programming language"

    # Retrieve from FAISS (default since RAG_STORE=faiss)
    logger.info("Retrieving from FAISS...")
    faiss_results = rag.retrieve(query, top_k=2)

    # Retrieve from Chroma (explicit call)
    try:
        logger.info("Retrieving from Chroma...")
        chroma_raw = rag.retrieve_from_chroma(query, top_k=2)
    except ValueError as e:
        logger.error(f"Chroma not enabled: {e}")
        return

    # Compare
    logger.info("--- FAISS Results ---")
    faiss_docs = []
    for res, score in faiss_results:
        logger.info(f"[{score:.4f}] {res.content[:50]}...")
        # Use a composite key of (url, hash(content)) for identity
        faiss_docs.append((res.source_url, hash(res.content)))

    logger.info("--- Chroma Results ---")
    chroma_docs = []
    for res, score in chroma_raw:
        logger.info(f"[{score:.4f}] {res.content[:50]}...")
        chroma_docs.append((res.source_url, hash(res.content)))

    # Parity Logic
    overlap = len(set(faiss_docs).intersection(set(chroma_docs)))
    logger.info(f"Overlap: {overlap}/2")

    if overlap == 2:
        logger.info("SUCCESS: Stores are in parity.")
    else:
        logger.warning("WARNING: Stores diverge.")

if __name__ == "__main__":
    check_parity()
