# PR Review Issues - Action Plan

**Generated:** 2025-12-11 15:30 AEDT

## PR #16: Hybrid Search, RAG Dual-Write, and Enhanced Validation

### Critical Issues to Address

#### 1. **FAISS Pruning - Soft Delete Pattern** (HIGH PRIORITY)
**File:** `backend/src/agent/rag.py` (lines 262-271)

**Issue:**
- Pruning updates `subgoal_evidence_map` but doesn't remove from `doc_store` or FAISS index
- Memory not reclaimed, index continues to grow
- Unclear if intentional (soft-delete) or bug

**Action Required:**
```python
# Add documentation comment explaining soft-delete pattern
# OR implement actual deletion:
# - Remove from doc_store
# - Rebuild FAISS index without pruned items
```

**Decision Needed:** Is this intentional soft-delete or should we implement hard delete?

---

#### 2. **Chroma Store Edge Case Handling** (MEDIUM PRIORITY)
**File:** `backend/src/rag/chroma_store.py` (lines 107-116)

**Issue:**
- Empty `where_filter` passed correctly as `None`
- But error handling relies on checking `results["ids"]`
- Could fail if collection is empty or query fails

**Action Required:**
```python
# Add defensive error handling:
try:
    results = collection.query(...)
    if not results or not results.get("ids"):
        return []  # Handle empty collection gracefully
except Exception as e:
    logger.error(f"Chroma query failed: {e}")
    return []
```

---

#### 3. **RAG Store Selection Logic** (LOW PRIORITY - DOCUMENTATION)
**File:** `backend/src/agent/rag.py` (lines 67-74)

**Issue:**
- `config.dual_write` enables both stores
- Might be confusing since `use_faiss` and `use_chroma` are independent flags
- Logic is correct but could be clearer

**Action Required:**
```python
# Add clarifying comment:
# When dual_write is enabled, both FAISS and Chroma are used
# independently of use_faiss/use_chroma flags for redundancy
```

---

### Linting Issues (Code Quality)

#### Files with Linting Warnings:

**backend/src/agent/nodes.py:**
- F841: Unused variables (`snippet`, `configurable`)
- F541: f-string without placeholders
- D205/D212: Docstring formatting

**backend/src/agent/kg.py:**
- D100: Missing module docstring
- E402: Module imports not at top
- F811: Redefinition of unused variables
- D103/D212: Docstring issues

**backend/src/config/app_config.py:**
- F401: Unused imports
- D100: Missing module docstring

**backend/src/rag/chroma_store.py:**
- D100: Missing module docstring
- D103: Missing function docstrings

---

## PR #19: MCP Persistence Wrapper

### Status
**No critical issues found** - Only Jules AI bot comment, no human reviews

### Potential Issues to Check:
1. Merge conflicts with current main (6 files expected)
2. Test coverage for new MCP wrapper
3. Integration with existing persistence layer

---

## Recommended Approach

### Phase 1: Address PR #16 Critical Issues

**Step 1: Checkout PR branch**
```bash
git fetch origin
git checkout -b fix/pr16-issues origin/feature/search-rag-hybrid-3228504735555579147
```

**Step 2: Fix FAISS Pruning**
- Add documentation OR implement hard delete
- Commit: "docs: clarify FAISS soft-delete pattern" OR "fix: implement hard delete for pruned FAISS entries"

**Step 3: Fix Chroma Edge Cases**
- Add defensive error handling
- Commit: "fix: add edge case handling for empty Chroma collections"

**Step 4: Clean up linting**
- Remove unused variables
- Fix docstrings
- Commit: "style: fix linting issues in nodes.py, kg.py, rag modules"

**Step 5: Test and push**
```bash
# Run tests
cd backend
pytest

# Push fixes
git push origin fix/pr16-issues

# Update PR #16 to point to fix branch
```

### Phase 2: Merge PR #19 (MCP Persistence)

**Step 1: Create merge branch**
```bash
git checkout main
git checkout -b merge/pr19-mcp-persistence
git merge origin/jules-mcp-persistence-wrapper-2114800518725581450
```

**Step 2: Resolve conflicts** (6 files expected)

**Step 3: Test and merge**

### Phase 3: Merge Fixed PR #16

**After PR #19 is merged:**
```bash
git checkout main
git merge fix/pr16-issues
```

---

## Files Requiring Changes

### PR #16 Fixes:

1. **backend/src/agent/rag.py**
   - Lines 67-74: Add clarifying comment
   - Lines 262-271: Fix pruning logic or add documentation

2. **backend/src/rag/chroma_store.py**
   - Lines 107-116: Add edge case handling

3. **backend/src/agent/nodes.py**
   - Remove unused variables
   - Fix f-string issues
   - Fix docstring formatting

4. **backend/src/agent/kg.py**
   - Add module docstring
   - Move imports to top
   - Fix variable redefinitions
   - Fix docstrings

5. **backend/src/config/app_config.py**
   - Remove unused imports
   - Add module docstring

---

## Decision Points

### For FAISS Pruning:

**Option A: Document Soft-Delete (Quick)**
- Add comment explaining intentional behavior
- No code changes
- Memory continues to grow (acceptable for short sessions)

**Option B: Implement Hard Delete (Proper)**
- Remove from `doc_store`
- Rebuild FAISS index
- Reclaim memory
- More complex, needs testing

**Recommendation:** Start with Option A (document), implement Option B if memory becomes an issue

---

## Testing Checklist

- [ ] FAISS pruning works correctly (soft or hard delete)
- [ ] Chroma handles empty collections gracefully
- [ ] All linting issues resolved
- [ ] Backend tests pass
- [ ] Frontend tests pass
- [ ] Integration tests pass
- [ ] No new conflicts with main

---

## Timeline Estimate

**PR #16 Fixes:** 2-3 hours
- Critical fixes: 1 hour
- Linting cleanup: 1 hour
- Testing: 1 hour

**PR #19 Merge:** 1-2 hours
- Conflict resolution: 1 hour
- Testing: 1 hour

**Total:** 3-5 hours for both PRs
