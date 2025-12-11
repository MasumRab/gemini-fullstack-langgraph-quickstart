# Deep Research Landscape & Implementation Reference

This document maps the current landscape of "Deep Research" agents, verified open-source implementations, and academic frameworks. It serves as a reference for architectural decisions in this project.

## 1. Open Source Implementations (Verified)

### **1. Open Deep Research (LangChain)**
- **GitHub**: [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research)
- **Architecture**: `Scope → Research → Write`
- **Key Concepts**: Plan-and-Execute, Scoping Phase.
- **Relevance**: We are adopting the "Scoping" phase (clarifying user intent) as a high priority.

### **2. STORM (Stanford)**
- **GitHub**: [stanford-oval/storm](https://github.com/stanford-oval/storm)
- **Architecture**: `Perspective Discovery → Outline Generation → Multi-Agent Conversation → Article Writing`
- **Relevance**: High value for our "Long-term Planning" goal via **Outline Generation**.

### **3. GPT Researcher**
- **GitHub**: [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher)
- **Architecture**: `Planner → Parallel Execution Agents → Aggregator → Report Writer`
- **Relevance**: We plan to adopt the **Recursive Depth** parameter.

### **4. FlowSearch (InternAgent)**
- **GitHub**: [InternScience/InternAgent](https://github.com/InternScience/InternAgent)
- **Paper**: [FlowSearch: Advancing deep research with dynamic structured knowledge flow](https://arxiv.org/abs/2510.08521)
- **Architecture**:
  - **Dynamic Knowledge Flow**: Active construction and evolution of a structured flow graph (DAG).
  - **Hierarchical Decomposition**: Breaks tasks down into sub-flows based on intermediate findings.
- **Relevance**: Aligns with our goal for a "Dynamic DAG" planner that evolves during execution.

### **5. ManuSearch (RUCAIBox)**
- **GitHub**: [RUCAIBox/ManuSearch](https://github.com/RUCAIBox/ManuSearch)
- **Paper**: [ManuSearch: Democratizing Deep Search in Large Language Models](https://arxiv.org/abs/2505.18105)
- **Architecture**: 3-Agent Collaborative Framework:
  1.  **Solution Planner**: Iteratively formulates sub-queries.
  2.  **Internet Searcher**: Retrieves documents via real-time search.
  3.  **Webpage Reader**: Extracts structured evidence from raw content.
- **Relevance**: The "Webpage Reader" agent concept aligns with our need for better content extraction.

## 2. Industry & Academic Frameworks

### **RhinoInsight**
- **Paper**: [RhinoInsight: Improving Deep Research through Control Mechanisms for Model Behavior and Context](https://arxiv.org/abs/2511.18743)
- **Key Contribution**: Control mechanisms for verification and context management.
- **Relevance**: Validates our focus on "Checklist-based Verification" and strict context auditing.

### **TTD-DR (Test-Time Denoising)**
- **Concept**: Diffusion-based reasoning where "noisy" initial drafts are iteratively "denoised" (refined) into a final high-quality answer.
- **Reference**: Applied in domains like [Controllable Traffic Generation](https://ieeexplore.ieee.org/document/10161463) and emerging reasoning agents.
- **Implementation Pattern**:
  ```python
  drafts = generate_variants(query)
  refined = [denoise(d) for d in drafts]
  final = select_best(refined)
  ```

## 3. Verified Benchmarks

### **DeepResearch-Bench**
- **Source**: [HuggingFace Leaderboard (muset-ai)](https://huggingface.co/spaces/muset-ai/DeepResearch-Bench-Leaderboard)
- **Metrics**: Pass@1, Citation Quality.

### **ORION (ManuSearch Benchmark)**
- **Source**: [HuggingFace Dataset (RUC-AIBOX)](https://huggingface.co/datasets/RUC-AIBOX/ORION)
- **Focus**: Open-web reasoning over long-tail entities.

## 4. Integration Roadmap

| Feature | Inspired By | Priority | Implementation Plan |
| :--- | :--- | :--- | :--- |
| **Recursive Depth** | GPT Researcher | High | Allow `web_research` to spawn sub-tasks |
| **Outline Generation** | STORM | Medium | Add `outline_node` before research loop |
| **Dynamic Flow** | FlowSearch | Medium | Implement "Graph Expansion" logic in planner |
| **Structured Reading** | ManuSearch | Medium | Create a dedicated `ContentReader` tool/node |
