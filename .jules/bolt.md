# Bolt's Journal - Critical Learnings

## 2024-05-22 - [Middleware Performance]
**Learning:** `RateLimitMiddleware` using `time.time()` inside high-frequency loops/requests can be a micro-bottleneck if not careful, though usually negligible in Python compared to I/O. However, the cleanup strategy (lazy vs periodic) is critical.
**Action:** Ensure cleanup is amortized or backgrounded.

## 2024-05-22 - [React Memoization Stability]
**Learning:** `React.memo` is useless if props are unstable. Passing inline functions `() => ...` or new objects `{}` as props defeats memoization.
**Action:** Always verify prop stability (useCallback/useMemo) in parent components before wrapping children in React.memo.

## 2024-05-23 - [List Virtualization Alternative]
**Learning:** For medium-sized append-only lists (like chat logs), extracting and memoizing the *list item* component is often a simpler, "good enough" alternative to full windowing/virtualization libraries, avoiding new dependencies.
**Action:** Before reaching for `react-window`, extract the mapped item into a `memo` component.

<<<<<<< HEAD
## 2024-05-24 - [Regex & Deduplication]
**Learning:** In tight loops involving string processing (like keyword extraction), compiling regex patterns at module level and using sets for immediate deduplication can significantly reduce overhead compared to repeated `re.split` calls and list appends.
**Action:** When extracting tokens/keywords from multiple sources, compile regex once and accumulate into a set to avoid O(N*M) downstream redundancy.

## 2024-05-24 - [RAG Context Efficiency]
**Learning:** Naively appending RAG results from multiple sources/subgoals and truncating by length indiscriminately drops high-relevance information found later in the process.
**Action:** Always sort aggregated evidence chunks by relevance score globally before truncating to fit context windows.

## 2026-01-01 - [Component Extraction for Streaming]
**Learning:** When optimizing list rendering for streaming data (like chat messages), extracting list items into memoized components is only effective if the props passed to them are stable. Passing the raw index or the entire list often defeats the purpose because the parent re-renders on every update.
**Action:** Pre-calculate stable boolean flags (e.g., `isLast`, `isLoading`) in the parent map loop and pass those primitive values to the child component instead of raw state objects.

## 2025-05-24 - [LLM Client Instantiation Overhead]
**Learning:** Creating `ChatGoogleGenerativeAI` instances carries a small but non-zero cost (~1.6ms). In high-concurrency scenarios (like parallel validation of 10+ search results), this adds up and churns objects.
**Action:** Use `functools.lru_cache` to reuse LLM client instances when configuration (model, temp) is stable.
