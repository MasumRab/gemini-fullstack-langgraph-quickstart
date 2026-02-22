# Code Fixes Plan

This document outlines all verified issues and their proposed fixes across multiple files.

## Summary

After analyzing all reported issues, **24 issues were verified** as needing fixes. The issues span across multiple files in the backend and scripts directories.

---

## File-by-File Fixes

### 1. backend/src/agent/nodes.py

#### Issue 1.1: Missing HumanMessage Import (Line 25)
**Status:** ✅ Verified
**Current Code:**
```python
from langchain_core.messages import AIMessage
```
**Problem:** `HumanMessage` is used at line 1170 but not imported.
**Fix:** Add `HumanMessage` to the import statement:
```python
from langchain_core.messages import AIMessage, HumanMessage
```

#### Issue 1.2: Non-normalized plan_todos in Fallback Paths (Lines 842, 859)
**Status:** ✅ Verified
**Current Code:**
```python
plan_todos = [dict(t) for t in current_plan]
```
**Problem:** The fallback paths create shallow dict copies without normalizing keys. The success path creates tasks with keys `title`, `description`, `status`, `query`, but fallback may have different keys like `task`.
**Fix:** Create a helper function to normalize task dicts and use it in both fallback paths:
```python
def _normalize_task(task: dict) -> dict:
    return {
        "title": task.get("title") or task.get("task", ""),
        "description": task.get("description", ""),
        "status": task.get("status", "pending"),
        "query": task.get("query") or task.get("title") or task.get("task", ""),
    }
```
Then replace both fallback lines with:
```python
plan_todos = [_normalize_task(t) for t in current_plan]
```

#### Issue 1.3: Git Merge Conflict Markers (Lines 1421-1425)
**Status:** ✅ Verified
**Current Code:**
```python
def _keywords_from_queries(queries: List[str]) -> List[str]:
```
**Problem:** Leftover git merge conflict markers.
**Fix:** Remove the conflict markers, keeping just the function definition:
```python
def _keywords_from_queries(queries: List[str]) -> List[str]:
```

---

### 2. backend/src/agent/utils.py

#### Issue 2.1: Temperature Not Passed to Gemma Client (Lines 225-234)
**Status:** ✅ Verified
**Current Code:**
```python
if is_gemma:
    from agent.gemma_client import get_gemma_client
    from agent.llm_client import GemmaAdapter

    client = get_gemma_client()
    return GemmaAdapter(client=client)
```
**Problem:** The `temperature` parameter is ignored in the Gemma branch.
**Fix:** Pass temperature to the adapter:
```python
if is_gemma:
    from agent.gemma_client import get_gemma_client
    from agent.llm_client import GemmaAdapter

    client = get_gemma_client()
    return GemmaAdapter(client=client, temperature=temperature)
```
Note: This also requires updating `GemmaAdapter.__init__` to accept and store temperature.

#### Issue 2.2: Git Merge Conflict Markers (Lines 243-279)
**Status:** ✅ Verified
**Current Code:**
```python
def has_fuzzy_match(
    keyword: str, candidates: Iterable[str], cutoff: float = 0.8
) -> bool:
```
And later:
```python
        # Check real_quick_ratio first as an upper bound (O(1))
```
**Problem:** Multiple git merge conflict markers.
**Fix:** Resolve by keeping the cleaner formatting and the Bolt optimization comment:
```python
def has_fuzzy_match(keyword: str, candidates: Iterable[str], cutoff: float = 0.8) -> bool:
    # ... docstring ...
    matcher = difflib.SequenceMatcher(b=keyword)
    for candidate in candidates:
        matcher.set_seq1(candidate)
        # ⚡ Bolt Optimization: Check real_quick_ratio first as an O(1) upper bound based on length
        if (
            matcher.real_quick_ratio() >= cutoff
            and matcher.quick_ratio() >= cutoff
            and matcher.ratio() >= cutoff
        ):
            return True
    return False
```

---

### 3. nul (Root Directory)

#### Issue 3.1: Accidental stderr Output File
**Status:** ✅ Verified
**Current Content:**
```
/usr/bin/bash: line 1: del: command not found
```
**Problem:** This file was created by accidentally running Windows `del` command on Unix.
**Fix:** Delete the file with `git rm nul` or `rm nul`. Add `nul` to `.gitignore` if not already present.

---

### 4. backend/scripts/benchmark.py

