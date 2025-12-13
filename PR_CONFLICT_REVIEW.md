# Open PR Conflict Review

> **Generated**: 2025-12-12T05:16:00+11:00  
> **Purpose**: Document conflicts and issues in open PRs before merge

---

## Summary

| PR | Title | Status | Critical Issues |
|----|-------|--------|-----------------|
| #16 | Hybrid Search, RAG Dual-Write, Validation | MERGEABLE | ⚠️ **DELETES 823 lines of valuable code** |
| #19 | MCP Persistence Wrapper | UNKNOWN | ⚠️ Merge status unknown, needs rebase |
| #23 | Add docstrings (CodeRabbit) | MERGEABLE | ✅ Low risk - docstrings only |
| #24 | SOTA Deep Research Alignment | MERGEABLE | ✅ Docs only - safe |
| #25 | Search Tool Comparison | MERGEABLE | ✅ Additive - safe |

---

## PR #16 - CRITICAL REVIEW REQUIRED

### Files Being Deleted (UNINTENDED?)

The following files exist on `main` and would be **deleted** if PR #16 is merged:

| File | Lines | Purpose |
|------|-------|---------|
| `backend/src/agent/orchestration.py` | 484 | ToolRegistry, AgentPool, Coordinator-based orchestration |
| `backend/src/agent/graph_builder.py` | 241 | Dynamic graph composition with optional enrichments |
| `backend/src/agent/graphs/planning.py` | 56 | Planning graph variant |
| `backend/src/agent/graphs/upstream.py` | 42 | Minimal upstream graph variant |
| `backend/tests/test_graph_mock.py` | 121 | Graph mock tests |
| `backend/tests/test_nodes.py` | 737 | Comprehensive node tests |

**Total: 1,681 lines of code would be lost**

### Recommended Action for PR #16

1. **Rebase on main** to pick up orchestration layer additions
2. **Restore deleted files** that were added to main after PR branch creation
3. **Keep the valid updates**: hybrid search, RAG improvements, validation enhancements

### Valid Changes to Keep from PR #16

- `backend/src/agent/_graph.py` (+425 lines) - Alternative graph implementation
- `docs/tasks/upstream_compatibility.md` (+62 lines) - Documentation
- RAG and search improvements in existing files
- Frontend InputForm.tsx improvements

---

## PR #19 - MCP Persistence Wrapper

### Status: UNKNOWN (needs rebase)

This PR has merge status `UNKNOWN`, indicating it needs to be rebased on the current main branch.

### Files Modified

- `backend/src/agent/mcp_*.py` - MCP configuration and persistence
- `backend/src/agent/nodes.py` - Node updates
- `backend/src/agent/rag.py` - RAG enhancements
- `backend/tests/test_*.py` - Test updates

### Recommended Action

1. Rebase on current main
2. Resolve any conflicts with recent main changes
3. Ensure MCP persistence doesn't conflict with orchestration layer

---

## PR #23 - CodeRabbit Docstrings

### Status: MERGEABLE ✅

Low-risk PR that only adds docstrings. Safe to merge.

---

## PR #24 - SOTA Deep Research Alignment

### Status: MERGEABLE ✅

Documentation-only PR. Adds research landscape docs and task files. Safe to merge.

---

## PR #25 - Search Tool Comparison

### Status: MERGEABLE ✅

Additive changes only:
- New `bing_adapter.py` and `tavily_adapter.py`
- New comparison notebook
- Router updates

Safe to merge - no deletions or conflicts.

---

## Merge Order Recommendation

1. **PR #25** - Search Tool Comparison (clean, additive)
2. **PR #24** - SOTA Documentation (docs only)
3. **PR #23** - Docstrings (safe)
4. **PR #19** - After rebase and conflict resolution
5. **PR #16** - **ONLY after restoring deleted files**

---

## Action Items

- [ ] Comment on PR #16 about deleted file issue
- [ ] Request PR #19 rebase
- [ ] Merge safe PRs (#23, #24, #25) 
- [ ] After safe merges, re-evaluate #16 and #19
