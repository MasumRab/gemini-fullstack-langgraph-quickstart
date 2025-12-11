# Research Agent Inspirations & Implementation Map

This document maps state-of-the-art (SOTA) research agent frameworks to the nodes and capabilities implemented in this project.

---

## 1. Open Deep Research (LangChain)

**Source:** [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research)

| Core Concept | This Project Implementation | Status |
|--------------|----------------------------|--------|
| **Scoping Phase** | `planning_mode` (interactive) | ⚡ Partial |
| **Research Loop** | `web_research` + `reflection` | ✅ Implemented |

---

## 2. STORM (Stanford)

**Source:** [stanford-oval/storm](https://github.com/stanford-oval/storm)

| Core Concept | This Project Implementation | Status |
|--------------|----------------------------|--------|
| **Outline Generation** | `planning_mode` (steps generation) | ⚡ Partial |
| **Co-STORM (Interaction)**| `planning_wait` / `human_feedback` | ✅ Implemented |

---

## 3. FlowSearch (InternAgent)

**Source:** [InternScience/InternAgent](https://github.com/InternScience/InternAgent)

| Core Concept | This Project Implementation | Status |
|--------------|----------------------------|--------|
| **Dynamic Knowledge Flow** | `OverallState` transitions | ⚡ Partial (Linear flow) |
| **Hierarchical Decomposition** | `planning_mode` (recursive steps) | ❌ Planned |

---

## 4. ManuSearch (RUCAIBox)

**Source:** [RUCAIBox/ManuSearch](https://github.com/RUCAIBox/ManuSearch)

| Core Concept | This Project Implementation | Status |
|--------------|----------------------------|--------|
| **Structured Reader** | `web_research` (raw content) | ⚡ Partial (Need dedicated Reader node) |

---

## 5. GPT Researcher

**Source:** [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher)

| Core Concept | This Project Implementation | Status |
|--------------|----------------------------|--------|
| **Recursive "Deep" Research**| N/A | ❌ Planned (Sub-task spawning) |

---

## 6. Quick Test Commands

```bash
# Test upstream (minimal)
python examples/cli_research.py "What is quantum computing?" --mode upstream

# Test planning (standard)
python examples/cli_research.py "Compare renewable energy sources" --mode planning
```