#### Issue 4.1: Missing UTF-8 Encoding (Lines 44, 151)
**Status:** ✅ Verified
**Current Code:**
```python
with open(path, "r") as f:  # Line 44
with open("benchmark_report.md", "w") as f:  # Line 151
```
**Fix:** Add explicit UTF-8 encoding:
```python
with open(path, "r", encoding="utf-8") as f:
with open("benchmark_report.md", "w", encoding="utf-8") as f:
```

#### Issue 4.2: KeyError Risk for item["question"] (Lines 59-61)
**Status:** ✅ Verified
**Current Code:**
```python
for item in questions:
    question = item["question"]
    expected_topics = item.get("expected_topics", [])
```
**Fix:** Use defensive access:
```python
for item in questions:
    question = item.get("question")
    if not question:
        logger.warning(f"Skipping malformed item missing 'question': {item}")
        continue
    expected_topics = item.get("expected_topics", [])
```

---

### 5. backend/scripts/visualize_agent_graph.py

#### Issue 5.1: Dummy API Key Injection (Lines 105-107)
**Status:** ✅ Verified
**Current Code:**
```python
if "GEMINI_API_KEY" not in os.environ:
    os.environ["GEMINI_API_KEY"] = "dummy_key_for_visualization"
```
**Problem:** Setting a dummy key can cause confusing errors later.
**Fix:** Fail fast with a clear message:
```python
if "GEMINI_API_KEY" not in os.environ:
    print("Error: GEMINI_API_KEY environment variable is required for visualization.")
    print("Please set GEMINI_API_KEY before running this script.")
    sys.exit(1)
```

---

### 6. backend/src/agent/app.py

#### Issue 6.1: Inconsistent Indentation (Lines 257-260)
**Status:** ✅ Verified
**Current Code:**
```python
                except ValueError as e:
                     if "cannot exceed" in str(e) or "must be at least" in str(e):
                        raise e
                     raise ValueError("max_research_loops must be an integer")
```
**Problem:** Extra indentation (5 spaces instead of 4) in the except block.
**Fix:** Normalize indentation to match surrounding code:
```python
                except ValueError as e:
                    if "cannot exceed" in str(e) or "must be at least" in str(e):
                        raise e
                    raise ValueError("max_research_loops must be an integer")
```

---

### 7. backend/src/agent/gemma_client.py

#### Issue 7.1: None-safe gemma_provider Access (Lines 99-108)
**Status:** ✅ Verified
**Current Code:**
```python
def get_gemma_client() -> GemmaClient:
    provider = app_config.gemma_provider.lower()
```
**Problem:** `app_config.gemma_provider` could be `None`, causing `AttributeError`.
**Fix:** Add default value before lowercasing:
```python
def get_gemma_client() -> GemmaClient:
    provider = (app_config.gemma_provider or "ollama").lower()
```

#### Issue 7.2: Missing Timeout for Ollama POST Request (Lines 91-94)
**Status:** ✅ Verified
**Current Code:**
```python
response = self.requests.post(self.generate_url, json=payload)
```
**Problem:** No timeout can cause indefinite hanging.
**Fix:** Add timeout parameter to the class and use it:
```python
class OllamaGemmaClient(GemmaClient):
    def __init__(self, model_name: str = "gemma:2b", base_url: str = "http://localhost:11434", timeout: int = 120):
        # ... existing init code ...
        self.timeout = timeout

    def invoke(self, prompt: str, **kwargs) -> str:
        # ...
        try:
            response = self.requests.post(self.generate_url, json=payload, timeout=self.timeout)
        except requests.Timeout:
            logger.error(f"Ollama request timed out after {self.timeout}s")
            raise TimeoutError(f"Ollama request timed out after {self.timeout}s")
        except requests.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
            raise
```

#### Issue 7.3: kwargs Can Override Protected Payload Fields (Lines 84-89)
**Status:** ✅ Verified
**Current Code:**
```python
payload = {
    "model": self.model_name,
    "prompt": prompt,
    "stream": False,
    **kwargs
}
```
**Problem:** kwargs can override `model`, `prompt`, and `stream`.
**Fix:** Filter out protected keys:
```python
PROTECTED_KEYS = {"model", "prompt", "stream"}
filtered_kwargs = {k: v for k, v in kwargs.items() if k not in PROTECTED_KEYS}
payload = {
    "model": self.model_name,
    "prompt": prompt,
    "stream": False,
    **filtered_kwargs
}
```

