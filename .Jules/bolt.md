# Bolt's Journal
This journal documents critical performance learnings for the codebase.

## 2024-05-23 - Lazy Loading Search Providers
**Learning:** Moving heavy SDK imports (like `google.genai`) inside methods significantly improves startup time and robustness.
**Action:** Use local imports inside factory methods for optional integrations or heavy dependencies. When testing, patch the class at its *source definition*, not the module namespace.

## 2024-05-24 - [Initial Entry]
**Learning:** Initial setup of Bolt's journal.
**Action:** Use this file to record specific performance insights.

## 2025-05-18 - [Optimization of Fuzzy Matching]
**Learning:** `difflib.SequenceMatcher.real_quick_ratio()` provides an O(1) upper bound check based on length, which is significantly faster than `quick_ratio()` (O(N)) or `ratio()` (O(N*M)). Using this as a first-pass filter for fuzzy matching large datasets can dramatically improve performance.
**Action:** Always check for `real_quick_ratio()` when implementing fuzzy matching loops with `difflib`.

## 2026-01-25 - [Memory vs Reality Discrepancy]
**Learning:** The memory claimed `format_search_output` was already using list join, but the actual code on disk was using O(N^2) string concatenation.
**Action:** Always verify code state with `read_file` before trusting memory or documentation about optimizations.
