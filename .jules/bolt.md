## 2024-05-24 - [Regex & Deduplication]
**Learning:** In tight loops involving string processing (like keyword extraction), compiling regex patterns at module level and using sets for immediate deduplication can significantly reduce overhead compared to repeated `re.split` calls and list appends.
**Action:** When extracting tokens/keywords from multiple sources, compile regex once and accumulate into a set to avoid O(N*M) downstream redundancy.
