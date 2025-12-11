from typing import List, Dict, Optional, Tuple, Any
import logging
import time
from dataclasses import dataclass, field, asdict
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
    """
    ChromaDB implementation of the RAG store.
    """

    def __init__(
        self,
        collection_name: str = "deep_search_evidence",
        persist_path: str = "./chroma_db",
        embedding_function: Any = None,
        allow_reset: bool = False
    ):
        """
        Initialize a persistent ChromaDB-backed evidence collection and client.
        
        Creates a PersistentClient at the given persist_path (optionally allowing destructive reset) and gets or creates a collection with the provided name and optional embedding function.
        
        Parameters:
            collection_name (str): Name of the Chroma collection to use or create.
            persist_path (str): Filesystem path where the Chroma database is persisted.
            embedding_function (Any): Optional embedding function compatible with the collection; if None, the collection's default embedding is used.
            allow_reset (bool): If True, allow destructive reset of the underlying database.
        """
        self.client = chromadb.PersistentClient(path=persist_path, settings=Settings(allow_reset=allow_reset))

        # Use default embedding function if none provided (Chroma uses all-MiniLM-L6-v2 by default)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function
        )
        logger.info(f"Initialized ChromaStore with collection '{collection_name}' at '{persist_path}'")

    def add_evidence(self, evidence_list: List[EvidenceChunk], embeddings: Optional[List[List[float]]] = None):
        """
        Add a list of EvidenceChunk items to the Chroma collection.
        
        Each EvidenceChunk is converted into a document, an id, and a flattened metadata dictionary and upserted into the collection. If `embeddings` is provided, those embeddings are used; otherwise the collection's embedding function is used to generate embeddings.
        
        Parameters:
            evidence_list (List[EvidenceChunk]): Evidence chunks to add; each must have a unique `chunk_id`.
            embeddings (Optional[List[List[float]]]): Optional precomputed embeddings aligned with `evidence_list`.
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
                **e.metadata
            }
            metadatas.append(meta)

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings if embeddings is not None else None
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        subgoal_filter: Optional[str] = None,
        min_score: float = 0.0,
        query_embedding: Optional[List[float]] = None
    ) -> List[Tuple[EvidenceChunk, float]]:
        """
        Retrieve relevant evidence for a text query from the Chroma collection.
        
        Parameters:
            query (str): Query text used when no precomputed embedding is provided.
            top_k (int): Maximum number of results to return.
            subgoal_filter (Optional[str]): If provided, restricts results to this subgoal_id.
            min_score (float): Minimum similarity threshold in [0, 1]; results with similarity below this are excluded.
            query_embedding (Optional[List[float]]): Precomputed embedding to use instead of the query text.
        
        Returns:
            List[Tuple[EvidenceChunk, float]]: Pairs of EvidenceChunk and similarity (0 to 1), sorted by descending similarity.
        """
        where_filter = {}
        if subgoal_filter:
            where_filter["subgoal_id"] = subgoal_filter

        try:
            # If we have pre-computed embedding, use query_embeddings
            results = self.collection.query(
                query_texts=[query] if query_embedding is None else None,
                query_embeddings=[query_embedding] if query_embedding is not None else None,
                n_results=top_k,
                where=where_filter if where_filter else None
            )
        except Exception as e:
            logger.error(f"Chroma query failed: {e}")
            return []

        if not results or not results.get("ids") or not results["ids"][0]:
            logger.debug("Chroma query returned empty results")
            return []

        # Parse results
        parsed_results = []

        # ids, distances, metadatas, documents are lists of lists (one list per query)
        ids = results["ids"][0]
        distances = results["distances"][0] if results["distances"] else [0.0] * len(ids)
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
                metadata={k: v for k, v in meta.items() if k not in ["source_url", "subgoal_id", "relevance_score", "timestamp"]}
            )

            parsed_results.append((evidence, similarity))

        # Sort by similarity desc
        parsed_results.sort(key=lambda x: x[1], reverse=True)
        return parsed_results

    def count(self) -> int:
        """
        Return the number of items stored in the underlying Chroma collection.
        
        Returns:
            int: The total count of documents in the collection.
        """
        return self.collection.count()

    def reset(self):
        """
        Reset the underlying ChromaDB client and clear the store's persisted data.
        
        This forces the backend Chroma database to be reset to an empty state, removing all collections and stored embeddings associated with the client.
        """
        self.client.reset()