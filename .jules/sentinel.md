## 2025-05-18 - [DoS via Unbounded Input Fan-out]
**Vulnerability:** The agent accepted an arbitrary `initial_search_query_count` and `max_research_loops` from the input state. This allowed an attacker to force the agent to generate thousands of search queries (DoS amplification) or run many research loops, exhausting API quotas and server resources.
**Learning:** Logic that trusts state inputs for control flow parameters (loop counts, fan-out factors) creates amplification vectors. Even if input complexity (size/depth) is validated, the *semantic value* must be capped.
**Prevention:** Always clamp numeric control parameters derived from input state using `min(value, HARD_LIMIT)` before using them in prompts or loops.
