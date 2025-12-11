# Model Usage Analysis

**Generated:** 2025-12-11 14:25 AEDT  
**Project:** gemini-fullstack-langgraph-quickstart

---

## Overview

This document catalogs all AI model definitions and usage across the project, including configuration defaults, runtime usage, and frontend references.

---

## Configuration Defaults

### Backend Configuration (`backend/src/agent/configuration.py`)

```python
class Configuration(BaseModel):
    query_generator_model: str = Field(
        default="gemini-1.5-flash",  # ← Default for query generation
        json_schema_extra={
            "description": "The name of the language model to use for the agent's query generation."
        },
    )

    reflection_model: str = Field(
        default="gemini-1.5-flash",  # ← Default for reflection/reasoning
        json_schema_extra={
            "description": "The name of the language model to use for the agent's reflection."
        },
    )

    answer_model: str = Field(
        default="gemini-1.5-pro",  # ← Default for final answer synthesis
        json_schema_extra={
            "description": "The name of the language model to use for the agent's answer."
        },
    )
```

**Configuration Loading:**
- Values can be overridden via:
  1. `RunnableConfig` configurable dict
  2. Environment variables (uppercase field names)
  3. Defaults to field defaults if not specified

---

## Runtime Model Usage

### 1. Query Generation (`backend/src/agent/nodes.py:generate_query`)

**Location:** Lines 64-109  
**Model Used:** `configurable.query_generator_model`  
**Default:** `gemini-1.5-flash`

```python
llm = ChatGoogleGenerativeAI(
    model=configurable.query_generator_model,  # ← Runtime configurable
    temperature=1.0,
    max_retries=2,
    api_key=os.getenv("GEMINI_API_KEY"),
)
structured_llm = llm.with_structured_output(SearchQueryList)
```

**Purpose:** Generates initial search queries from user's question  
**Output:** Structured list of search queries  
**Temperature:** 1.0 (creative query generation)

---

### 2. Web Research (`backend/src/agent/nodes.py:web_research`)

**Location:** Lines 140-220  
**Model Used:** `configurable.query_generator_model`  
**Default:** `gemini-1.5-flash`

```python
response = genai_client.models.generate_content(
    model=configurable.query_generator_model,  # ← Same as query generation
    contents=formatted_prompt,
    config={
        "tools": [{"google_search": {}}],
        "temperature": 0,
    },
)
```

**Purpose:** Performs web research using Google Search tool  
**Output:** Grounded search results with citations  
**Temperature:** 0 (factual, deterministic)  
**Special:** Uses `google.genai.Client` directly (not LangChain) for grounding metadata

---

### 3. Reflection (`backend/src/agent/nodes.py:reflection`)

**Location:** Lines 474-524  
**Model Used:** `state.get("reasoning_model", configurable.reflection_model)`  
**Default:** `gemini-1.5-flash`  
**Override:** Can be set via `state["reasoning_model"]`

```python
reasoning_model = state.get("reasoning_model", configurable.reflection_model)

llm = ChatGoogleGenerativeAI(
    model=reasoning_model,  # ← State override or config default
    temperature=1.0,
    max_retries=2,
    api_key=os.getenv("GEMINI_API_KEY"),
)
result = llm.with_structured_output(Reflection).invoke(formatted_prompt, config=config)
```

**Purpose:** Evaluates research coverage and generates follow-up queries  
**Output:** Structured reflection with `is_sufficient` flag and follow-up queries  
**Temperature:** 1.0 (creative gap analysis)

---

### 4. Final Answer (`backend/src/agent/nodes.py:finalize_answer`)

**Location:** Lines 569-623  
**Model Used:** `state.get("reasoning_model") or configurable.answer_model`  
**Default:** `gemini-1.5-pro`  
**Override:** Can be set via `state["reasoning_model"]`

```python
reasoning_model = state.get("reasoning_model") or configurable.answer_model

llm = ChatGoogleGenerativeAI(
    model=reasoning_model,  # ← State override or config default (pro model)
    temperature=0,
    max_retries=2,
    api_key=os.getenv("GEMINI_API_KEY"),
)
result = llm.invoke(formatted_prompt)
```

