# Tasks: SOTA Deep Research Integration

## Status: 🔴 Not Started

This task list tracks the integration of features from verified state-of-the-art (SOTA) research agents: **Open Deep Research**, **STORM**, **FlowSearch**, **ManuSearch**, and **GPT Researcher**.

## 1. Scoping & Clarification (Open Deep Research)
*Goal: Prevent "garbage in, garbage out" by ensuring the agent understands the user's intent.*

- [ ] **Implement `scoping_node`** (See `docs/tasks/05_IMPLEMENTATION_GUIDE.md` for detailed flow)
    - [x] **State**: Define `ScopingState` (query, clarifications_needed, user_answers).
        - Implemented in `backend/src/agent/state.py` (inherits from `TypedDict` with `total=False`).
        - `OverallState` extends `ScopingState` and includes `plan: List[Todo]`.
    - [ ] **Logic**: Analyze input query. If ambiguous, generate clarifying questions and interrupt graph.
    - [ ] **Integration**: Place before `planning_mode` in the main graph.

## 2. Dynamic Flow & Outlines (FlowSearch / STORM)
*Goal: Move from linear search to dynamic, structured research.*

- [ ] **Implement `outline_gen` Node (STORM)**
    - [ ] **Input**: Refined user query + initial context.
    - [ ] **Logic**: Generate a hierarchical `Outline` (Sections -> Subsections).
    - [ ] **Output**: Populate `OverallState.outline`.
- [ ] **Implement `flow_update` Node (FlowSearch)**
    - [ ] **Input**: Current `todo_list` + `web_research_results`.
    - [ ] **Logic**: Analyze findings. Decide to (a) Mark task done, (b) Add new tasks (DAG expansion), (c) Refine existing tasks.
    - [ ] **Output**: Updated `todo_list` (DAG structure).

## 3. Structured Content Reading (ManuSearch)
*Goal: Improve evidence extraction from raw web pages.*

- [ ] **Implement `content_reader` Node**
    - [ ] **Input**: Raw HTML/Text from search.
    - [ ] **Logic**: Use LLM to extract structured `Evidence` items (Claim, Source URL, Context Snippet).
    - [ ] **Output**: List of `Evidence` objects appended to `OverallState.evidence_bank`.

## 4. Recursive Research (GPT Researcher)
*Goal: Handle depth by allowing the agent to "dive deep".*

- [ ] **Implement `research_subgraph` Node**
    - [ ] **Input**: A sub-topic query.
    - [ ] **Logic**: Compile and run a fresh instance of the `ResearchGraph` (recursive call).
    - [ ] **Output**: A summarized markdown report for that sub-topic.

## 5. Verification & Refinement (RhinoInsight / TTD-DR)
*Goal: Ensure high fidelity.*

- [ ] **Implement `checklist_verifier` Node**
    - [ ] **Logic**: Audit the `evidence_bank` against the `outline` requirements. Flag missing citations.
- [ ] **Implement `denoising_refiner` Node**
    - [ ] **Logic**: Generate $N$ draft answers, critique them, and synthesize the best components.

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
