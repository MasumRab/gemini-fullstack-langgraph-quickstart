# Research Agent Inspirations & Implementation Map

This document maps state-of-the-art (SOTA) research agent frameworks to the nodes and capabilities implemented in this project.

---

## 1. Open Deep Research (LangChain)

**Source:** [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research)

| Core Concept | This Project Implementation | Status |
|--------------|----------------------------|--------|
| **Scoping Phase** | `planning_mode` (interactive) | ⚡ Partial (Needs formal clarification loop) |
| **Research Loop** | `web_research` + `reflection` | ✅ Implemented |
| **Synthesis** | `finalize_answer` | ✅ Implemented |
| **Evaluation** | `DeepResearch-Bench` integration | ❌ Planned |

**Planned Action:** Adopt the "Scoping" pattern to ask clarifying questions before generating the initial plan.

---

## 2. STORM (Stanford)

**Source:** [stanford-oval/storm](https://github.com/stanford-oval/storm)

| Core Concept | This Project Implementation | Status |
|--------------|----------------------------|--------|
| **Outline Generation** | `planning_mode` (steps generation) | ⚡ Partial (Linear list, not hierarchical outline) |
| **Perspective-Guided QA** | `generate_query` | ❌ Planned (Currently uses generic query expansion) |
| **Simulated Conversation** | N/A | ❌ Low Priority |
| **Co-STORM (Human Interaction)**| `planning_wait` / `human_feedback` | ✅ Implemented |

**Planned Action:** Upgrade `planning_mode` to generate a hierarchical **Outline** instead of just a flat list of queries.

---

## 3. GPT Researcher

**Source:** [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher)

| Core Concept | This Project Implementation | Status |
|--------------|----------------------------|--------|
| **Parallel Execution** | `Send()` API in LangGraph | ✅ Implemented |
| **Recursive "Deep" Research**| N/A | ❌ Planned (Sub-task spawning) |
| **Local Document Support** | MCP Integration | ⚡ Partial (Via `mcp_server_filesystem`) |
| **Context Aggregation** | `OverallState.web_research_result` | ✅ Implemented |

**Planned Action:** Implement **Recursive Depth** by allowing a research node to recursively call the graph for sub-topics.

---

## 4. Implementation Reference Table

| Name | Repo | Key Feature to Adopt |
| :--- | :--- | :--- |
| **Open Deep Research** | `langchain-ai/open_deep_research` | **Scoping/Clarification Loop** |
| **STORM** | `stanford-oval/storm` | **Hierarchical Outlines** |
| **GPT Researcher** | `assafelovic/gpt-researcher` | **Recursive Tree Exploration** |

---

## Quick Test Commands

```bash
# Test upstream (minimal)
python examples/cli_research.py "What is quantum computing?" --mode upstream

# Test planning (standard)
python examples/cli_research.py "Compare renewable energy sources" --mode planning
```
