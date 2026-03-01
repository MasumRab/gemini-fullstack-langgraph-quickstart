import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

import chromadb
from chromadb.config import Settings

# Re-use the EvidenceChunk definition from the main agent to ensure compatibility
# However, we must redefine it here to avoid circular imports if we want independent modules.
# For now, let's redefine a compatible dataclass.

logger = logging.getLogger(__name__)


@dataclass
class EvidenceChunk:
    """Individual evidence unit with metadata."""

    content: str
    source_url: str
    subgoal_id: str
    relevance_score: float
    timestamp: float
    chunk_id: str
    metadata: Dict = field(default_factory=dict)


class ChromaStore:
    """ChromaDB implementation of the RAG store."""

    def __init__(
        self,
        collection_name: str = "deep_search_evidence",
        persist_path: str = "./chroma_db",
        embedding_function: Any = None,
        allow_reset: bool = False,
    ):
        """
        Initialize the ChromaDB-backed store and ensure the collection exists.
        
        Parameters:
            collection_name: Name of the Chroma collection to create or open.
            persist_path: Filesystem path where the Chroma database is persisted.
            embedding_function: Optional embedding function to use for the collection; if `None`, the store uses Chroma's default compatible embedding (all-MiniLM-L6-v2).
            allow_reset: If `True`, allow destructive reset operations on the underlying persistent client.
        """
        self.client = chromadb.PersistentClient(
            path=persist_path, settings=Settings(allow_reset=allow_reset)
        )

        # Use default embedding function if none provided (Chroma uses all-MiniLM-L6-v2 by default)
        self.collection = self.client.get_or_create_collection(
            name=collection_name, embedding_function=embedding_function
        )
        logger.info(
            f"Initialized ChromaStore with collection '{collection_name}' at '{persist_path}'"
        )

    def add_evidence(
        self,
        evidence_list: List[EvidenceChunk],
        embeddings: List[List[float]] | None = None,
    ):
        """
        Add multiple EvidenceChunk items to the Chroma collection.
        
        If `evidence_list` is empty this is a no-op. Each chunk's core fields (source_url, subgoal_id, relevance_score, timestamp) and any additional `metadata` are stored as flattened metadata entries.
        
        Parameters:
            evidence_list (List[EvidenceChunk]): Evidence chunks to add to the store.
            embeddings (List[List[float]] | None): Optional list of precomputed embeddings aligned with `evidence_list`; if `None`, the collection will compute embeddings.
        """
        if not evidence_list:
            return

        ids = [e.chunk_id for e in evidence_list]
        documents = [e.content for e in evidence_list]
        metadatas = []

        for e in evidence_list:
            # Flatten metadata for Chroma (no nested dicts allowed usually)
            meta = {
                "source_url": e.source_url,
                "subgoal_id": e.subgoal_id,
                "relevance_score": float(e.relevance_score),
                "timestamp": float(e.timestamp),
                **e.metadata,
            }
            metadatas.append(meta)

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings if embeddings is not None else None,
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        subgoal_filter: str | None = None,
        min_score: float = 0.0,
        query_embedding: List[float] | None = None,
    ) -> List[Tuple[EvidenceChunk, float]]:
        """
        Retrieve relevant evidence chunks matching a text query or a precomputed query embedding.
        
        Searches the collection using either `query` (text) or `query_embedding` (vector), optionally restricts results to a specific `subgoal_id`, filters out results with similarity below `min_score`, and returns up to `top_k` matches sorted by descending similarity.
        
        Parameters:
            query (str): Text query used when `query_embedding` is not provided.
            top_k (int): Maximum number of results to return.
            subgoal_filter (str | None): If provided, only return chunks with this `subgoal_id`.
            min_score (float): Minimum similarity threshold (0 to 1); results with similarity below this value are excluded.
            query_embedding (List[float] | None): Optional precomputed embedding to use instead of the text query.
        
        Returns:
            List[Tuple[EvidenceChunk, float]]: List of (EvidenceChunk, similarity_score) pairs where `similarity_score` is in [0, 1], sorted by similarity descending.
        """
        where_filter = {}
        if subgoal_filter:
            where_filter["subgoal_id"] = subgoal_filter

        # If we have pre-computed embedding, use query_embeddings
        results = self.collection.query(
            query_texts=[query] if query_embedding is None else None,
            query_embeddings=[query_embedding] if query_embedding is not None else None,
            n_results=top_k,
            where=where_filter if where_filter else None,
        )

        if not results["ids"] or not results["ids"][0]:
            return []

        # Parse results
        parsed_results = []

        # ids, distances, metadatas, documents are lists of lists (one list per query)
        ids = results["ids"][0]
        distances = (
            results["distances"][0] if results["distances"] else [0.0] * len(ids)
        )
        metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(ids)
        docs = results["documents"][0] if results["documents"] else [""] * len(ids)

        for i, doc_id in enumerate(ids):
            meta = metas[i]
            dist = distances[i]

            # Chroma returns L2 distance by default (lower is better).
            # Convert to similarity: 1 / (1 + distance)
            similarity = 1 / (1 + dist)

            if similarity < min_score:
                continue

            # Reconstruct EvidenceChunk
            evidence = EvidenceChunk(
                chunk_id=doc_id,
                content=docs[i],
                source_url=meta.get("source_url", ""),
                subgoal_id=meta.get("subgoal_id", ""),
                relevance_score=meta.get("relevance_score", 0.0),
                timestamp=meta.get("timestamp", 0.0),
                metadata={
                    k: v
                    for k, v in meta.items()
                    if k
                    not in ["source_url", "subgoal_id", "relevance_score", "timestamp"]
                },
            )

            parsed_results.append((evidence, similarity))

        # Sort by similarity desc
        parsed_results.sort(key=lambda x: x[1], reverse=True)
        return parsed_results

    def count(self) -> int:
        return self.collection.count()

    def reset(self):
        self.client.reset()
