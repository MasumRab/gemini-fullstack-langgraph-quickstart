# Deep Research Landscape & Implementation Reference

This document maps the current landscape of "Deep Research" agents, verified open-source implementations, and academic frameworks. It serves as a reference for architectural decisions in this project.

## 1. Open Source Implementations (Verified)

### **1. Open Deep Research (LangChain)**
- **GitHub**: [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research)
- **Architecture**: `Scope → Research → Write`
- **Key Concepts**: Plan-and-Execute, Scoping Phase.
- **Proposed Implementation**:
  - **Node**: `scoping_node`
  - **Logic**: Intercepts the user query before the main loop. If ambiguous, it returns a `ScopingState` interrupt to ask the user clarifying questions. Once satisfied, it passes the refined query to `planning_mode`.

### **2. STORM (Stanford)**
- **GitHub**: [stanford-oval/storm](https://github.com/stanford-oval/storm)
- **Architecture**: `Perspective Discovery → Outline Generation → Multi-Agent Conversation → Article Writing`
- **Relevance**: High value for our "Long-term Planning" goal via **Outline Generation**.
- **Proposed Implementation**:
  - **Node**: `outline_gen`
  - **Logic**: Accepts a query and context. Uses an LLM to generate a hierarchical `Outline` object (Section -> Subsections) instead of a flat list.
  - **Node**: `perspective_gen`
  - **Logic**: Generates "personas" (e.g., "Skeptic", "Historian") to bias the query generation for broader coverage.

### **3. GPT Researcher**
- **GitHub**: [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher)
- **Architecture**: `Planner → Parallel Execution Agents → Aggregator → Report Writer`
- **Relevance**: We plan to adopt the **Recursive Depth** parameter.
- **Proposed Implementation**:
  - **Node**: `research_subgraph`
  - **Logic**: A node that compiles and runs a *new* instance of the agent graph for a specific sub-topic. It inputs a sub-query and outputs a summarized report, which is then fed back into the main graph's context.

### **4. FlowSearch (InternAgent)**
- **GitHub**: [InternScience/InternAgent](https://github.com/InternScience/InternAgent)
- **Docs**: [InternLM Document](https://internlm.intern-ai.org.cn/api/document)
- **Paper**: [FlowSearch: Advancing deep research with dynamic structured knowledge flow](https://arxiv.org/abs/2510.08521)
- **Architecture**:
  - **Dynamic Knowledge Flow**: Active construction and evolution of a structured flow graph (DAG).
- **Proposed Implementation**:
  - **Node**: `flow_update`
  - **Logic**: Runs after every search iteration. It analyzes the `web_research_results` and decides whether to (a) Mark current task complete, (b) Add new dependent tasks, or (c) Modify existing tasks. It essentially "patches" the `todo_list` DAG in real-time.

### **5. ManuSearch (RUCAIBox)**
- **GitHub**: [RUCAIBox/ManuSearch](https://github.com/RUCAIBox/ManuSearch)
- **Paper**: [ManuSearch: Democratizing Deep Search in Large Language Models](https://arxiv.org/abs/2505.18105)
- **Architecture**: 3-Agent Collaborative Framework (Planner, Searcher, Reader).
- **Proposed Implementation**:
  - **Node**: `content_reader`
  - **Logic**: Instead of just dumping raw HTML, this node takes the retrieved content and extracts structured `Evidence` objects (Claim, Source, Context, Confidence) relevant to the specific plan step.

## 2. Industry & Academic Frameworks

### **RhinoInsight**
- **Paper**: [RhinoInsight: Improving Deep Research through Control Mechanisms for Model Behavior and Context](https://arxiv.org/abs/2511.18743)
- **Relevance**: Validates our focus on "Checklist-based Verification".
- **Proposed Implementation**:
  - **Node**: `checklist_verifier`
  - **Logic**: Runs a dedicated "Audit" pass over the findings against the original plan items, flagging unsupported claims for re-research.

### **TTD-DR (Test-Time Denoising)**
- **Concept**: Diffusion-based reasoning.
- **Proposed Implementation**:
  - **Node**: `denoising_refiner`
  - **Logic**: Generates $N$ draft answers in parallel, then uses a "Judge" model to critique and merge them into a single "denoised" high-quality answer.

## 3. Verified Benchmarks

### **MLE-bench (OpenAI)**
- **GitHub**: [openai/mle-bench](https://github.com/openai/mle-bench)
- **Focus**: Evaluating AI agents on Machine Learning Engineering tasks.

### **DeepResearch-Bench**
- **Source**: [HuggingFace Leaderboard (muset-ai)](https://huggingface.co/spaces/muset-ai/DeepResearch-Bench-Leaderboard)
- **Metrics**: Pass@1, Citation Quality.

### **ORION (ManuSearch Benchmark)**
- **Source**: [HuggingFace Dataset (RUC-AIBOX)](https://huggingface.co/datasets/RUC-AIBOX/ORION)
- **Focus**: Open-web reasoning over long-tail entities.

## 4. Integration Roadmap

| Feature | Inspired By | Priority | Implementation Plan |
| :--- | :--- | :--- | :--- |
| **Recursive Depth** | GPT Researcher | High | Implement `research_subgraph` node |
| **Outline Generation** | STORM | Medium | Implement `outline_gen` node |
| **Dynamic Flow** | FlowSearch | Medium | Implement `flow_update` node |
| **Structured Reading** | ManuSearch | Medium | Implement `content_reader` node |
