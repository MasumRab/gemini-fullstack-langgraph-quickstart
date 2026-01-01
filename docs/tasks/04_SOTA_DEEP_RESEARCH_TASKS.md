# Tasks: SOTA Deep Research Integration

## Status: 🟡 In Progress (Significant Progress)

This task list tracks the integration of features from verified state-of-the-art (SOTA) research agents: **Open Deep Research**, **STORM**, **FlowSearch**, **ManuSearch**, and **GPT Researcher**.

## 1. Scoping & Clarification (Open Deep Research)
*Goal: Prevent "garbage in, garbage out" by ensuring the agent understands the user's intent.*

- [x] **Implement `scoping_node`**
    - [x] **State**: Define `ScopingState` (query, clarifications_needed, user_answers).
    - [x] **Logic**: Analyze input query. If ambiguous, generate clarifying questions and interrupt graph.
    - [x] **Integration**: Place before `planning_mode` in the main graph.

## 2. Dynamic Flow & Outlines (FlowSearch / STORM)
*Goal: Move from linear search to dynamic, structured research.*

- [x] **Implement `outline_gen` Node (STORM)**
    - [x] **Input**: Refined user query + initial context.
    - [x] **Logic**: Generate a hierarchical `Outline` (Sections -> Subsections).
    - [x] **Output**: Populate `OverallState.outline`.
- [x] **Implement `flow_update` Node (FlowSearch)**
    - [x] **Input**: Current `todo_list` + `web_research_results`.
    - [x] **Logic**: Analyze findings. Decide to (a) Mark task done, (b) Add new tasks (DAG expansion), (c) Refine existing tasks.
    - [x] **Output**: Updated `todo_list` (Implemented as `update_plan`).

## 3. Structured Content Reading (ManuSearch)
*Goal: Improve evidence extraction from raw web pages.*

- [x] **Implement `content_reader` Node**
    - [x] **Input**: Raw HTML/Text from search.
    - [x] **Logic**: Use LLM to extract structured `Evidence` items (Claim, Source URL, Context Snippet).
    - [x] **Output**: List of `Evidence` objects appended to `OverallState.evidence_bank`.

## 4. Recursive Research (GPT Researcher)
*Goal: Handle depth by allowing the agent to "dive deep".*

- [ ] **Implement `research_subgraph` Node**
    - [ ] **Input**: A sub-topic query.
    - [ ] **Logic**: Compile and run a fresh instance of the `ResearchGraph` (recursive call).
    - [ ] **Output**: A summarized markdown report for that sub-topic.

## 5. Verification & Refinement (RhinoInsight / TTD-DR)
*Goal: Ensure high fidelity.*

- [x] **Implement `checklist_verifier` Node (RhinoInsight)**
    - [x] **Logic**: Audit the `evidence_bank` against the `outline` requirements. Flag missing citations.
- [x] **Implement `denoising_refiner` Node (TTD-DR)**
    - [x] **Logic**: Generate multiple draft answers and synthesize the best components.

## 6. Benchmarking
*Goal: Validate performance.*

- [ ] **MLE-bench Integration**
    - [ ] Evaluate agent performance on a subset of Kaggle engineering tasks.
- [ ] **DeepResearch-Bench Setup**
    - [ ] Load tasks from the `DeepResearch-Bench` (muset-ai) space.

## 7. Model Agnostic Infrastructure (Gemma Integration)
*Goal: Ensure the agent graph can execute with open-weight models (Gemma) alongside API models (Gemini).*

- [x] **Gemma Tool Adapter**
    - [x] **Logic**: Models like Gemma 3 do not support native `bind_tools`. We implemented an adapter in `backend/src/agent/tool_adapter.py`.
    - [x] **Mechanism**:
        - Detect Gemma models via `agent.models.is_gemma_model`.
        - Format tools as JSON schemas and inject into the system prompt.
        - Instruct the model to output tool calls as strict JSON in markdown blocks.
        - Manually parse the text response into `AIMessage.tool_calls` for downstream compatibility.
    - [x] **Usage**: Applied in `generate_query` node to support `SearchQueryList` structured output and MCP tools.
