# Test Coverage Improvement Plan

## Current State (as of 2025-12-08)

### Backend Coverage: 55%

| Module | Coverage | Status |
|--------|----------|--------|
| `utils.py` | 100% | ✅ Complete |
| `configuration.py` | 100% | ✅ Complete |
| `tools_and_schemas.py` | 100% | ✅ Complete |
| `state.py` | 98% | ✅ Nearly complete |
| `persistence.py` | 93% | ✅ Good |
| `prompts.py` | 86% | ✅ Good |
| `graph.py` | 69% | ⚠️ Needs work |
| `rag_nodes.py` | 49% | ⚠️ Needs work |
| `_graph.py` | 0% | ❌ Not tested |
| `app.py` | 0% | ❌ Not tested |

### Frontend Coverage: 0%

- No test framework configured
- No test files exist
- No test scripts in `package.json`

---

## Phase 1: Backend Coverage to 85% (Priority: HIGH)

### 1.1 Add Property-Based Tests with Hypothesis

**Target:** `utils.py`, `graph.py` validation functions

```python
# Example: test_utils_hypothesis.py
from hypothesis import given, strategies as st
from agent.utils import insert_citation_markers, resolve_urls

@given(
    text=st.text(min_size=1, max_size=500),
    end_indices=st.lists(st.integers(min_value=0, max_value=500), max_size=5)
)
def test_insert_citation_never_raises(text, end_indices):
    citations = [{"end_index": idx, "segments": []} for idx in end_indices]
    # Should never raise, even with weird indices
    insert_citation_markers(text, citations)
```

**Files to create:**
- `tests/test_utils_hypothesis.py`
- `tests/test_graph_hypothesis.py`

### 1.2 Mock LLM Calls in graph.py

**Target:** Cover `generate_query`, `web_research`, `reflection`, `finalize_answer`

```python
# Example: test_graph_nodes.py
from unittest.mock import Mock, patch

@patch('agent.graph.ChatGoogleGenerativeAI')
@patch('agent.graph.genai_client')
def test_generate_query_returns_queries(mock_genai, mock_llm):
    mock_llm.return_value.with_structured_output.return_value.invoke.return_value = Mock(
        query=["query1", "query2"]
    )
    state = {"messages": [{"content": "test"}], "initial_search_query_count": 2}
    result = generate_query(state, config={"configurable": {}})
    assert "search_query" in result
```

**Functions to cover:**
- [ ] `generate_query` - Mock LLM, verify query extraction
- [ ] `web_research` - Mock genai_client, verify citation processing
- [ ] `reflection` - Mock LLM, verify is_sufficient logic
- [ ] `finalize_answer` - Mock LLM, verify URL replacement
- [ ] `load_context` - Mock persistence, verify state loading

### 1.3 Cover rag_nodes.py Retrieval Logic

**Target:** `rag_retrieve` with mocked RAG backend

```python
@patch('agent.rag_nodes.rag_backend')
def test_rag_retrieve_returns_documents(mock_backend, monkeypatch):
    monkeypatch.setattr(rag_nodes, "is_rag_enabled", lambda: True)
    mock_backend.retrieve.return_value = ["doc1", "doc2"]
    
    result = rag_nodes.rag_retrieve({"messages": [], "rag_resources": ["uri"]}, config=None)
    assert result["rag_documents"] == ["doc1", "doc2"]
```

### 1.4 Cover _graph.py (Alternative Multi-Provider Graph)

**Target:** Basic smoke tests for the alternative graph implementation

- [ ] `check_api_keys` - Test with/without env vars
- [ ] `generate_query` - Mock LLMFactory
- [ ] `web_research` - Mock web_search_tool
- [ ] `reflection` - Mock LLMFactory
- [ ] `evaluate_research` - Test routing logic
- [ ] `finalize_answer` - Mock LLMFactory

### 1.5 Cover app.py (FastAPI Entry Point)

**Target:** Basic endpoint tests

```python
from fastapi.testclient import TestClient
from agent.app import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
```

---

## Phase 2: Frontend Testing with Vitest (Priority: MEDIUM)

### 2.1 Install Dependencies

```bash
cd frontend
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom @vitest/coverage-v8
```

### 2.2 Configure Vitest

**Create `vitest.config.ts`:**
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react-swc';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    coverage: {
      reporter: ['text', 'html'],
      exclude: ['node_modules/', 'src/test/'],
    },
  },
});
```

**Create `src/test/setup.ts`:**
```typescript
import '@testing-library/jest-dom';
```

### 2.3 Add Test Scripts to package.json

```json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest --coverage"
  }
}
```

### 2.4 Create Component Tests

**Priority components to test:**
1. `ChatInput.tsx` - User input handling
2. `MessageList.tsx` - Message rendering
3. `SourcesList.tsx` - Sources display
4. `PlanningSteps.tsx` - Planning UI (if exists)

**Example test:**
```typescript
// src/components/ChatInput.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatInput } from './ChatInput';

describe('ChatInput', () => {
  it('renders input field', () => {
    render(<ChatInput onSubmit={() => {}} />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('calls onSubmit when form is submitted', () => {
    const mockSubmit = vi.fn();
    render(<ChatInput onSubmit={mockSubmit} />);
    
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'test' } });
    fireEvent.submit(screen.getByRole('form'));
    
    expect(mockSubmit).toHaveBeenCalledWith('test');
  });
});
```

---

## Phase 3: Integration from Examples (Priority: MEDIUM)

### 3.1 Reference Implementations

From `examples/open_deep_research_example/src/open_deep_research/`:
- `tavily_search` - Search tool implementation
- `think_tool` - Reflection tool
- `summarize_webpage` - Content summarization
- `compress_research` - Research compression

From `examples/thinkdepthai_deep_research_example/src/`:
- `tavily_search_multiple` - Batch search
- `deduplicate_search_results` - Deduplication logic
- `process_search_results` - Result processing
- `refine_draft_report` - Report refinement

### 3.2 Functions to Port/Test

| Function | Source | Target |
|----------|--------|--------|
| `tavily_search` | open_deep_research | `agent/tools/search.py` |
| `think_tool` | open_deep_research | `agent/tools/reflection.py` |
| `summarize_webpage` | open_deep_research | `agent/utils.py` |
| `deduplicate_search_results` | thinkdepthai | `agent/utils.py` |

---

## Phase 4: CI/CD Integration (Priority: LOW)

### 4.1 GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -e backend[test]
      - run: pytest --cov=backend/src/agent --cov-fail-under=85

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: cd frontend && npm ci && npm test
```

### 4.2 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest backend/tests -q
        language: system
        pass_filenames: false
```

---

## Timeline Estimate

| Phase | Effort | Target Coverage |
|-------|--------|-----------------|
| Phase 1.1-1.2 | 2-3 hours | 70% |
| Phase 1.3-1.5 | 2-3 hours | 85% |
| Phase 2 | 3-4 hours | Frontend 60% |
| Phase 3 | 4-6 hours | Additional utilities |
| Phase 4 | 1-2 hours | CI/CD automation |

**Total estimated effort: 12-18 hours**

---

## Next Actions

1. ✅ Install `pytest-cov` and `hypothesis`
2. ⬜ Create `test_graph_nodes.py` with mocked LLM tests
3. ⬜ Create `test_utils_hypothesis.py` with property tests
4. ⬜ Set up Vitest in frontend
5. ⬜ Create basic frontend component tests
6. ⬜ Add CI workflow