---

### 8. backend/src/agent/llm_client.py

#### Issue 8.1: AttributeError Risk for tool.name (Lines 101-102)
**Status:** ✅ Verified
**Current Code:**
```python
tool_names = [t.name for t in self.tools]
```
**Problem:** Assumes every tool has a `.name` attribute.
**Fix:** Use defensive extraction:
```python
tool_names = [name for t in self.tools if (name := getattr(t, "name", None))]
if len(tool_names) != len(self.tools):
    logger.warning("Some tools lack a 'name' attribute and were skipped")
```

#### Issue 8.2: Duplicate AIMessage Import (Lines 97-108)
**Status:** ✅ Verified
**Current Code:**
```python
if self.tools:
    from agent.tool_adapter import parse_tool_calls
    from langchain_core.messages import AIMessage  # First import
    # ...
from langchain_core.messages import AIMessage  # Second import (line 107)
```
**Problem:** `AIMessage` is imported twice.
**Fix:** Move import to top of method or module level:
```python
from langchain_core.messages import AIMessage

# In the method:
if self.tools:
    from agent.tool_adapter import parse_tool_calls
    tool_names = [name for t in self.tools if (name := getattr(t, "name", None))]
    tool_calls = parse_tool_calls(response_text, allowed_tools=tool_names)
    if tool_calls:
        return AIMessage(content=response_text, tool_calls=tool_calls)
return AIMessage(content=response_text)
```

---

### 9. backend/src/agent/security.py

#### Issue 9.1: Wrong IP Selection from X-Forwarded-For (Lines 143-154)
**Status:** ✅ Verified
**Current Code:**
```python
ips = [ip.strip() for ip in forwarded.split(",")]
client_ip = ips[-1]  # Takes last hop
```
**Problem:** Using `ips[-1]` gets the nearest proxy, not the original client.
**Fix:** Use `ips[0]` for the original client IP:
```python
ips = [ip.strip() for ip in forwarded.split(",")]
client_ip = ips[0]  # Original client IP (leftmost)
```
Note: Update the comment to reflect this change.

---

### 10. backend/src/search/router.py

#### Issue 10.1: Silent None Return for Unknown Provider (Lines 32-48)
**Status:** ✅ Verified
**Current Code:**
```python
def _get_provider(self, name: str) -> Optional[SearchProvider]:
    # ... provider initialization ...
    return self.providers.get(name)  # Returns None silently for unknown names
```
**Problem:** No warning for unrecognized provider names.
**Fix:** Add warning logging:
```python
def _get_provider(self, name: str) -> Optional[SearchProvider]:
    if name in self.providers:
        return self.providers[name]

    try:
        # ... existing provider initialization ...
    except Exception as e:
        logger.debug(f"Provider {name} failed to init: {e}")
        return None

    if name not in self.providers:
        valid_providers = [p.value for p in SearchProviderType]
        logger.warning(f"Unknown provider '{name}'. Valid providers: {valid_providers}")

    return self.providers.get(name)
```

#### Issue 10.2: Race Condition in Lazy Provider Init (Lines 27-51)
**Status:** ✅ Verified
**Current Code:**
```python
def _get_provider(self, name: str) -> Optional[SearchProvider]:
    if name in self.providers:
        return self.providers[name]
    # No lock - race condition possible
```
**Problem:** Multiple threads could initialize the same provider simultaneously.
**Fix:** Add thread lock:
```python
import threading

class SearchRouter:
    def __init__(self):
        self.providers: Dict[str, SearchProvider] = {}
        self._providers_lock = threading.Lock()

    def _get_provider(self, name: str) -> Optional[SearchProvider]:
        if name in self.providers:
            return self.providers[name]

        with self._providers_lock:
            # Double-checked locking
            if name in self.providers:
                return self.providers[name]

            try:
                # ... existing provider initialization ...
            except Exception as e:
                logger.debug(f"Provider {name} failed to init: {e}")
                return None

        return self.providers.get(name)
```

---

### 11. backend/tests/conftest.py

#### Issue 11.1: Duplicate pytest Hook Implementations (Lines 34-62, 198-221)
**Status:** ✅ Verified
**Current Code:** The file has two sets of `pytest_addoption` and `pytest_collection_modifyitems`:
- First set: Lines 34-62
- Second set: Lines 198-221
**Problem:** Duplicate hook implementations can cause silent overwrites.
**Fix:** Remove the second set (lines 194-221), keeping only the first set with `pytest_configure`.

