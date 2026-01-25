# Bolt's Journal

This journal documents critical performance learnings for the codebase.

## 2024-05-24 - [Initial Entry]
**Learning:** Initial setup of Bolt's journal.
**Action:** Use this file to record specific performance insights.

## 2026-01-25 - [Memory vs Reality Discrepancy]
**Learning:** The memory claimed `format_search_output` was already using list join, but the actual code on disk was using O(N^2) string concatenation.
**Action:** Always verify code state with `read_file` before trusting memory or documentation about optimizations.
