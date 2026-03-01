import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter

from agent.llm_client import call_llm_robust

# Optional imports for RAG dependencies
try:
    import faiss
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None
    faiss = None

# Optional Chroma
try:
    from rag.chroma_store import ChromaStore
    from rag.chroma_store import EvidenceChunk as ChromaEvidenceChunk

    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    ChromaStore = None
    ChromaEvidenceChunk = None

logger = logging.getLogger(__name__)


@dataclass
class EvidenceChunk:
    """Individual evidence unit with metadata"""

    content: str
    source_url: str
    subgoal_id: str
    relevance_score: float
    timestamp: float
    chunk_id: str
    metadata: Dict = field(default_factory=dict)


class DeepSearchRAG:
    """RAG system optimized for deep research workflows.
    Implements continuous evidence auditing and context pruning.
    Now supports hybrid store (FAISS + Chroma) with dual-write.
    """

    def __init__(
        self,
        config=None,  # Allow injecting config
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        max_context_chunks: int = 10,
    ):
        """
        Initialize the DeepSearchRAG instance, loading the embedding model, selecting and initializing vector stores (FAISS and optionally Chroma) according to configuration, creating a consistent embedding wrapper for Chroma, and configuring the text splitter and subgoal evidence tracking.
        
        Parameters:
            config (Any | None): Optional configuration object to override the global app config; expects attributes like `rag_store`, `dual_write`, and optionally `chroma_persist_path`.
            embedding_model (str): SentenceTransformers model identifier to load for embeddings.
            chunk_size (int): Maximum characters per text chunk produced by the splitter.
            chunk_overlap (int): Number of overlapping characters between adjacent chunks.
            max_context_chunks (int): Maximum number of evidence chunks to include when building synthesis context.
        """
        self.embedding_model = embedding_model
        # Use provided config or fallback to global
        from config.app_config import config as global_config

        self.config = config or global_config

        # Load embedding model
        if SentenceTransformer:
            logger.info(f"Loading embedding model: {embedding_model}")
            self.embedder = SentenceTransformer(embedding_model)
            self.embedding_dim = self.embedder.get_sentence_embedding_dimension()
        else:
            raise ImportError("sentence-transformers required")

        # Initialize Stores
        # Force fallback if optional libs missing
        requested_store = self.config.rag_store

        if requested_store == "chroma" and not CHROMA_AVAILABLE:
            logger.warning("ChromaDB not available. Falling back to FAISS.")
            requested_store = "faiss"

        # Store selection logic:
        # - When dual_write is enabled, BOTH stores are used for redundancy
        # - use_faiss/use_chroma flags control which stores are active
        # - Dual-write overrides individual flags to ensure both stores receive data
        self.use_faiss = requested_store == "faiss" or self.config.dual_write
        self.use_chroma = (
            requested_store == "chroma" or self.config.dual_write
        ) and CHROMA_AVAILABLE

        # FAISS Init
        if self.use_faiss:
            if faiss is None:
                raise ImportError("faiss-cpu required for FAISS store")
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            self.index_with_ids = faiss.IndexIDMap(self.index)
            self.doc_store: Dict[int, EvidenceChunk] = {}
            self.next_id = 0

        # Chroma Init
        if self.use_chroma and CHROMA_AVAILABLE:
            # Configurable path
            persist_path = getattr(self.config, "chroma_persist_path", "./chroma_db")

            # Create wrapper for consistent embeddings between FAISS and Chroma
            embedding_fn = None
            if self.embedder:

                class ConsistentEmbeddingFunction:
                    def __init__(self, model):
                        """
                        Initialize the instance with the provided model used for downstream operations.
                        
                        Parameters:
                            model: The model object to use (e.g., a machine-learning model or encoder). It should implement the interface expected by this class for inference or embedding operations.
                        """
                        self.model = model

                    def __call__(self, input):
                        # Ensure input is list of strings
                        """
                        Generate embeddings for a string or list of strings using the wrapped model.
                        
                        Parameters:
                            input (str | list[str]): A single text string or a list of text strings to encode.
                        
                        Returns:
                            list[list[float]]: A list of embedding vectors (one vector per input string), each vector represented as a list of floats.
                        """
                        if isinstance(input, str):
                            input = [input]
                        # Return list of lists of floats
                        embeddings = self.model.encode(input)
                        return embeddings.tolist()

                embedding_fn = ConsistentEmbeddingFunction(self.embedder)

            self.chroma = ChromaStore(
                collection_name="deep_search_evidence",
                persist_path=persist_path,
                embedding_function=embedding_fn,
            )
            logger.warning(
                "Dual write enabled but ChromaDB is missing. Writing to FAISS only."
            )

        # Text splitting
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
        )

        self.max_context_chunks = max_context_chunks
        self.subgoal_evidence_map: Dict[
            str, List[int]
        ] = {}  # Primarily tracks FAISS IDs if active

    def retrieve_from_chroma(
        self, query: str, top_k: int, query_embedding: List[float] | None = None
    ) -> List[Tuple[EvidenceChunk, float]]:
        """
        Retrieve relevant evidence from the Chroma vector store for a textual query.
        
        If a precomputed embedding is provided, it will be used instead of encoding the query.
        
        Parameters:
            query (str): Text query used to find relevant evidence.
            top_k (int): Maximum number of results to return.
            query_embedding (List[float] | None): Optional precomputed embedding for `query`; must match the embedding dimensionality used by the store.
        
        Returns:
            List[Tuple[EvidenceChunk, float]]: A list of (evidence, score) tuples ordered by the store's relevance ranking. `score` is a relevance/similarity value where larger indicates more relevant matches.
        
        Raises:
            ValueError: If the Chroma store is not enabled.
        """
        if not self.use_chroma:
            raise ValueError("Chroma not enabled")

        # ⚡ Bolt Optimization: Use pre-computed embedding if provided
        if query_embedding is not None:
            embedding = query_embedding
        else:
            embedding = self.embedder.encode(query).tolist()

        # Map ChromaEvidenceChunk back to EvidenceChunk
        results = self.chroma.retrieve(query, top_k=top_k, query_embedding=embedding)
        return [
            (
                EvidenceChunk(
                    content=c.content,
                    source_url=c.source_url,
                    subgoal_id=c.subgoal_id,
                    relevance_score=c.relevance_score,
                    timestamp=c.timestamp,
                    chunk_id=c.chunk_id,
                    metadata=c.metadata,
                ),
                score,
            )
            for c, score in results
        ]

    def ingest_research_results(
        self, documents: List[Dict], subgoal_id: str, metadata: Dict | None = None
    ) -> List[int]:
        """
        Ingests a list of web documents into the RAG stores by splitting each document into text chunks, encoding them in a single batch, and writing the resulting evidence into FAISS and/or Chroma according to the instance configuration.
        
        Each chunk receives a deterministic chunk_id (prefixed by the provided subgoal_id), associated metadata, a timestamp, and a relevance_score derived from the source document. The method updates the subgoal-to-evidence mapping for FAISS and performs batch inserts to the configured stores.
        
        Parameters:
            documents (List[Dict]): List of document objects; each document should contain at least a "content" string. Optional keys used: "url" and "score".
            subgoal_id (str): Identifier for the subgoal to which these evidence chunks belong.
            metadata (Dict | None): Optional metadata to attach to every ingested chunk.
        
        Returns:
            List[int]: List of integer IDs assigned to the ingested chunks in the FAISS store. Returns an empty list if no chunks were ingested into FAISS.
        """
        ingested_ids = []
        chroma_chunks = []
        embeddings_list = []
        chunks_to_process = []

        for doc in documents:
            content = doc.get("content", "")
            if not content:
                continue

            doc_chunks = self.splitter.split_text(content)

            for chunk in doc_chunks:
                # ⚡ Bolt Optimization: Prepare for batch processing
                chunks_to_process.append({"chunk": chunk, "doc": doc})

        # ⚡ Bolt Optimization: Batch Embedding
        # Call the model once for all chunks instead of N times (N=docs*chunks)
        if not chunks_to_process:
            return []

        texts = [c["chunk"] for c in chunks_to_process]
        embeddings = self.embedder.encode(texts)

        # Process embeddings and store
        current_time = time.time()

        faiss_embeddings = []
        faiss_ids = []
        start_id = self.next_id

        for i, item in enumerate(chunks_to_process):
            chunk = item["chunk"]
            doc = item["doc"]
            embedding = embeddings[i]
            # Use same UUID for both stores to maintain consistency
            chunk_id_str = f"{subgoal_id}_{uuid.uuid4()}"

            # FAISS Logic
            if self.use_faiss:
                current_id = start_id + i  # Incremental ID for FAISS

                evidence = EvidenceChunk(
                    content=chunk,
                    source_url=doc.get("url", "unknown"),
                    subgoal_id=subgoal_id,
                    relevance_score=doc.get("score", 0.0),
                    timestamp=current_time,
                    chunk_id=chunk_id_str,
                    metadata=metadata or {},
                )

                self.doc_store[current_id] = evidence
                ingested_ids.append(current_id)
                faiss_embeddings.append(embedding)
                faiss_ids.append(current_id)

                if subgoal_id not in self.subgoal_evidence_map:
                    self.subgoal_evidence_map[subgoal_id] = []
                self.subgoal_evidence_map[subgoal_id].append(current_id)

            # Chroma Logic
            if self.use_chroma and CHROMA_AVAILABLE:
                chroma_chunks.append(
                    ChromaEvidenceChunk(
                        content=chunk,
                        source_url=doc.get("url", "unknown"),
                        subgoal_id=subgoal_id,
                        relevance_score=doc.get("score", 0.0),
                        timestamp=current_time,
                        chunk_id=chunk_id_str,
                        metadata=metadata or {},
                    )
                )
                embeddings_list.append(embedding.tolist())

        # ⚡ Bolt Optimization: Batch FAISS Add
        if self.use_faiss and faiss_embeddings:
            self.index_with_ids.add_with_ids(
                np.array(faiss_embeddings, dtype=np.float32),
                np.array(faiss_ids, dtype=np.int64),
            )
            self.next_id += len(faiss_ids)

        # Batch insert to Chroma
        if self.use_chroma and chroma_chunks and CHROMA_AVAILABLE:
            self.chroma.add_evidence(chroma_chunks, embeddings=embeddings_list)

        return ingested_ids

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        subgoal_filter: str | None = None,
        min_score: float = 0.0,
        query_embedding: List[float] | None = None,
    ) -> List[Tuple[EvidenceChunk, float]]:
        """
        Retrieve evidence chunks relevant to the given query using the configured vector store.
        
        The method will prefer the configured read store (Chroma when selected and available) and fall back to the FAISS index when appropriate. Returned results are sorted by descending similarity.
        
        Parameters:
            query (str): The search query text.
            top_k (int): Maximum number of results to return.
            subgoal_filter (str | None): If provided, only return evidence whose subgoal_id equals this value.
            min_score (float): Minimum similarity score (0.0–1.0) required for an item to be included.
            query_embedding (List[float] | None): Precomputed embedding for `query`; used directly if provided.
        
        Returns:
            List[Tuple[EvidenceChunk, float]]: A list of (evidence_chunk, similarity) tuples sorted by similarity (highest first). The similarity is a float in the range [0.0, 1.0].
        """
        # Decide which store to read from
        read_source = self.config.rag_store

        if read_source == "chroma" and self.use_chroma and CHROMA_AVAILABLE:
            return self.retrieve_from_chroma(
                query, top_k, query_embedding=query_embedding
            )

        elif self.use_faiss:
            # Existing FAISS logic
            if self.index_with_ids.ntotal == 0:
                return []

            # ⚡ Bolt Optimization: Use pre-computed embedding if provided
            if query_embedding is not None:
                q_emb = np.array([query_embedding], dtype=np.float32)
            else:
                raw_emb = self.embedder.encode(query)
                q_emb = np.array([raw_emb], dtype=np.float32)

            k_search = min(top_k * 2, self.index_with_ids.ntotal)
            distances, indices = self.index_with_ids.search(q_emb, k=k_search)

            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx == -1 or idx not in self.doc_store:
                    continue
                evidence = self.doc_store[idx]
                similarity = 1 / (1 + dist)
                if subgoal_filter and evidence.subgoal_id != subgoal_filter:
                    continue
                if similarity < min_score:
                    continue
                results.append((evidence, similarity))

            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]

        return []

    def audit_and_prune(
        self,
        subgoal_id: str,
        relevance_threshold: float = 0.5,
        diversity_weight: float = 0.3,
    ) -> Dict:
        """
        Prune low-relevance evidence for a given subgoal using a soft-delete policy.
        
        Performs a relevance-based audit of evidence associated with subgoal_id and removes
        (lowers visibility of) items whose relevance score is below relevance_threshold.
        This routine applies to the FAISS-backed store; when FAISS is not enabled the
        operation is skipped.
        
        Parameters:
            subgoal_id (str): Identifier of the subgoal whose evidence should be audited.
            relevance_threshold (float): Minimum relevance score (0.0-1.0) required for an
                evidence item to be retained.
            diversity_weight (float): Weight intended for diversity scoring (present for API
                compatibility; not used by the current implementation).
        
        Returns:
            dict: A statistics/result object. On success contains:
                - status: "success"
                - original_count: int, number of evidence items before pruning
                - kept_count: int, number of items retained
                - pruned_count: int, number of items removed from the subgoal mapping
                - avg_score: float, average relevance score of retained items
            If skipped or no evidence, contains a status and a reason (e.g., "pruning_not_implemented_for_chroma"
            or "no_evidence").
        """
        if not self.use_faiss:
            return {"status": "skipped", "reason": "pruning_not_implemented_for_chroma"}

        # Existing FAISS pruning logic...
        if subgoal_id not in self.subgoal_evidence_map:
            return {"status": "no_evidence", "pruned": 0}

        evidence_ids = self.subgoal_evidence_map[subgoal_id]
        original_count = len(evidence_ids)
        scored_evidence = []
        for eid in evidence_ids:
            evidence = self.doc_store[eid]
            score = (
                float(evidence.relevance_score)
                if evidence.relevance_score is not None
                else 0.0
            )
            scored_evidence.append((eid, score, evidence))

        scored_evidence.sort(key=lambda x: x[1], reverse=True)
        kept_ids = []
        for eid, score, evidence in scored_evidence:
            if score >= relevance_threshold:
                kept_ids.append(eid)

        self.subgoal_evidence_map[subgoal_id] = kept_ids
        pruned_count = original_count - len(kept_ids)

        avg_score = 0.0
        if kept_ids:
            avg_score = float(
                np.mean([x[1] for x in scored_evidence if x[0] in kept_ids])
            )

        return {
            "status": "success",
            "original_count": original_count,
            "kept_count": len(kept_ids),
            "pruned_count": pruned_count,
            "avg_score": avg_score,
        }

    # ... keep existing methods (verify_subgoal_coverage, get_context_for_synthesis, export_state) ...
    def verify_subgoal_coverage(
        self,
        subgoal: str,
        subgoal_id: str,
        llm_client,
        confidence_threshold: float = 0.7,
    ) -> Dict:
        """
        Assess whether retrieved evidence sufficiently covers a research sub-goal by querying an LLM verifier.
        
        Parameters:
            subgoal (str): The research sub-goal to verify.
            subgoal_id (str): Identifier used to filter evidence relevant to the sub-goal.
            llm_client: LLM client or interface used by the internal LLM call function.
            confidence_threshold (float): Minimum confidence (0.0–1.0) considered sufficient for verification.
        
        Returns:
            dict: Verification result containing:
                - `verified` (bool): `true` if the evidence is judged to cover the sub-goal, `false` otherwise.
                - `confidence` (float): Confidence score between 0.0 and 1.0.
                - `reasoning` (str, optional): Explanatory text from the verifier when provided.
                - `evidence_count` (int): Number of evidence items evaluated.
                - `reason` (str, optional): Short machine-readable reason for failure (e.g., "no_evidence" or an error tag).
        """
        evidence_list = self.retrieve(query=subgoal, subgoal_filter=subgoal_id, top_k=5)
        if not evidence_list:
            return {"verified": False, "confidence": 0.0, "reason": "no_evidence"}

        combined_evidence = "\n\n".join(
            [
                f"[{i + 1}] {e.content[:200]}..."
                for i, (e, _) in enumerate(evidence_list)
            ]
        )

        verification_prompt = f"""
Verify if the following evidence adequately addresses the research sub-goal.

Sub-goal: {subgoal}

Evidence:
{combined_evidence}

Respond in JSON format:
{{
    "verified": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "explanation"
}}
"""
        import json

        try:
            response_text = call_llm_robust(llm_client, verification_prompt)

            response_text = response_text.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            result = json.loads(response_text)
            result["evidence_count"] = len(evidence_list)
            return result
        except Exception as e:
            return {
                "verified": False,
                "confidence": 0.0,
                "reason": f"verification_error: {str(e)}",
            }

    def get_context_for_synthesis(
        self, query: str, max_tokens: int = 4000, subgoal_ids: List[str] | None = None,
    ) -> str:
        """
        Assembles a deduplicated, relevance-ordered contextual string of evidence to provide as synthesis input.
        
        Retrieves relevant evidence chunks for the given query (optionally restricted to the supplied subgoal IDs), removes duplicate chunk contents, orders the remaining chunks by their relevance score (highest first), and concatenates them into a single context string. Each chunk is prefixed with a "[Source: URL]" header and chunks are separated by "\n---\n". The returned context is truncated to approximately max_tokens (enforced by a character cap of max_tokens * 4) to keep the payload within the requested size.
        
        Parameters:
            query (str): The text query used to retrieve relevant evidence.
            max_tokens (int): Target maximum tokens for the returned context; the function enforces an approximate character cap of max_tokens * 4.
            subgoal_ids (List[str] | None): Optional list of subgoal IDs to restrict retrieval to those subgoals; if omitted, evidence is retrieved across all subgoals.
        
        Returns:
            str: A concatenated, source-labeled context string composed of the highest-relevance, deduplicated evidence chunks, truncated to fit the token-based size limit.
        """
        all_chunks = []

        # ⚡ Bolt Optimization: Pre-compute query embedding once for all subgoals
        # This avoids re-encoding the same query N times (where N = len(subgoal_ids))
        query_embedding = None
        if self.embedder:
            try:
                raw_emb = self.embedder.encode(query)
                # Handle numpy array vs list
                if hasattr(raw_emb, "tolist"):
                    query_embedding = raw_emb.tolist()
                else:
                    query_embedding = raw_emb
            except Exception as e:
                logger.warning(f"Failed to pre-compute embedding: {e}")

        if subgoal_ids:
            for sg_id in subgoal_ids:
                chunks = self.retrieve(
                    query=query,
                    subgoal_filter=sg_id,
                    top_k=self.max_context_chunks,
                    query_embedding=query_embedding,
                )
                all_chunks.extend(chunks)
        else:
            all_chunks = self.retrieve(
                query=query,
                top_k=self.max_context_chunks,
                query_embedding=query_embedding,
            )

        seen_content = set()
        unique_chunks = []
        for chunk, score in all_chunks:
            if chunk.content not in seen_content:
                seen_content.add(chunk.content)
                unique_chunks.append((chunk, score))

        # ⚡ Bolt Optimization: Sort unique chunks by relevance score descending.
        # This ensures that when we truncate to max_tokens, we keep the highest quality evidence
        # regardless of which subgoal found it, rather than blindly preferring the first subgoal's results.
        unique_chunks.sort(key=lambda x: x[1], reverse=True)

        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4

        for chunk, score in unique_chunks:
            chunk_text = f"[Source: {chunk.source_url}]\n{chunk.content}\n"
            if total_chars + len(chunk_text) > max_chars:
                break
            context_parts.append(chunk_text)
            total_chars += len(chunk_text)

        return "\n---\n".join(context_parts)

    def export_state(self) -> Dict:
        """
        Export a summary of the RAG instance's current storage state.
        
        Returns:
            state (Dict): Dictionary with keys:
                - `doc_count` (int): Number of documents stored in the active vector store (FAISS or Chroma).
                - `subgoal_map` (Dict[str, int]): Mapping of subgoal_id to count of evidence items associated with that subgoal.
                - `next_id` (int): Next available numeric ID for FAISS entries (0 if not applicable).
        """
        count = 0
        if self.use_faiss:
            count = len(self.doc_store)
        elif self.use_chroma and CHROMA_AVAILABLE:
            count = self.chroma.count()

        return {
            "doc_count": count,
            "subgoal_map": {k: len(v) for k, v in self.subgoal_evidence_map.items()},
            "next_id": getattr(self, "next_id", 0),
        }


# Compatibility exports
class _RAGConfig:
    enabled = True
    enable_fallback = True
    max_documents = 5


rag_config = _RAGConfig()


def is_rag_enabled() -> bool:
    """
    Indicates whether the retrieval-augmented generation (RAG) system is enabled.
    
    Returns:
        `true` if RAG is enabled, `false` otherwise.
    """
    return True


class Resource:
    """Stub resource class for legacy compatibility."""



def create_rag_tool(resources):
    """
    Compatibility stub preserving the legacy create_rag_tool API while performing no operation.
    
    This function accepts a legacy `resources` argument, emits a warning, and returns None to maintain backward compatibility with callers that still invoke create_rag_tool.
    
    Parameters:
        resources: Legacy resources object or mapping expected by older callers; this parameter is unused.
    """
    logger.warning("Using legacy create_rag_tool stub")
    return None
