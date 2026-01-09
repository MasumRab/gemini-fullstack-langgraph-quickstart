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

## 2024-05-24 - [RAG Context Efficiency]
**Learning:** Naively appending RAG results from multiple sources/subgoals and truncating by length indiscriminately drops high-relevance information found later in the process.
**Action:** Always sort aggregated evidence chunks by relevance score globally before truncating to fit context windows.
