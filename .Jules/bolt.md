## 2025-05-18 - [Optimization of Fuzzy Matching]
**Learning:** `difflib.SequenceMatcher.real_quick_ratio()` provides an O(1) upper bound check based on length, which is significantly faster than `quick_ratio()` (O(N)) or `ratio()` (O(N*M)). Using this as a first-pass filter for fuzzy matching large datasets can dramatically improve performance.
**Action:** Always check for `real_quick_ratio()` when implementing fuzzy matching loops with `difflib`.
