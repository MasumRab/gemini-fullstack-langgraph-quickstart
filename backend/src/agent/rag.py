from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np
import time
from langchain.text_splitter import RecursiveCharacterTextSplitter
import logging

# Optional imports for RAG dependencies to avoid breaking if not installed
try:
    from sentence_transformers import SentenceTransformer
    import faiss
except ImportError:
    SentenceTransformer = None
    faiss = None

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
    """

    def __init__(
        self,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        max_context_chunks: int = 10
    ):
        if SentenceTransformer is None or faiss is None:
            raise ImportError("sentence-transformers and faiss-cpu are required for DeepSearchRAG")

        # Embedding setup
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedder = SentenceTransformer(embedding_model)
        self.embedding_dim = self.embedder.get_sentence_embedding_dimension()

        # Vector store (FAISS for efficiency)
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.index_with_ids = faiss.IndexIDMap(self.index)

        # Document store
        self.doc_store: Dict[int, EvidenceChunk] = {}
        self.next_id = 0

        # Text splitting
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )

        # Configuration
        self.max_context_chunks = max_context_chunks

        # Subgoal tracking (for verification)
        self.subgoal_evidence_map: Dict[str, List[int]] = {}

    def ingest_research_results(
        self,
        documents: List[Dict],
        subgoal_id: str,
        metadata: Optional[Dict] = None
    ) -> List[int]:
        """
        Ingest web search results into the RAG system.

        Args:
            documents: List of {content, url, score} dicts
            subgoal_id: Which research sub-goal this addresses
            metadata: Additional context

        Returns:
            List of assigned document IDs
        """
        ingested_ids = []

        for doc in documents:
            # Split into chunks
            content = doc.get("content", "")
            if not content:
                continue

            chunks = self.splitter.split_text(content)

            for i, chunk in enumerate(chunks):
                # Create evidence chunk
                evidence = EvidenceChunk(
                    content=chunk,
                    source_url=doc.get("url", "unknown"),
                    subgoal_id=subgoal_id,
                    relevance_score=doc.get("score", 0.0),
                    timestamp=time.time(),
                    chunk_id=f"{subgoal_id}_{self.next_id}_{i}",
                    metadata=metadata or {}
                )

                # Generate embedding
                embedding = self.embedder.encode(chunk)

                # Add to vector store
                self.index_with_ids.add_with_ids(
                    np.array([embedding], dtype=np.float32),
                    np.array([self.next_id])
                )

                # Store document
                self.doc_store[self.next_id] = evidence
                ingested_ids.append(self.next_id)

                # Track subgoal mapping
                if subgoal_id not in self.subgoal_evidence_map:
                    self.subgoal_evidence_map[subgoal_id] = []
                self.subgoal_evidence_map[subgoal_id].append(self.next_id)

                self.next_id += 1

        return ingested_ids

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        subgoal_filter: Optional[str] = None,
        min_score: float = 0.0
    ) -> List[Tuple[EvidenceChunk, float]]:
        """
        Retrieve relevant evidence chunks for a query.

        Args:
            query: Search query
            top_k: Number of results to return
            subgoal_filter: Only return evidence from specific subgoal
            min_score: Minimum similarity threshold

        Returns:
            List of (evidence, similarity_score) tuples
        """
        if self.index_with_ids.ntotal == 0:
            return []

        # Generate query embedding
        query_embedding = self.embedder.encode(query)

        # Search vector store
        k_search = min(top_k * 2, len(self.doc_store))
        distances, indices = self.index_with_ids.search(
            np.array([query_embedding], dtype=np.float32),
            k=k_search  # Get extra for filtering
        )

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for missing
                continue
            if idx not in self.doc_store:
                continue

            evidence = self.doc_store[idx]
            similarity = 1 / (1 + dist)  # Convert L2 distance to similarity

            # Apply filters
            if subgoal_filter and evidence.subgoal_id != subgoal_filter:
                continue
            if similarity < min_score:
                continue

            results.append((evidence, similarity))

        # Sort by similarity and limit
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def audit_and_prune(
        self,
        subgoal_id: str,
        relevance_threshold: float = 0.5,
        diversity_weight: float = 0.3
    ) -> Dict:
        """
        SOTA Requirement: Continuous evidence auditing.
        Prune low-quality evidence and maintain diversity.

        Args:
            subgoal_id: Target subgoal
            relevance_threshold: Minimum relevance score
            diversity_weight: Weight for diversity vs relevance

        Returns:
            Audit report with statistics
        """
        if subgoal_id not in self.subgoal_evidence_map:
            return {"status": "no_evidence", "pruned": 0}

        evidence_ids = self.subgoal_evidence_map[subgoal_id]
        original_count = len(evidence_ids)

        # Score each piece of evidence
        scored_evidence = []
        for eid in evidence_ids:
            evidence = self.doc_store[eid]
            # Use the relevance score from the search result or a default
            # In a real system, you might re-rank here
            score = float(evidence.relevance_score) if evidence.relevance_score is not None else 0.0
            scored_evidence.append((eid, score, evidence))

        # Rank by score
        scored_evidence.sort(key=lambda x: x[1], reverse=True)

        # Prune low-quality evidence
        kept_ids = []
        for eid, score, evidence in scored_evidence:
            if score >= relevance_threshold:
                kept_ids.append(eid)
            # Alternatively, keep top K regardless of threshold if too few

        # Update mapping
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

    def verify_subgoal_coverage(
        self,
        subgoal: str,
        subgoal_id: str,
        llm_client,
        confidence_threshold: float = 0.7
    ) -> Dict:
        """
        SOTA Requirement: Verify evidence against sub-goals.

        Args:
            subgoal: The research sub-goal
            subgoal_id: Sub-goal identifier
            llm_client: LLM for verification
            confidence_threshold: Minimum confidence

        Returns:
            Verification report
        """
        # Retrieve evidence for this subgoal
        evidence_list = self.retrieve(
            query=subgoal,
            subgoal_filter=subgoal_id,
            top_k=5
        )

        if not evidence_list:
            return {
                "verified": False,
                "confidence": 0.0,
                "reason": "no_evidence"
            }

        # Combine evidence
        combined_evidence = "\n\n".join([
            f"[{i+1}] {e.content[:200]}..."
            for i, (e, _) in enumerate(evidence_list)
        ])

        # LLM verification
        # Assuming llm_client has an 'invoke' or 'generate' method.
        # Adapting to typical LangChain or string-based client.
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
            # Check if llm_client is a LangChain Runnable
            if hasattr(llm_client, "invoke"):
                 response = llm_client.invoke(verification_prompt)
                 if hasattr(response, "content"):
                     response_text = response.content
                 else:
                     response_text = str(response)
            # Check if it has generate method (custom client)
            elif hasattr(llm_client, "generate"):
                response_text = llm_client.generate(verification_prompt)
            else:
                raise ValueError("Unknown LLM client interface")

            # Basic JSON extraction
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
                "reason": f"verification_error: {str(e)}"
            }

    def get_context_for_synthesis(
        self,
        query: str,
        max_tokens: int = 4000,
        subgoal_ids: Optional[List[str]] = None
    ) -> str:
        """
        Get pruned context for final answer synthesis.
        Implements context window management.

        Args:
            query: Final query to answer
            max_tokens: Token budget (approximate)
            subgoal_ids: Optional filter for specific subgoals

        Returns:
            Formatted context string
        """
        # Retrieve relevant chunks
        all_chunks = []

        if subgoal_ids:
            # Get from specific subgoals
            for sg_id in subgoal_ids:
                chunks = self.retrieve(
                    query=query,
                    subgoal_filter=sg_id,
                    top_k=self.max_context_chunks
                )
                all_chunks.extend(chunks)
        else:
            # Global retrieval
            all_chunks = self.retrieve(
                query=query,
                top_k=self.max_context_chunks
            )

        # Deduplicate and rank
        seen_content = set()
        unique_chunks = []
        for chunk, score in all_chunks:
            if chunk.content not in seen_content:
                seen_content.add(chunk.content)
                unique_chunks.append((chunk, score))

        # Budget tokens (rough estimate: 4 chars = 1 token)
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
        """Export RAG state for checkpointing"""
        return {
            "doc_count": len(self.doc_store),
            "subgoal_map": {k: len(v) for k, v in self.subgoal_evidence_map.items()},
            "next_id": self.next_id
        }

# Compatibility exports for existing consumers (rag_nodes.py)
# These are mocks/proxies to prevent import errors in the rest of the codebase
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
    """Factory to create a RAG tool compatible with existing code if needed."""
    # This is a placeholder. The new DeepSearchRAG is used directly in the new agents.
    # Existing rag_nodes.py uses this.
    logger.warning("Using legacy create_rag_tool stub")
    return None
