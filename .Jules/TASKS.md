# Jules Remote Task Backlog

Use the following commands to delegate these specific integration tasks to Jules. Each task corresponds to high-priority TODOs in the codebase.

## 1. Recursive Research Trigger
**Task**: Implement the logic to trigger recursive sub-topic research.
**Command**:
```bash
jules remote new --session "Implement recursive research trigger: Update reflection or update_plan nodes in backend/src/agent/nodes.py to identify sub-topics and set 'subtopic_query' in the state. Wire conditional edges in graph.py to research_subgraph."
```

## 2. Gemma Interface Standardization
**Task**: Create a seamless adapter for swapping between Gemini and Gemma.
**Command**:
```bash
jules remote new --session "Standardize Gemma interface: Implement a GemmaAdapter in backend/src/agent/llm_client.py that handles the Thought-Action parsing (using tool_adapter.py) so Gemma can be used interchangeably with Gemini in any node."
```

## 3. Benchmark Orchestration
**Task**: Complete the benchmarking script to measure agent performance.
**Command**:
```bash
jules remote new --session "Complete benchmark orchestration: Update backend/scripts/benchmark.py to load a test dataset, execute the agent graph, and use evaluators.py to report quality and groundedness scores."
```

## 4. Gemma Testing Suite
**Task**: Add robust testing for the new Gemma clients.
**Command**:
```bash
jules remote new --session "Implement Gemma tests: Create backend/tests/agent/test_gemma.py and add unit tests for VertexAIGemmaClient and OllamaGemmaClient. Test tool parsing compatibility and error handling."
```

---
**Note to Agent**: Refer to `AGENTS.md` for environment setup and `.Jules/antigravity.md` for project-specific logic.
