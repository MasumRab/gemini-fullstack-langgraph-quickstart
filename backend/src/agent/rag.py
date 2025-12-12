from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict
import numpy as np
import time
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging
import os

from config.app_config import config

# Optional imports for RAG dependencies
try:
    from sentence_transformers import SentenceTransformer
    import faiss
except ImportError:
    SentenceTransformer = None
    faiss = None

# Optional Chroma
try:
    from rag.chroma_store import ChromaStore, EvidenceChunk as ChromaEvidenceChunk
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
    """
    RAG system optimized for deep research workflows.
    Implements continuous evidence auditing and context pruning.
    Now supports hybrid store (FAISS + Chroma) with dual-write.
    """

    def __init__(
        self,
        config=None, # Allow injecting config
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        max_context_chunks: int = 10
    ):
        """
        Initialize a DeepSearchRAG instance and configure its embedding model, vector stores, and chunking behavior.
        
        Parameters:
            config (optional): Configuration object to control store selection, dual-write, and Chroma persistence; if omitted, the global app config is used.
            embedding_model (str): Name or path of the SentenceTransformer model used to produce embeddings.
            chunk_size (int): Maximum number of characters per text chunk produced by the internal splitter.
            chunk_overlap (int): Number of overlapping characters between consecutive chunks.
            max_context_chunks (int): Maximum number of chunks returned per subgoal when assembling context for synthesis.
        
        Notes:
            - The constructor loads the embedding model and initializes selected stores (FAISS and/or Chroma) according to the provided configuration.
            - When dual-write is enabled, both FAISS and Chroma are used (subject to availability) to persist ingested evidence.
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
        self.use_chroma = (requested_store == "chroma" or self.config.dual_write) and CHROMA_AVAILABLE

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
            persist_path = getattr(self.config, 'chroma_persist_path', "./chroma_db")

            # Create wrapper for consistent embeddings between FAISS and Chroma
            embedding_fn = None
            if self.embedder:
                class ConsistentEmbeddingFunction:
                    def __init__(self, model):
                        """
                        Initialize the instance with the provided model used for inference and embedding operations.
                        
                        Parameters:
                            model: The model instance used for generating embeddings or running inference (for example, an LLM or embedding model).
                        """
                        self.model = model
                    def __call__(self, input):
                        # Ensure input is list of strings
                        """
                        Convert one or more input texts into embedding vectors using the underlying model.
                        
                        Parameters:
                            input (str | list[str]): A single text or a list of texts to be embedded.
                        
                        Returns:
                            list[list[float]]: A list of embedding vectors; each embedding is a list of floats corresponding to an input text.
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
                embedding_function=embedding_fn
            )
            logger.warning("Dual write enabled but ChromaDB is missing. Writing to FAISS only.")

        # Text splitting
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )

        self.max_context_chunks = max_context_chunks
        self.subgoal_evidence_map: Dict[str, List[int]] = {} # Primarily tracks FAISS IDs if active

    def retrieve_from_chroma(self, query: str, top_k: int) -> List[Tuple[EvidenceChunk, float]]:
        """
        Retrieve matching evidence chunks from the Chroma vector store for the provided query.
        
        Results are returned as EvidenceChunk objects paired with a numeric similarity score (higher is more similar).
        
        Returns:
            List[Tuple[EvidenceChunk, float]]: A list of tuples where each tuple contains an EvidenceChunk and its similarity score.
        
        Raises:
            ValueError: If Chroma is not enabled for this instance.
        """
        if not self.use_chroma:
            raise ValueError("Chroma not enabled")
        embedding = self.embedder.encode(query).tolist()

        # Map ChromaEvidenceChunk back to EvidenceChunk
        results = self.chroma.retrieve(query, top_k=top_k, query_embedding=embedding)
        return [
            (EvidenceChunk(
                content=c.content,
                source_url=c.source_url,
                subgoal_id=c.subgoal_id,
                relevance_score=c.relevance_score,
                timestamp=c.timestamp,
                chunk_id=c.chunk_id,
                metadata=c.metadata
            ), score)
            for c, score in results
        ]

    def ingest_research_results(
        self,
        documents: List[Dict],
        subgoal_id: str,
        metadata: Optional[Dict] = None
    ) -> List[int]:
        """
        Ingests a list of documents by chunking and embedding their content, storing chunks into the configured vector stores.
        
        Parameters:
            documents (List[Dict]): Documents to ingest; each dict may include "content", "url", and "score".
            subgoal_id (str): Identifier for the subgoal associated with these documents; used to tag each chunk.
            metadata (Optional[Dict]): Optional metadata to attach to every ingested chunk.
        
        Returns:
            ingested_ids (List[int]): List of internal FAISS IDs assigned to the ingested chunks (empty if FAISS is disabled or no content was ingested).
        """
        ingested_ids = []
        chroma_chunks = []
        embeddings_list = []

        for doc in documents:
            content = doc.get("content", "")
            if not content:
                continue

            chunks = self.splitter.split_text(content)

            for i, chunk in enumerate(chunks):
                # Common data
                chunk_timestamp = time.time()
                chunk_id_str = f"{subgoal_id}_{int(chunk_timestamp * 1000)}_{i}"
                embedding = self.embedder.encode(chunk)

                # FAISS Logic
                if self.use_faiss:
                    evidence = EvidenceChunk(
                        content=chunk,
                        source_url=doc.get("url", "unknown"),
                        subgoal_id=subgoal_id,
                        relevance_score=doc.get("score", 0.0),
                        timestamp=chunk_timestamp,
                        chunk_id=chunk_id_str,
                        metadata=metadata or {}
                    )

                    self.index_with_ids.add_with_ids(
                        np.array([embedding], dtype=np.float32),
                        np.array([self.next_id])
                    )
                    self.doc_store[self.next_id] = evidence
                    ingested_ids.append(self.next_id)

                    if subgoal_id not in self.subgoal_evidence_map:
                        self.subgoal_evidence_map[subgoal_id] = []
                    self.subgoal_evidence_map[subgoal_id].append(self.next_id)

                    self.next_id += 1

                # Chroma Logic (Buffer for batch insert)
                if self.use_chroma and CHROMA_AVAILABLE:
                    chroma_chunks.append(ChromaEvidenceChunk(
                        content=chunk,
                        source_url=doc.get("url", "unknown"),
                        subgoal_id=subgoal_id,
                        relevance_score=doc.get("score", 0.0),
                        timestamp=chunk_timestamp,
                        chunk_id=chunk_id_str,
                        metadata=metadata or {}
                    ))
                    embeddings_list.append(embedding.tolist())

        # Batch insert to Chroma
        if self.use_chroma and chroma_chunks and CHROMA_AVAILABLE:
            self.chroma.add_evidence(chroma_chunks, embeddings=embeddings_list)

        return ingested_ids

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        subgoal_filter: Optional[str] = None,
        min_score: float = 0.0
    ) -> List[Tuple[EvidenceChunk, float]]:
        """
        Retrieve the most relevant evidence for a query from the configured store.
        
        This selects the read source according to the RAG configuration (Chroma when configured and available; otherwise FAISS), applies an optional subgoal filter and minimum similarity threshold, sorts results by similarity descending, and returns up to `top_k` items.
        
        Parameters:
        	query (str): The natural-language query used to find relevant evidence.
        	top_k (int): Maximum number of evidence items to return.
        	subgoal_filter (Optional[str]): If provided, restrict results to evidence for this subgoal ID.
        	min_score (float): Minimum similarity score (0 to 1) required for returned items.
        
        Returns:
        	results (List[Tuple[EvidenceChunk, float]]): A list of tuples containing an EvidenceChunk and its similarity score (higher is more similar), sorted by score in descending order and limited to `top_k`.
        """
        # Decide which store to read from
        read_source = self.config.rag_store

        if read_source == "chroma" and self.use_chroma and CHROMA_AVAILABLE:
            return self.retrieve_from_chroma(query, top_k)

        elif self.use_faiss:
            # Existing FAISS logic
            if self.index_with_ids.ntotal == 0:
                return []

            query_embedding = self.embedder.encode(query)
            k_search = min(top_k * 2, self.index_with_ids.ntotal)
            distances, indices = self.index_with_ids.search(
                np.array([query_embedding], dtype=np.float32),
                k=k_search
            )

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

    def audit_and_prune(self, subgoal_id: str, relevance_threshold: float = 0.5, diversity_weight: float = 0.3) -> Dict:
        """
        Audit evidence for a subgoal and remove low-relevance items from future retrievals (soft-delete).
        
        Parameters:
            subgoal_id (str): Identifier of the subgoal to audit.
            relevance_threshold (float): Minimum relevance score (0.0–1.0) required for an evidence item to be kept.
            diversity_weight (float): Weight to influence selection by diversity (currently unused).
        
        Returns:
            dict: Pruning result with keys:
                - status (str): "success", "skipped" (when FAISS not used), or "no_evidence".
                - original_count (int): Number of evidence items before pruning (present when status == "success").
                - kept_count (int): Number of items retained (present when status == "success").
                - pruned_count (int): Number of items removed from the subgoal mapping (present when status == "success").
                - avg_score (float): Average relevance score of kept items (0.0 if none kept; present when status == "success").
                - reason (str): Explanation when status == "skipped".
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
            score = float(evidence.relevance_score) if evidence.relevance_score is not None else 0.0
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
             avg_score = float(np.mean([x[1] for x in scored_evidence if x[0] in kept_ids]))

        return {
            "status": "success",
            "original_count": original_count,
            "kept_count": len(kept_ids),
            "pruned_count": pruned_count,
            "avg_score": avg_score
        }

    # ... keep existing methods (verify_subgoal_coverage, get_context_for_synthesis, export_state) ...
    def verify_subgoal_coverage(self, subgoal: str, subgoal_id: str, llm_client, confidence_threshold: float = 0.7) -> Dict:
        """
        Check whether stored evidence sufficiently addresses a research sub-goal by asking an LLM to verify and return a structured assessment.
        
        Parameters:
            subgoal (str): The textual formulation of the research sub-goal to verify.
            subgoal_id (str): Identifier used to filter evidence associated with the sub-goal.
            llm_client: LLM client object used to evaluate evidence. Must implement either `invoke(prompt)` (returning an object with `.content`) or `generate(prompt)` (returning a string).
            confidence_threshold (float): Threshold between 0.0 and 1.0 used by callers to interpret returned confidence (not enforced inside this method).
        
        Returns:
            result (dict): Parsed JSON-like dictionary produced by the LLM augmented with:
                - "verified" (bool): Whether the evidence is judged to address the sub-goal.
                - "confidence" (float): Confidence score between 0.0 and 1.0.
                - "reasoning" (str): Explanatory text from the LLM.
                - "evidence_count" (int): Number of evidence items considered.
              On failure returns a dict with "verified": False, "confidence": 0.0 and a "reason" explaining the failure, e.g. "no_evidence" or "verification_error: <msg>".
        """
        evidence_list = self.retrieve(query=subgoal, subgoal_filter=subgoal_id, top_k=5)
        if not evidence_list:
            return {"verified": False, "confidence": 0.0, "reason": "no_evidence"}

        combined_evidence = "\n\n".join([f"[{i+1}] {e.content[:200]}..." for i, (e, _) in enumerate(evidence_list)])

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
            if hasattr(llm_client, "invoke"):
                 response = llm_client.invoke(verification_prompt)
                 response_text = response.content if hasattr(response, "content") else str(response)
            elif hasattr(llm_client, "generate"):
                response_text = llm_client.generate(verification_prompt)
            else:
                raise ValueError("Unknown LLM client interface")

            response_text = response_text.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                 response_text = response_text.split("```")[1].split("```")[0]

            result = json.loads(response_text)
            result["evidence_count"] = len(evidence_list)
            return result
        except Exception as e:
            return {"verified": False, "confidence": 0.0, "reason": f"verification_error: {str(e)}"}

    def get_context_for_synthesis(self, query: str, max_tokens: int = 4000, subgoal_ids: Optional[List[str]] = None) -> str:
        """
        Assembles a deduplicated, token‑bounded contextual text for synthesis from retrieved evidence chunks.
        
        Retrieves relevant evidence chunks (optionally limited to provided subgoal IDs), removes duplicate chunk contents, and concatenates chunk texts prefixed with their source. The function enforces a simple token budget by approximating one token as four characters and stops adding chunks once the budget would be exceeded. Chunks are separated by "\n---\n" in the returned context.
        
        Parameters:
            query (str): Query string used to retrieve relevant evidence chunks.
            max_tokens (int): Maximum token budget for the returned context (approximate; one token ≈ four characters). Defaults to 4000.
            subgoal_ids (Optional[List[str]]): If provided, restrict retrieval to these subgoal IDs; otherwise retrieve across all subgoals.
        
        Returns:
            str: Concatenated, deduplicated chunk contexts (each prefixed with "[Source: <url>]") separated by "\n---\n", truncated to fit within the approximate token budget.
        """
        all_chunks = []
        if subgoal_ids:
            for sg_id in subgoal_ids:
                chunks = self.retrieve(query=query, subgoal_filter=sg_id, top_k=self.max_context_chunks)
                all_chunks.extend(chunks)
        else:
            all_chunks = self.retrieve(query=query, top_k=self.max_context_chunks)

        seen_content = set()
        unique_chunks = []
        for chunk, score in all_chunks:
            if chunk.content not in seen_content:
                seen_content.add(chunk.content)
                unique_chunks.append((chunk, score))

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
        Export a snapshot of the RAG storage state.
        
        The returned dictionary includes the total number of stored documents (based on the active store), a mapping of subgoal IDs to their counts of associated evidence entries, and the next internal ID to be assigned.
        
        Returns:
            state (Dict): {
                "doc_count": int,       # total documents managed by the active store
                "subgoal_map": Dict[str, int],  # subgoal_id -> number of evidence items
                "next_id": int          # next internal identifier (0 if not present)
            }
        """
        count = 0
        if self.use_faiss:
            count = len(self.doc_store)
        elif self.use_chroma and CHROMA_AVAILABLE:
            count = self.chroma.count()

        return {
            "doc_count": count,
            "subgoal_map": {k: len(v) for k, v in self.subgoal_evidence_map.items()},
            "next_id": getattr(self, "next_id", 0)
        }

# Compatibility exports
class _RAGConfig:
    enabled = True
    enable_fallback = True
    max_documents = 5

rag_config = _RAGConfig()

def is_rag_enabled() -> bool:
    return True

class Resource:
    pass

def create_rag_tool(resources):
    """
    Legacy factory placeholder for creating a RAG tool retained for backward compatibility.
    
    Parameters:
        resources: Legacy resources or dependency container passed by callers; this function ignores it.
    
    Returns:
        None: No tool is created.
    """
    logger.warning("Using legacy create_rag_tool stub")
    return None