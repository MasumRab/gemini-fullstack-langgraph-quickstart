# Bolt's Journal - Critical Learnings

## 2024-05-22 - [Middleware Performance]
**Learning:** `RateLimitMiddleware` using `time.time()` inside high-frequency loops/requests can be a micro-bottleneck if not careful, though usually negligible in Python compared to I/O. However, the cleanup strategy (lazy vs periodic) is critical.
**Action:** Ensure cleanup is amortized or backgrounded.

## 2024-05-22 - [React Memoization Stability]
**Learning:** `React.memo` is useless if props are unstable. Passing inline functions `() => ...` or new objects `{}` as props defeats memoization.
**Action:** Always verify prop stability (useCallback/useMemo) in parent components before wrapping children in React.memo.
