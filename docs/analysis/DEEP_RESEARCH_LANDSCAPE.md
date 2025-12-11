# Deep Research Landscape & Implementation Reference

This document maps the current landscape of "Deep Research" agents, verified open-source implementations, and academic frameworks. It serves as a reference for architectural decisions in this project.

## 1. Open Source Implementations (Verified)

### **1. Open Deep Research (LangChain)**
- **GitHub**: [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research)
- **Architecture**: `Scope → Research → Write`
- **Key Concepts**:
  - **Plan-and-Execute**: Separation of planning (scoping) from execution.
  - **Refinement Loops**: The "Research" phase is iterative, generating queries based on gaps.
- **Relevance**: We are adopting the "Scoping" phase (clarifying user intent) as a high priority.

### **2. STORM (Stanford)**
- **GitHub**: [stanford-oval/storm](https://github.com/stanford-oval/storm)
- **Architecture**: `Perspective Discovery → Outline Generation → Multi-Agent Conversation → Article Writing`
- **Key Concepts**:
  - **Perspective-Guided QA**: Adopts specific personas (e.g., "Economist") to ask questions.
  - **Simulated Conversation**: A "Writer" agent interviews an "Expert" agent.
- **Relevance**: High value for our "Long-term Planning" goal. We plan to implement an **Outline Generation Node**.

### **3. GPT Researcher**
- **GitHub**: [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher)
- **Architecture**: `Planner → Parallel Execution Agents → Aggregator → Report Writer`
- **Key Concepts**:
  - **Recursive "Deep Research"**: A tree-like exploration (BFS/DFS) of sub-topics.
- **Relevance**: We plan to adopt the **Recursive Depth** parameter.

### **4. ManuSearch (RUCAIBox)**
- **GitHub**: [RUCAIBox/ManuSearch](https://github.com/RUCAIBox/ManuSearch)
- **Paper**: "ManuSearch: Democratizing Deep Search in Large Language Models"
- **Architecture**: 3-Agent Collaborative Framework:
  1.  **Solution Planner**: Iteratively formulates sub-queries.
  2.  **Internet Searcher**: Retrieves documents via real-time search.
  3.  **Webpage Reader**: Extracts structured evidence from raw content.
- **Benchmark**: Introduces `ORION` (Open-Web Reasoning) benchmark.
- **Relevance**: The "Webpage Reader" agent concept aligns with our need for better content extraction from search results.

## 2. Industry & Academic Frameworks

### **Co-STORM (Human-in-the-Loop)**
- **Concept**: An evolution of STORM where the human acts as one of the "experts" or the "moderator".
- **Relevance**: Aligning `planning_wait` with this pattern allows users to inject knowledge during the loop.

### **Test-Time Denoising / Diffusion Approaches** (Conceptual)
- **Concept**: While a specific "TTD-DR" repo remains elusive, the concept of generating multiple "noisy" answer variants and iteratively "denoising" (refining) them via self-critique is a valid SOTA pattern.
- **Implementation**:
  ```python
  variants = [generate_answer(query) for _ in range(5)]
  critiques = [critique(v) for v in variants]
  final = synthesize(variants, critiques)
  ```

## 3. Verified Benchmarks

### **DeepResearch-Bench**
- **Source**: [HuggingFace Leaderboard (muset-ai)](https://huggingface.co/spaces/muset-ai/DeepResearch-Bench-Leaderboard)
- **Metrics**:
  - **Pass@1**: Does the report answer the core question?
  - **Citation Quality**: Are sources real and relevant?

### **ORION (ManuSearch Benchmark)**
- **Source**: [HuggingFace Dataset (RUC-AIBOX)](https://huggingface.co/datasets/RUC-AIBOX/ORION)
- **Focus**: Open-web reasoning over long-tail entities.

## 4. Integration Roadmap

| Feature | Inspired By | Priority | Implementation Plan |
| :--- | :--- | :--- | :--- |
| **Recursive Depth** | GPT Researcher | High | Allow `web_research` to spawn sub-tasks |
| **Outline Generation** | STORM | Medium | Add `outline_node` before research loop |
| **Scoping Phase** | Open Deep Research | High | Add "Clarification" step before Plan approval |
| **Structured Reading** | ManuSearch | Medium | Create a dedicated `ContentReader` tool/node |