**Purpose:** Synthesizes final research answer with citations  
**Output:** Formatted answer with deduplicated sources  
**Temperature:** 0 (factual, deterministic)  
**Note:** Uses higher-capability `gemini-1.5-pro` by default

---

## Frontend Model Configuration

### Default Model (`frontend/src/hooks/useAgentState.ts`)

**Location:** Lines 24-28

```typescript
const lastConfigRef = useRef({
  initial_search_query_count: 1,
  max_research_loops: 1,
  reasoning_model: "gemini-2.5-flash-preview-04-17",  // ← Frontend default
});
```

**Usage:** Sent to backend in request configuration  
**Note:** This overrides backend defaults when set

### Model Selection in Frontend

**Location:** Lines 30-35 (type definition)

```typescript
const thread = useStream<{
  messages: Message[];
  initial_search_query_count: number;
  max_research_loops: number;
  reasoning_model: string;  // ← Can be configured per request
}>({
  // ...
});
```

**Submission:** Lines 168-193 (handleSubmit function)

```typescript
const config = {
  initial_search_query_count,
  max_research_loops,
  reasoning_model: model,  // ← Passed from UI
};
lastConfigRef.current = config;
thread.submit({
  messages: newMessages,
  ...config,
});
```

---

## Research Tools (`backend/src/agent/research_tools.py`)

### Hardcoded Model Usage

**Location:** Line 445

```python
writer_model = init_chat_model(model="gemini-1.5-pro", max_tokens=16000)
```

**Purpose:** Used in research tools for content generation  
**Note:** Hardcoded, not configurable

### Token Limits Mapping

**Location:** Lines 524-529

```python
MODEL_TOKEN_LIMITS = {
    "google:gemini-1.5-pro": 2097152,
    "google:gemini-1.5-flash": 1048576,
    "google:gemini-2.0-flash": 1048576,
    "gemini-1.5-pro": 2097152,
    "gemini-1.5-flash": 1048576,
    "gemini-2.0-flash-exp": 1048576,
}
```

**Purpose:** Token limit lookup for different model variants  
**Usage:** `get_model_token_limit(model_name)` function

---

## Model Usage Summary

### By Node/Function

| Node/Function | Config Field | Default Model | Temperature | Purpose |
|--------------|--------------|---------------|-------------|---------|
| `generate_query` | `query_generator_model` | `gemini-1.5-flash` | 1.0 | Generate search queries |
| `web_research` | `query_generator_model` | `gemini-1.5-flash` | 0 | Web search with grounding |
| `reflection` | `reflection_model` | `gemini-1.5-flash` | 1.0 | Evaluate coverage, generate follow-ups |
| `finalize_answer` | `answer_model` | `gemini-1.5-pro` | 0 | Synthesize final answer |
| Research Tools | Hardcoded | `gemini-1.5-pro` | N/A | Content generation in tools |

### Model Variants in Use

**Production Models:**
- `gemini-1.5-flash` - Fast, efficient (query gen, reflection, web research)
- `gemini-1.5-pro` - Higher capability (final answer, research tools)

**Preview/Experimental Models:**
- `gemini-2.5-flash-preview-04-17` - Frontend default (preview version)
- `gemini-2.0-flash-exp` - Experimental (in token limits)
- `gemini-2.0-flash` - Newer flash variant (in token limits)

**Legacy/Build Artifacts:**
- Build directory shows older defaults: `gemini-2.0-flash`, `gemini-2.5-flash`, `gemini-2.5-pro`

---

## Configuration Override Hierarchy

**Priority (highest to lowest):**

1. **State Override** (`state["reasoning_model"]`)
   - Used in `reflection` and `finalize_answer`
   - Allows per-execution model selection

2. **RunnableConfig** (`config["configurable"][field_name]`)
   - Passed from frontend or API calls
   - Overrides defaults for entire execution