---

### 12. backend/tests/data/benchmark_questions.json

#### Issue 12.1: Typos in Test Data (Lines 3-4)
**Status:** ✅ Verified
**Current Content:**
```json
{
  "question": "What are the latest developments in rooms-temperature superconductivity as of 2025?",
  "expected_topics": ["LK-99", "Reddmatter", "high pressure"]
}
```
**Problems:**
1. "rooms-temperature" should be "room-temperature"
2. "Reddmatter" appears to be a typo - likely should be "Reddmatter" (a claimed superconductor) or removed if uncertain

**Fix:**
```json
{
  "question": "What are the latest developments in room-temperature superconductivity as of 2025?",
  "expected_topics": ["LK-99", "Reddmatter", "high pressure"]
}
```
Note: "Reddmatter" appears to be intentional (referring to a specific material claim), so keeping it but fixing "rooms-temperature".

---

### 13. backend/tests/evaluators.py

#### Issue 13.1: None API Key Passed to ChatGoogleGenerativeAI (Lines 16-20)
**Status:** ✅ Verified
**Current Code:**
```python
judge_model = ChatGoogleGenerativeAI(
    model=GEMINI_PRO,
    temperature=0,
    api_key=os.getenv("GEMINI_API_KEY")  # Can be None
)
```
**Problem:** `os.getenv("GEMINI_API_KEY")` can return `None`.
**Fix:** Validate before use:
```python
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required for evaluators")

judge_model = ChatGoogleGenerativeAI(
    model=GEMINI_PRO,
    temperature=0,
    api_key=GEMINI_API_KEY
)
```

---

### 14. backend/tests/test_gemma_compatibility.py

#### Issue 14.1: Unused base_state Fixture (Lines 107-128)
**Status:** ✅ Verified
**Current Code:**
```python
def test_web_research_gemma_safety(
    self, mock_search_router, model_name, base_state
):
    # ...
    state = {"search_query": ["Test Query"], "id": 1}  # Creates new state instead of using base_state
```
**Problem:** `base_state` fixture is accepted but not used.
**Fix:** Either remove `base_state` from signature or use it:
```python
def test_web_research_gemma_safety(
    self, mock_search_router, model_name, base_state
):
    config = RunnableConfig(configurable={"query_generator_model": model_name})
    state = base_state.copy()
    state["search_query"] = ["Test Query"]
    state["id"] = 1
    # ...
```

---

### 15. scripts/pruning_plan.py

#### Issue 15.1: Unchecked subprocess Return Code in get_remote_branches (Lines 6-14)
**Status:** ✅ Verified
**Current Code:**
```python
def get_remote_branches():
    cmd = ["git", "branch", "-r"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    branches = []
    for line in result.stdout.splitlines():
        # ...
    return branches
```
**Problem:** `result.returncode` is never checked.
**Fix:**
```python
def get_remote_branches():
    cmd = ["git", "branch", "-r"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git branch -r failed: {result.stderr}")
    branches = []
    for line in result.stdout.splitlines():
        # ...
    return branches
```

#### Issue 15.2: Hardcoded "main" and Missing Return Code Checks in get_diff_stats (Lines 16-29)
**Status:** ✅ Verified
**Current Code:**
```python
def get_diff_stats(branch):
    cmd_merged = ["git", "rev-list", "--count", f"main..{branch}"]
    res_merged = subprocess.run(cmd_merged, capture_output=True, text=True)
    if res_merged.returncode == 0 and res_merged.stdout.strip() == "0":
        return "MERGED", 0

    cmd = ["git", "diff", "--shortstat", f"main...{branch}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
```
**Problems:**
1. Hardcoded "main" branch
2. First subprocess return code is checked, but second is not
3. Invalid refs return "NO_DIFF" silently

**Fix:**
```python
def get_diff_stats(branch, default_branch: str = "main"):
    # Check if merged first
    cmd_merged = ["git", "rev-list", "--count", f"{default_branch}..{branch}"]
    res_merged = subprocess.run(cmd_merged, capture_output=True, text=True)
    if res_merged.returncode != 0:
        logger.warning(f"Failed to check merge status for {branch}: {res_merged.stderr}")
        return "ERROR", 0
    if res_merged.stdout.strip() == "0":
        return "MERGED", 0

    # Get diff stats
    cmd = ["git", "diff", "--shortstat", f"{default_branch}...{branch}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning(f"Failed to get diff stats for {branch}: {result.stderr}")
        return "ERROR", 0

    output = result.stdout.strip()
    # ...
```

