# Merge-Tree Analysis: PR Branches vs Main

**Generated:** 2025-12-11 14:21 AEDT
**Base Branch:** `main` (commit: 11d1042)

---

## PR #19: MCP Persistence Wrapper

**Branch:** `origin/jules-mcp-persistence-wrapper-2114800518725581450`
**Commits ahead of main:** 3

### Commit History
```
* 641785b Merge origin/main and Resolve Conflicts
* 99c4fc4 Merge branch 'main' into jules-mcp-persistence-wrapper-2114800518725581450
* 64900ff feat: Wrap persistence.py with MCP adapter
```

### Merge Analysis

**Merge Status:** ⚠️ **CONFLICTS DETECTED**

**Conflicting Files:**
1. `ROADMAP.md` - Content conflict
2. `backend/src/agent/graph.py` - Content conflict
3. `backend/src/agent/mcp_config.py` - Add/add conflict
4. `backend/src/agent/tools_and_schemas.py` - Content conflict
5. `backend/tests/test_registry.py` - Add/add conflict
6. `docs/tasks/01_MCP_TASKS.md` - Content conflict

### File Changes Summary
```
 ROADMAP.md                                  |   4 +-
 STATUS.md                                   |  37 ++
 backend/src/agent/app.py                    |   6 -
 backend/src/agent/graph.py                  |   6 +-
 backend/src/agent/mcp_config.py             |  70 ++-
 backend/src/agent/mcp_persistence.py        |  38 ++    [NEW FILE]
 backend/src/agent/tools_and_schemas.py      |  16 +-
 backend/src/debug_mcp_2.py                  |   7 +
 backend/src/tests/test_mcp_wrapper.py       |  46 ++
 backend/tests/test_graph_mock.py            | 121 +++++
 backend/tests/test_nodes.py                 | 737 ++++++++++++++++++++++++++++
 backend/tests/test_observability.py         | 101 ++++
 backend/tests/test_registry.py              | 551 +++++++++++++++------
 backend/tests/test_utils_hypothesis.py      |   4 +-
 docs/tasks/01_MCP_TASKS.md                  |  10 +-
 examples/open_deep_research_example         |   1 -
 examples/thinkdepthai_deep_research_example |   1 -

 18 files changed, 1580 insertions(+), 190 deletions(-)
```

### Key Changes

**New Files:**
- `backend/src/agent/mcp_persistence.py` - MCP wrapper for persistence layer
  - Wraps `load_plan()` and `save_plan()` as MCP tools
  - Uses FastMCP server
  - Provides `load_thread_plan()` and `save_thread_plan()` tools

**Modified Files:**
- `backend/src/agent/mcp_config.py` - Extended MCP configuration
- `backend/tests/test_registry.py` - Extensive test additions
- `backend/tests/test_nodes.py` - 737 new lines of tests
- `backend/tests/test_observability.py` - New observability tests
- `backend/tests/test_graph_mock.py` - New graph mocking tests

**Deletions:**
- Removed example submodules (open_deep_research, thinkdepthai)

### Conflict Analysis

**High Priority Conflicts:**
1. **`backend/src/agent/graph.py`** - Core graph implementation
   - Main has recent changes from 18 merged branches
   - PR has MCP integration changes
   - Resolution: Need to carefully merge both sets of changes

2. **`backend/tests/test_registry.py`** - Add/add conflict
   - Both branches added this file independently
   - Resolution: Merge test suites, ensure no duplicate tests

**Medium Priority Conflicts:**
3. **`backend/src/agent/mcp_config.py`** - Add/add conflict
   - Configuration changes on both sides
   - Resolution: Merge configurations

4. **`backend/src/agent/tools_and_schemas.py`** - Content conflict
   - Tool definitions modified
   - Resolution: Ensure all tools are preserved

**Low Priority Conflicts:**
5. **`ROADMAP.md`** - Documentation conflict
6. **`docs/tasks/01_MCP_TASKS.md`** - Task documentation conflict

### Merge Complexity: **MEDIUM**
- 6 conflicting files
- Mostly test and configuration conflicts
- Core functionality (mcp_persistence.py) is new, no conflicts
- Main conflict is in graph.py which is critical

---