3. **Environment Variables** (`os.environ[FIELD_NAME.upper()]`)
   - System-wide defaults
   - Example: `QUERY_GENERATOR_MODEL=gemini-2.0-flash`

4. **Field Defaults** (Configuration class)
   - Fallback if nothing else specified
   - `gemini-1.5-flash` for most, `gemini-1.5-pro` for answer

---

## Environment Variables

### Required
- `GEMINI_API_KEY` - API key for all Gemini model calls

### Optional (Configuration Overrides)
- `QUERY_GENERATOR_MODEL` - Override query generation model
- `REFLECTION_MODEL` - Override reflection model
- `ANSWER_MODEL` - Override answer synthesis model
- `NUMBER_OF_INITIAL_QUERIES` - Number of initial search queries
- `MAX_RESEARCH_LOOPS` - Maximum research iterations
- `REQUIRE_PLANNING_CONFIRMATION` - Enable/disable planning confirmation

---

## Model Selection Recommendations

### Current Setup (Optimized for Cost/Performance)

**Fast Operations (Flash):**
- Query generation: `gemini-1.5-flash` ✓
- Web research: `gemini-1.5-flash` ✓
- Reflection: `gemini-1.5-flash` ✓

**Quality-Critical (Pro):**
- Final answer: `gemini-1.5-pro` ✓

### Alternative Configurations

**Maximum Quality:**
```python
query_generator_model = "gemini-1.5-pro"
reflection_model = "gemini-1.5-pro"
answer_model = "gemini-1.5-pro"
```

**Maximum Speed:**
```python
query_generator_model = "gemini-1.5-flash"
reflection_model = "gemini-1.5-flash"
answer_model = "gemini-1.5-flash"
```

**Experimental (Latest Features):**
```python
query_generator_model = "gemini-2.0-flash"
reflection_model = "gemini-2.0-flash"
answer_model = "gemini-2.5-pro"  # If available
```

---

## Testing Configuration

### Test Defaults (`backend/tests/test_configuration.py`)

```python
assert config.query_generator_model == "gemini-1.5-flash"
assert config.reflection_model == "gemini-1.5-flash"
assert config.answer_model == "gemini-1.5-pro"
```

**Tests verify:**
- Default values are correct
- Environment variable overrides work
- RunnableConfig overrides work
- Type conversions (bool, int) work correctly

---

## Migration Notes

### From Build Artifacts (Older Versions)

**Old Defaults (build/lib/agent/configuration.py):**
```python
query_generator_model: default="gemini-2.0-flash"
reflection_model: default="gemini-2.5-flash"
answer_model: default="gemini-2.5-pro"
```

**Current Defaults (src/agent/configuration.py):**
```python
query_generator_model: default="gemini-1.5-flash"
reflection_model: default="gemini-1.5-flash"
answer_model: default="gemini-1.5-pro"
```

**Reason for Change:** Likely reverted to stable 1.5 models from experimental 2.x versions

---

## Action Items

### Immediate
- [ ] Verify `gemini-2.5-flash-preview-04-17` (frontend default) is valid/available
- [ ] Consider standardizing frontend and backend defaults
- [ ] Document model selection strategy in main README

### Future
- [ ] Add model validation on startup
- [ ] Implement model fallback logic if primary model unavailable
- [ ] Add model performance/cost tracking
- [ ] Consider adding model selection UI in frontend
- [ ] Update token limits for newer models (2.5-pro, 2.0-flash)

---

## Related Files

**Configuration:**
- `backend/src/agent/configuration.py` - Main configuration class
- `frontend/src/hooks/useAgentState.ts` - Frontend model selection

**Usage:**
- `backend/src/agent/nodes.py` - All node implementations
- `backend/src/agent/research_tools.py` - Research tool models

**Testing:**
- `backend/tests/test_configuration.py` - Configuration tests
- `backend/tests/test_research_tools.py` - Token limit tests

**Build Artifacts (Historical):**
- `backend/build/lib/agent/configuration.py` - Old defaults
- `backend/htmlcov/` - Coverage reports (ignore)
