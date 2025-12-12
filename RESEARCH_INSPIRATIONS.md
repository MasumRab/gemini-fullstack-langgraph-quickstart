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

## 3. ThinkDepthAI Deep Research

**Source:** [ThinkDepthAI/thinkdepthai](https://github.com/QishengLu/thinkdepthai)

| Core Concept | This Project Implementation | Status |
|--------------|----------------------------|--------|
| Planning Mode | `planning_mode` + `planning_wait` | ✅ Implemented |
| User Confirmation | `planning_router` + `/confirm_plan` | ✅ Implemented |
| Structured Plans | `planning_steps` in state | ✅ Implemented |
| Plan Persistence | `save_plan` / `load_plan` | ✅ Implemented |

**Web:** [thinkdepth.ai](https://thinkdepth.ai/)
**Graph:** `planning.py`

---

## 4. FlowSearch (InternAgent)

**Source:** [InternScience/InternAgent](https://github.com/InternScience/InternAgent)
**Docs:** [InternLM](https://internlm.intern-ai.org.cn/api/document)

| Core Concept | This Project Implementation | Status |
|--------------|----------------------------|--------|
| **Dynamic Knowledge Flow** | `OverallState` transitions | ⚡ Partial (Linear flow) |
| **Hierarchical Decomposition** | `planning_mode` (recursive steps) | ❌ Planned |

---

## 5. ManuSearch (RUCAIBox)

**Source:** [RUCAIBox/ManuSearch](https://github.com/RUCAIBox/ManuSearch)

| Core Concept | This Project Implementation | Status |
|--------------|----------------------------|--------|
| **Structured Reader** | `web_research` (raw content) | ⚡ Partial (Need dedicated Reader node) |

---

## 6. GPT Researcher

**Source:** [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher)

| Core Concept | This Project Implementation | Status |
|--------------|----------------------------|--------|
| **Recursive "Deep" Research**| N/A | ❌ Planned (Sub-task spawning) |

---

## 7. Benchmarks (Planned)

| Benchmark | Source | Goal |
|-----------|--------|------|
| **MLE-bench** | [openai/mle-bench](https://github.com/openai/mle-bench) | Evaluate Engineering Capabilities |
| **DeepResearch-Bench** | [muset-ai](https://huggingface.co/spaces/muset-ai/DeepResearch-Bench-Leaderboard) | Evaluate Research Quality |

---

## 8. Quick Test Commands

```bash
# Test upstream (minimal)
python examples/cli_research.py "What is quantum computing?" --mode upstream

# Test planning (standard)
python examples/cli_research.py "Compare renewable energy sources" --mode planning
```

---

## References

| Framework | Repository/Paper |
|-----------|-----------------|
| Open Deep Research | https://github.com/langchain-ai/open_deep_research |
| ThinkDepthAI | https://github.com/QishengLu/thinkdepthai |
| STORM | https://github.com/stanford-oval/storm |
| RhinoInsight | (Conceptual - Checklist verification pattern) |
| TTD-DR | (Conceptual - Diffusion-based research) |
| ManuSearch | https://github.com/RUCAIBox/ManuSearch |
| FlowSearch | https://github.com/InternScience/InternAgent |
| Cognee (KG) | https://github.com/topoteretes/cognee |
| LangGraph | https://github.com/langchain-ai/langgraph |
