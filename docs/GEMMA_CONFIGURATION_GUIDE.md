# Gemma Configuration & Best Practices Guide

This guide provides recommendations for configuring and using Gemma models (specifically `gemma-3-27b-it`) effectively within the Research Agent, based on empirical verification and prompt engineering patterns.

## 1. Model Configuration Strategies

Choosing the right configuration depends on your priority: **Speed** vs. **Depth/Quality**.

| Strategy | Recommended Config | Use Case | Trade-offs |
| :--- | :--- | :--- | :--- |
| **Fast / Overview** | `max_research_loops=1`<br>`number_of_initial_queries=2` | Quick summaries, fact-checking, simple topics. | Lower depth, might miss nuance. Fastest response time. |
| **Balanced** | `max_research_loops=2`<br>`number_of_initial_queries=3` | Standard research reports, general knowledge exploration. | Good balance of coverage and latency. |
| **Deep Research** | `max_research_loops=3+`<br>`number_of_initial_queries=4+` | Complex topics, academic reviews, multi-faceted analysis. | High latency, higher token usage. susceptible to API rate limits on free tiers. |

### Configuration Parameters

*   **`max_research_loops`**: Controls how many times the agent reflects on its findings and generates new follow-up queries. Higher values lead to more exhaustive research but significantly increase execution time.
*   **`number_of_initial_queries`**: Determines the breadth of the initial search. More queries cover more angles but can overwhelm rate limits.

## 2. Tooling & Prompting Best Practices

Gemma models, while powerful, benefit significantly from specific prompting structures to ensure reliable tool usage (function calling).

### The "Thought-Action" Pattern
Unlike models with native function calling APIs that abstract away the process, Gemma performs best when explicitly instructed to "Think" before acting.

**Recommended Prompt Structure:**
```markdown
1. **Thought**: First, reason about the user's request and which tool (if any) is best suited.
2. **Action**: If a tool is needed, output a JSON object strictly following this schema...
```
*Why?* Forcing the model to output a rationale ("Thought") first stabilizes its internal state and increases the probability of generating valid JSON in the subsequent "Action" block.

### Search Query Optimization
Open-weights models can sometimes be "chatty," interacting with search tools as if they were a human (e.g., "Please tell me about...").

**Recommendation:**
Explicitly instruct the model to generate **Keyword-Based Queries**.
*   **Bad:** "What are the latest advancements in solid state batteries?"
*   **Good:** "solid state battery advancements 2024 2025"

*Justification:* Search engines (like DuckDuckGo/Google) rank keyword-dense queries higher than natural language questions, leading to higher quality context retrieval for the agent.

### JSON Robustness
Models may sometimes output the tool arguments directly without wrapping them in a `tool_calls` list, or include markdown formatting (` ```json `).

**Implementation Note:** The `GemmaToolAdapter` in this codebase includes fallback logic to handle:
1.  Standard `tool_calls` wrapper.
2.  Direct argument objects (implicit tool selection).
3.  Markdown code block stripping.

## 3. Rate Limit Management (Google GenAI)

When using Gemma via the Google GenAI API (Free Tier), you may encounter `429 RESOURCE_EXHAUSTED` errors if the agent runs too many parallel searches.

**Mitigation:**
*   **Reduce Parallelism:** Lower `number_of_initial_queries`.
*   **Sequential Execution:** The agent graph is designed to handle failures gracefully, but reducing the initial burst of queries is the most effective fix.
*   **Retry Logic:** Ensure your `llm_client` implements exponential backoff (already handled in this codebase).