## PR #16: Hybrid Search, RAG Dual-Write, and Validation

**Branch:** `origin/feature/search-rag-hybrid-3228504735555579147`
**Commits ahead of main:** 6

### Commit History
```
* b585d96 merge: resolve conflicts with main
* c4ebfb2 fix: address PR review feedback
* 404476f feat: implement hybrid search, RAG dual-write, and validation enhancements
* b615115 feat: implement hybrid search, RAG dual-write, and validation enhancements
* 024e253 Merge branch 'main' into feature/search-rag-hybrid-3228504735555579147
* c58ce0b feat: implement hybrid search, RAG dual-write, and validation enhancements
```

### Merge Analysis

**Merge Status:** ⚠️ **CONFLICTS DETECTED**

**Conflicting Files:**
1. `backend/src/agent/graph.py` - Content conflict
2. `backend/src/agent/nodes.py` - Content conflict

### File Changes Summary
```
 backend/scripts/check_rag_parity.py                |  87 +++++
 backend/scripts/test_search.py                     |  21 ++
 backend/scripts/test_validation.py                 |  40 ++
 backend/scripts/verify_agent_flow.py               |  49 +++
 backend/src/agent/graph.py                         |  37 +-
 backend/src/agent/kg.py                            |  70 ++++    [NEW FILE]
 backend/src/agent/nodes.py                         | 382 +++++++++----------
 backend/src/agent/rag.py                           | 409 ++++++++++-----------
 backend/src/config/__init__.py                     |   4 +
 backend/src/config/app_config.py                   |  61 +++    [NEW FILE]
 backend/src/rag/chroma_store.py                    | 163 ++++++++  [NEW FILE]
 backend/src/search/__init__.py                     |   5 +
 backend/src/search/provider.py                     |  38 ++    [NEW FILE]
 backend/src/search/providers/brave_adapter.py      |  68 ++++    [NEW FILE]
 backend/src/search/providers/duckduckgo_adapter.py |  61 +++    [NEW FILE]
 backend/src/search/providers/google_adapter.py     |  65 ++++    [NEW FILE]
 backend/src/search/router.py                       | 108 ++++++   [NEW FILE]
 docs/tasks/implementation_report.md                |  74 ++++    [NEW FILE]
 requirements.txt                                   |  33 ++

 19 files changed, 1350 insertions(+), 425 deletions(-)
```

### Key Changes

**New Modules:**
1. **Search Abstraction Layer** (`backend/src/search/`)
   - `provider.py` - Abstract search provider interface
   - `router.py` - Search provider routing logic
   - `providers/brave_adapter.py` - Brave Search integration
   - `providers/duckduckgo_adapter.py` - DuckDuckGo integration
   - `providers/google_adapter.py` - Google Search integration

2. **RAG Enhancements** (`backend/src/rag/`)
   - `chroma_store.py` - ChromaDB vector store implementation
   - Dual-write capability for FAISS + Chroma

3. **Knowledge Graph** (`backend/src/agent/`)
   - `kg.py` - Knowledge graph integration

4. **Configuration** (`backend/src/config/`)
   - `app_config.py` - Centralized app configuration

**Verification Scripts:**
- `check_rag_parity.py` - Verify FAISS/Chroma parity
- `test_search.py` - Test search providers
- `test_validation.py` - Test validation pipelines
- `verify_agent_flow.py` - End-to-end agent flow verification

**Major Refactors:**
- `backend/src/agent/nodes.py` - 382 lines changed (refactored for hybrid search)
- `backend/src/agent/rag.py` - 409 lines changed (dual-write implementation)

### Conflict Analysis

**Critical Conflicts:**
1. **`backend/src/agent/graph.py`** - Content conflict
   - Main has 18 merged branches worth of changes
   - PR has hybrid search integration
   - Resolution: Complex merge required

2. **`backend/src/agent/nodes.py`** - Content conflict
   - Main has recent refactoring
   - PR has extensive node refactoring (382 lines changed)
   - Resolution: Very complex merge, high risk of breaking changes

### CodeRabbit Issues (from PR comments)

**FAISS Store - Soft Delete Pattern:**
- Location: `backend/src/rag/faiss_store.py` (not in diff, likely in rag.py)
- Issue: Pruning removes from mapping but not from doc_store or FAISS index
- Action: Clarify if intentional soft-delete or implement actual deletion

