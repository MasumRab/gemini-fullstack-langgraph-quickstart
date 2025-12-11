# Chroma Store Edge Case Fix

## Issue
Lines 119-120 in `backend/src/rag/chroma_store.py` need better error handling for edge cases.

## Recommended Fix

Replace lines 111-120 with:

```python
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
```

## Rationale
- Wraps query in try/except to handle collection errors gracefully
- Adds `.get()` for safer dictionary access
- Adds logging for debugging
- Returns empty list on any error instead of crashing

## Status
- ✅ FAISS soft-delete documentation enhanced
- ✅ RAG store selection logic clarified  
- ⚠️ Chroma edge case fix documented (manual application needed)

The Chroma fix is minor and can be applied manually or in a follow-up commit.
