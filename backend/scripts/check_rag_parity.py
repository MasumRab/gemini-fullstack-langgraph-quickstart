import argparse
import logging
import sys
import os

# Ensure backend path is in pythonpath
sys.path.append(os.getcwd())

from backend.src.config.app_config import AppConfig
from backend.src.agent.rag import DeepSearchRAG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_parity():
    """
    Ingest sample data and verify that both FAISS and Chroma return similar results.
    """
    # Force dual write
    os.environ["RAG_STORE"] = "faiss"
    os.environ["DUAL_WRITE"] = "true"

    # Reload config (hacky but works for script)
    from backend.src.config.app_config import AppConfig
    # We might need to reload the module or just instantiate RAG which reads config

    logger.info("Initializing RAG with Dual Write...")
    try:
        rag = DeepSearchRAG()
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

    # Retrieve from Chroma (force read)
    # We temporarily patch config.rag_store or inspect the implementation.
    # The implementation reads `config.rag_store`.
    # To check parity without restarting, we can access `rag.chroma` directly if available.

    if not rag.use_chroma:
        logger.error("Chroma not enabled despite DUAL_WRITE=true")
        return

    logger.info("Retrieving from Chroma...")
    # Manually call chroma retrieve
    embedding = rag.embedder.encode(query).tolist()
    chroma_raw = rag.chroma.retrieve(query, top_k=2, query_embedding=embedding)

    # Compare
    logger.info("--- FAISS Results ---")
    faiss_ids = set()
    for res, score in faiss_results:
        logger.info(f"[{score:.4f}] {res.content[:50]}...")
        faiss_ids.add(res.content) # using content as proxy for ID since IDs differ in format

    logger.info("--- Chroma Results ---")
    chroma_ids = set()
    for res, score in chroma_raw:
        logger.info(f"[{score:.4f}] {res.content[:50]}...")
        chroma_ids.add(res.content)

    # Parity Logic
    overlap = len(faiss_ids.intersection(chroma_ids))
    logger.info(f"Overlap: {overlap}/2")

    if overlap == 2:
        logger.info("SUCCESS: Stores are in parity.")
    else:
        logger.warning("WARNING: Stores diverge.")

if __name__ == "__main__":
    check_parity()
