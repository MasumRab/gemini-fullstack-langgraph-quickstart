# Deep Research Landscape & Implementation Reference

This document maps the current landscape of "Deep Research" agents, verified open-source implementations, and academic frameworks. It serves as a reference for architectural decisions in this project.

## 1. Open Source Implementations (Verified)

### **1. Open Deep Research (LangChain)**
- **GitHub**: [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research)
- **Architecture**: `Scope → Research → Write`
- **Key Concepts**:
  - **Plan-and-Execute**: Separation of planning (scoping) from execution.
  - **Refinement Loops**: The "Research" phase is iterative, generating queries based on gaps.
  - **Conflict Resolution**: Uses a "Reflection" step to verify claims.
- **Relevance to Us**:
  - We already implement a variant of this with our `planning_mode` and `web_research` nodes.
  - *Gap*: We lack the formal "Scoping" phase (clarifying user intent before starting).

### **2. STORM (Stanford)**
- **GitHub**: [stanford-oval/storm](https://github.com/stanford-oval/storm)
- **Paper**: "Assisting in Writing Wikipedia-like Articles From Scratch with Large Language Models"
- **Architecture**: `Perspective Discovery → Outline Generation → Multi-Agent Conversation → Article Writing`
- **Key Concepts**:
  - **Perspective-Guided QA**: Instead of generic queries, it adopts specific personas (e.g., "Economist", "Historian") to ask questions.
  - **Simulated Conversation**: A "Writer" agent interviews an "Expert" agent to gather depth.
  - **Outline-Driven**: Research is strictly bounded by a generated outline.
- **Relevance to Us**:
  - High value for our "Long-term Planning" goal. We should implement an **Outline Generation Node**.

### **3. GPT Researcher**
- **GitHub**: [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher)
- **Architecture**: `Planner → Parallel Execution Agents → Aggregator → Report Writer`
- **Key Concepts**:
  - **Parallelization**: Speed is achieved by running search queries concurrently.
  - **Recursive "Deep Research"**: A tree-like exploration (BFS/DFS) of sub-topics.
  - **Context-Aware**: Maintains a "global context" of findings to prevent duplicate work.
- **Relevance to Us**:
  - We currently use `Send()` for parallelization, similar to this pattern.
  - We should adopt the **Recursive Depth** parameter (e.g., research sub-topics of the main plan).

## 2. Industry & Academic Frameworks

### **4. Co-STORM (Human-in-the-Loop)**
- **Concept**: an evolution of STORM where the human acts as one of the "experts" or the "moderator".
- **Relevance**: Directly aligns with our `planning_wait` and interactive chat goals. The user should be able to inject "knowledge" during the research loop, not just at the start.

### **5. Self-Refining Agents (Reflexion)**
- **Concept**: Agents that critique their own output and generate a "refined" version.
- **Implementation**:
  ```python
  draft = generate(query)
  critique = evaluate(draft)
  final = refine(draft, critique)
  ```
- **Relevance**: Our `reflection` node is a basic version of this. We can enhance it with a formal "Critique" prompt that checks for missing citations specifically.

## 3. Verified Benchmarks

### **DeepResearch-Bench**
- **Source**: [HuggingFace Leaderboard](https://huggingface.co/spaces/Ayanami0730/DeepResearch-Leaderboard) (Maintained by Ayanami0730/LangChain community members, widely used by Open Deep Research).
- **Metrics**:
  - **Pass@1**: Does the report answer the core question?
  - **Citation Quality**: Are sources real and relevant?
  - **Hallucination Rate**: Frequency of unsupported claims.

### **GAIA (General AI Assistants)**
- **Focus**: Multi-step reasoning and tool use.
- **Relevance**: Good for testing the "Planning" aspect of our agent.

## 4. Integration Roadmap

| Feature | Inspired By | Priority | Implementation Plan |
| :--- | :--- | :--- | :--- |
| **Recursive Depth** | GPT Researcher | High | Allow `web_research` to spawn sub-tasks |
| **Outline Generation** | STORM | Medium | Add `outline_node` before research loop |
| **Perspective QA** | STORM | Low | Add `persona` generation to query rewriting |
| **Scoping Phase** | Open Deep Research | High | Add "Clarification" step before Plan approval |