---

## Execution Order

The fixes should be applied in the following order for efficiency:

1. **Delete nul file** - Simple cleanup
2. **Fix git merge conflicts** - Critical for code parsing (nodes.py, utils.py)
3. **Fix imports** - Critical for runtime (nodes.py HumanMessage, llm_client.py AIMessage)
4. **Fix conftest.py duplicates** - Test infrastructure
5. **Fix remaining issues** - All other fixes can be done in parallel

---

## Verification Steps

After applying fixes:

1. Run `ruff check backend/` to verify lint compliance
2. Run `mypy backend/` for type checking
3. Run `pytest backend/tests/` to verify tests pass
4. Run `python -m py_compile backend/src/agent/nodes.py` to verify syntax

---

## Commit Strategy

Each fix will be committed incrementally with descriptive commit messages for easier review and rollback:

| Commit # | File | Commit Message |
|----------|------|----------------|
| 1 | nul | `chore: remove accidental nul file from Windows del command` |
| 2 | nodes.py | `fix(nodes): add HumanMessage to langchain_core.messages import` |
| 3 | nodes.py | `fix(nodes): normalize plan_todos in fallback paths for consistent schema` |
| 4 | nodes.py | `fix(nodes): remove git merge conflict markers` |
| 5 | utils.py | `fix(utils): pass temperature parameter to Gemma client/adapter` |
| 6 | utils.py | `fix(utils): resolve git merge conflict markers in has_fuzzy_match` |
| 7 | gemma_client.py | `fix(gemma): handle None gemma_provider with default value` |
| 8 | gemma_client.py | `fix(gemma): add timeout to Ollama POST request` |
| 9 | gemma_client.py | `fix(gemma): protect payload fields from kwargs override` |
| 10 | llm_client.py | `fix(llm): defensive tool.name extraction with getattr` |
| 11 | llm_client.py | `fix(llm): remove duplicate AIMessage import` |
| 12 | app.py | `style(app): normalize indentation in max_research_loops validation` |
| 13 | security.py | `fix(security): use ips[0] for original client IP in X-Forwarded-For` |
| 14 | router.py | `fix(search): log warning for unrecognized provider names` |
| 15 | router.py | `fix(search): add thread-safe lock for provider lazy initialization` |
| 16 | benchmark.py | `fix(benchmark): add UTF-8 encoding to file open calls` |
| 17 | benchmark.py | `fix(benchmark): add defensive access for item question field` |
| 18 | visualize_agent_graph.py | `fix(viz): fail fast with clear error when GEMINI_API_KEY missing` |
| 19 | conftest.py | `fix(tests): remove duplicate pytest hook implementations` |
| 20 | evaluators.py | `fix(tests): validate GEMINI_API_KEY before use in evaluators` |
| 21 | test_gemma_compatibility.py | `fix(tests): use base_state fixture in test_web_research_gemma_safety` |
| 22 | benchmark_questions.json | `fix(tests): correct typo rooms-temperature to room-temperature` |
| 23 | pruning_plan.py | `fix(scripts): check subprocess return codes in get_remote_branches` |
| 24 | pruning_plan.py | `fix(scripts): add default_branch param and return code checks to get_diff_stats` |

---

## Files Requiring Changes

| File | Issue Count |
|------|-------------|
| backend/src/agent/nodes.py | 3 |
| backend/src/agent/utils.py | 2 |
| backend/src/agent/gemma_client.py | 3 |
| backend/src/agent/llm_client.py | 2 |
| backend/src/agent/app.py | 1 |
| backend/src/agent/security.py | 1 |
| backend/src/search/router.py | 2 |
| backend/scripts/benchmark.py | 2 |
| backend/scripts/visualize_agent_graph.py | 1 |
| backend/tests/conftest.py | 1 |
| backend/tests/evaluators.py | 1 |
| backend/tests/test_gemma_compatibility.py | 1 |
| backend/tests/data/benchmark_questions.json | 1 |
| scripts/pruning_plan.py | 2 |
| nul | 1 (delete) |
| **Total** | **24** |
