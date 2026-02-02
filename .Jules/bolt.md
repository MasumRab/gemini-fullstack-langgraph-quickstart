## 2024-05-23 - Fuzzy Matching Optimization
**Learning:** `difflib.SequenceMatcher.real_quick_ratio()` is an O(1) upper bound on string similarity that is significantly faster than `quick_ratio()` (O(N)) or `ratio()` (O(N*M)), especially when comparing strings of vastly different lengths.
**Action:** Always check `real_quick_ratio()` before `quick_ratio()` or `ratio()` in fuzzy matching loops.