**Chroma Store - Edge Cases:**
- Location: `backend/src/rag/chroma_store.py`
- Issue: Need better error handling for empty collections
- Action: Add error handling

### Merge Complexity: **HIGH**
- 2 conflicting files but both are CRITICAL
- Massive refactoring in nodes.py (382 lines)
- Large changes in rag.py (409 lines)
- New dependencies (Chroma, search providers)
- CodeRabbit issues to address

---

## Merge Strategy Recommendations

### Option 1: Sequential Merge (Recommended)

**Step 1: Merge PR #19 (MCP Persistence) First**
- **Rationale:** Smaller, more isolated changes
- **Complexity:** Medium
- **Risk:** Medium
- **Conflicts:** 6 files, mostly tests and config
- **Time Estimate:** 1-2 hours

**Conflict Resolution Strategy:**
1. `graph.py` - Carefully merge MCP integration with recent main changes
2. `test_registry.py` - Merge test suites, deduplicate
3. `mcp_config.py` - Merge configurations
4. `tools_and_schemas.py` - Preserve all tool definitions
5. Documentation files - Accept both changes

**Step 2: Merge PR #16 (Hybrid Search) Second**
- **Rationale:** Build on stable base after PR #19
- **Complexity:** High
- **Risk:** High
- **Conflicts:** 2 critical files (graph.py, nodes.py)
- **Time Estimate:** 3-4 hours

**Conflict Resolution Strategy:**
1. `graph.py` - Merge hybrid search with MCP-integrated graph
2. `nodes.py` - Very careful merge of refactored code
3. Test thoroughly after merge
4. Address CodeRabbit feedback

### Option 2: Parallel Merge (Not Recommended)

Merging both PRs simultaneously would create:
- Compound conflicts in graph.py
- Extremely complex nodes.py merge
- High risk of breaking changes
- Difficult to debug issues

### Option 3: Rebase Strategy

**Rebase PR #16 onto PR #19:**
- Create new branch from PR #19
- Rebase PR #16 changes
- Resolve conflicts in isolated environment
- Submit as new PR
- **Advantage:** Cleaner history
- **Disadvantage:** More work, requires PR #19 merge first

---

## Pre-Merge Checklist

### For PR #19 (MCP Persistence):
- [ ] Review mcp_persistence.py implementation
- [ ] Verify MCP tool signatures
- [ ] Check test coverage for new functionality
- [ ] Resolve 6 file conflicts
- [ ] Run full test suite
- [ ] Verify MCP server integration

### For PR #16 (Hybrid Search):
- [ ] Address CodeRabbit FAISS soft-delete issue
- [ ] Add Chroma edge case handling
- [ ] Review search provider implementations
- [ ] Test dual-write RAG functionality
- [ ] Verify knowledge graph integration
- [ ] Resolve 2 critical file conflicts
- [ ] Run verification scripts
- [ ] Full integration testing

---

## Risk Assessment

### PR #19 Risks:
- **Medium Risk:** MCP integration may affect existing persistence
- **Medium Risk:** Test conflicts may hide issues
- **Low Risk:** New file (mcp_persistence.py) is isolated

### PR #16 Risks:
- **High Risk:** Massive nodes.py refactoring
- **High Risk:** RAG dual-write may cause data inconsistencies
- **Medium Risk:** New search providers may have API issues
- **Medium Risk:** CodeRabbit issues need addressing

---

## Recommended Action Plan

1. **Immediate:**
   - Review this analysis with team
   - Decide on merge strategy (recommend Sequential)
   - Allocate time for conflict resolution

2. **PR #19 Merge:**
   - Create merge branch: `merge/pr19-mcp-persistence`
   - Resolve conflicts systematically
   - Test MCP functionality
   - Merge to main

3. **PR #16 Merge:**
   - Wait for PR #19 to stabilize
   - Address CodeRabbit feedback first
   - Create merge branch: `merge/pr16-hybrid-search`
   - Resolve conflicts carefully
   - Extensive testing
   - Merge to main

4. **Post-Merge:**
   - Update documentation
   - Run full test suite
   - Monitor for issues
   - Update worktrees
