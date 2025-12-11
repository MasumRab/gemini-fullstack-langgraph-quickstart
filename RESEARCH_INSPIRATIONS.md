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

---

## 2. STORM (Stanford)

**Source:** [stanford-oval/storm](https://github.com/stanford-oval/storm)

| Core Concept | This Project Implementation | Status |
|--------------|----------------------------|--------|
| **Outline Generation** | `planning_mode` (steps generation) | ⚡ Partial (Linear list, not hierarchical outline) |
| **Perspective-Guided QA** | `generate_query` | ❌ Planned |
| **Co-STORM (Human Interaction)**| `planning_wait` / `human_feedback` | ✅ Implemented |

---

## 3. ManuSearch (RUCAIBox)

**Source:** [RUCAIBox/ManuSearch](https://github.com/RUCAIBox/ManuSearch)

| Core Concept | This Project Implementation | Status |
|--------------|----------------------------|--------|
| **Collaborative Agents** | `Supervisor` / `Parallel` Graphs | ✅ Implemented |
| **Structured Reader** | `web_research` (raw content) | ⚡ Partial (Need dedicated Reader node) |
| **ORION Benchmark** | N/A | ❌ Planned |

---

## 4. GPT Researcher

**Source:** [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher)

| Core Concept | This Project Implementation | Status |
|--------------|----------------------------|--------|
| **Parallel Execution** | `Send()` API in LangGraph | ✅ Implemented |
| **Recursive "Deep" Research**| N/A | ❌ Planned (Sub-task spawning) |

---

## 5. Quick Test Commands

```bash
# Test upstream (minimal)
python examples/cli_research.py "What is quantum computing?" --mode upstream

# Test planning (standard)
python examples/cli_research.py "Compare renewable energy sources" --mode planning
```
