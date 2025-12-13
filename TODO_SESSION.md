# Session TODO - Unfinished/Interrupted Tasks

## Priority 1: Critical (Blocking)

### 1. ✅ Resolve All Merge Conflict Markers
- **Status:** COMPLETED (as of last grep search)
- **Files Fixed:**
  - `backend/src/agent/graph.py`
  - `backend/src/agent/configuration.py`
  - `backend/src/agent/nodes.py`
  - `backend/src/agent/mcp_config.py`
  - `backend/src/agent/research_tools.py`
  - `backend/tests/test_nodes.py`

### 2. ⏳ Verify Backend Tests Pass
- **Status:** INTERRUPTED (pytest was running when command was canceled)
- **Action Required:** Run `pytest backend/tests/test_nodes.py` to confirm test collection works
- **Next Step:** If passes, run full backend test suite

### 3. ⏳ Verify Agent Flow Script
- **Status:** NOT STARTED (blocked by conflict resolution)
- **Action Required:** Run `python backend/scripts/verify_agent_flow.py`

## Priority 2: Git History Cleanup

### 4. 🔴 Squash 104 Commits Into Logical Groups
- **Status:** NOT STARTED
- **User Request:** "there are still 104 commits, find some more smart squashes"
- **Proposed Groups:**
  1. `feat: MCP Persistence Wrapper & Graph Integration` - Core PR #19 feature
  2. `feat: Model Configuration Updates (Gemini 2.5)` - All model-related changes
  3. `feat: Validation & Compression Pipeline` - Hybrid validation, compression_node
  4. `feat: Search Router Abstraction` - SearchRouter, provider fallback
  5. `feat: Rate Limiting & Context Management` - Rate limiter, context window mgr
  6. `chore: Conflict Resolution & Cleanup` - Merge conflict fixes
  7. `docs: Model Centralization Task` - TASK_CENTRALIZE_MODELS.md

### 5. 🔴 Stage and Commit Current Conflict Fixes
- **Status:** NOT STARTED (conflict resolution edits are unstaged)
- **Action Required:** 
  ```bash
  git add -A
  git commit -m "fix: resolve all merge conflict markers"
  ```

## Priority 3: Deferred Tasks (From TASK_CENTRALIZE_MODELS.md)

### 6. 📋 Model Centralization Task
- **Status:** DOCUMENTED, NOT IMPLEMENTED
- **File:** `TASK_CENTRALIZE_MODELS.md`
- **Summary:** Create a central `ModelRegistry` to manage all model definitions across the codebase

## Priority 4: Verification

### 7. 📋 Check for Conflict Markers in Other Directories
- **Status:** Partially Done
- **Done:** `backend/src/` - CLEAN
- **TODO:** Check `backend/tests/`, `frontend/`, `notebooks/`, root files

---

## Quick Commands

```powershell
# 1. Verify no conflicts remain
git diff --check

# 2. Run tests
pytest backend/tests/test_nodes.py

# 3. Stage and commit fixes
git add -A
git commit -m "fix: resolve all merge conflict markers"

# 4. View commit count
git log --oneline | Measure-Object -Line

# 5. Interactive rebase for squashing (use HEAD~N where N is commit count)
git rebase -i HEAD~104
```

---
*Generated: 2024-12-13*
