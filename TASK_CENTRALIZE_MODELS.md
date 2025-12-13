# Task: Centralize Model Configuration

**Priority**: 🔴 HIGH  
**Created**: 2025-12-12  
**Status**: 📋 TODO

---

## Objective

Remove all hardcoded model strings from the codebase and centralize model definitions in a single configuration file. This will:
- ✅ Make model updates easier (change once, apply everywhere)
- ✅ Support multiple model providers (Gemini, Gemma, Claude, etc.)
- ✅ Enable environment-specific defaults (prod, test, dev)
- ✅ Improve maintainability and reduce errors

---

## Current State Analysis

### Hardcoded Model References Found In:

1. **Configuration Files**
   - `backend/src/agent/configuration.py` - Default model strings
   - `backend/src/config/app_config.py` - Environment-based config

2. **Test Files**
   - `backend/tests/test_nodes.py` - Test fixtures with model names
   - `backend/tests/test_graph_mock.py` - Mock configurations
   - `backend/tests/test_configuration.py` - Configuration tests
   - All notebook files (`.ipynb`) - Example model references

3. **Source Code**
   - `backend/src/agent/research_tools.py` - MODEL_TOKEN_LIMITS dictionary
   - `backend/src/agent/nodes.py` - Potential inline model references
   - `backend/src/agent/rag.py` - Potential inline model references
   - `update_models.py` - Migration script with hardcoded models

4. **Frontend**
   - `frontend/src/components/InputForm.tsx` - Model selector dropdown
   - `frontend/src/hooks/useAgentState.ts` - Default model state

---

## Proposed Solution

### Phase 1: Create Centralized Model Registry

**File**: `backend/src/models/registry.py`

```python
"""
Centralized model registry for all AI models used in the application.
"""

from dataclasses import dataclass
from typing import Dict, Literal, Optional
from enum import Enum


class ModelProvider(str, Enum):
    """Supported model providers"""
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class ModelClass(str, Enum):
    """Model capability classes"""
    FAST = "fast"          # Quick responses, lower cost (Gemma, Flash-lite)
    BALANCED = "balanced"  # Balance of speed/quality (Flash, Haiku)
    PREMIUM = "premium"    # Highest quality (Pro, Opus)


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for a single model"""
    id: str
    provider: ModelProvider
    model_class: ModelClass
    token_limit: int
    cost_per_1k_tokens: float
    description: str
    supports_tools: bool = True
    supports_vision: bool = False


class ModelRegistry:
    """Registry of all available models"""
    
    # Gemini Models
    GEMINI_2_5_FLASH_LITE = ModelConfig(
        id="gemini-2.5-flash-lite",
        provider=ModelProvider.GOOGLE,
        model_class=ModelClass.FAST,
        token_limit=1048576,
        cost_per_1k_tokens=0.00005,
        description="Fastest Gemini model for testing and demos",
    )
    
    GEMINI_2_5_FLASH = ModelConfig(
        id="gemini-2.5-flash",
        provider=ModelProvider.GOOGLE,
        model_class=ModelClass.BALANCED,
        token_limit=1048576,
        cost_per_1k_tokens=0.0001,
        description="Balanced speed and quality",
    )
    
    GEMINI_2_5_PRO = ModelConfig(
        id="gemini-2.5-pro",
        provider=ModelProvider.GOOGLE,
        model_class=ModelClass.PREMIUM,
        token_limit=2097152,
        cost_per_1k_tokens=0.001,
        description="Highest quality reasoning",
    )
    
    # Gemma Models (for testing/demos)
    GEMMA_2_9B = ModelConfig(
        id="gemma-2-9b-it",
        provider=ModelProvider.GOOGLE,
        model_class=ModelClass.FAST,
        token_limit=8192,
        cost_per_1k_tokens=0.00001,
        description="Lightweight model for testing",
    )
    
    # Legacy support (optional, for backward compatibility)
    GEMINI_2_0_FLASH = ModelConfig(
        id="gemini-2.0-flash-exp",
        provider=ModelProvider.GOOGLE,
        model_class=ModelClass.BALANCED,
        token_limit=1048576,
        cost_per_1k_tokens=0.0001,
        description="Legacy experimental model",
    )
    
    @classmethod
    def get_model(cls, model_id: str) -> Optional[ModelConfig]:
        """Get model config by ID"""
        for attr in dir(cls):
            obj = getattr(cls, attr)
            if isinstance(obj, ModelConfig) and obj.id == model_id:
                return obj
        return None
    
    @classmethod
    def get_models_by_class(cls, model_class: ModelClass) -> list[ModelConfig]:
        """Get all models of a specific class"""
        return [
            getattr(cls, attr)
            for attr in dir(cls)
            if isinstance(getattr(cls, attr), ModelConfig)
            and getattr(cls, attr).model_class == model_class
        ]
    
    @classmethod
    def get_token_limits(cls) -> Dict[str, int]:
        """Get token limits dictionary (for backward compatibility)"""
        return {
            getattr(cls, attr).id: getattr(cls, attr).token_limit
            for attr in dir(cls)
            if isinstance(getattr(cls, attr), ModelConfig)
        }


# Default models for different environments
DEFAULT_MODELS = {
    "production": {
        "query_generator": ModelRegistry.GEMINI_2_5_FLASH_LITE.id,
        "reflection": ModelRegistry.GEMINI_2_5_FLASH.id,
        "answer": ModelRegistry.GEMINI_2_5_PRO.id,
        "research_tools": ModelRegistry.GEMINI_2_5_FLASH.id,
    },
    "testing": {
        "query_generator": ModelRegistry.GEMMA_2_9B.id,
        "reflection": ModelRegistry.GEMMA_2_9B.id,
        "answer": ModelRegistry.GEMMA_2_9B.id,
        "research_tools": ModelRegistry.GEMMA_2_9B.id,
    },
    "development": {
        "query_generator": ModelRegistry.GEMINI_2_5_FLASH_LITE.id,
        "reflection": ModelRegistry.GEMINI_2_5_FLASH.id,
        "answer": ModelRegistry.GEMINI_2_5_FLASH.id,
        "research_tools": ModelRegistry.GEMINI_2_5_FLASH.id,
    },
}


def get_default_models(environment: str = "production") -> Dict[str, str]:
    """Get default model IDs for the current environment"""
    return DEFAULT_MODELS.get(environment, DEFAULT_MODELS["production"])
```

---

### Phase 2: Update Configuration Files

**Changes to `backend/src/agent/configuration.py`:**

```python
from models.registry import ModelRegistry, get_default_models
import os

# Get environment (defaults to production)
ENV = os.getenv("APP_ENV", "production")
DEFAULTS = get_default_models(ENV)

class Configuration(BaseModel):
    """The configuration for the agent."""

    query_generator_model: str = Field(
        default=DEFAULTS["query_generator"],
        json_schema_extra={
            "description": "Model for query generation."
        },
    )

    reflection_model: str = Field(
        default=DEFAULTS["reflection"],
        json_schema_extra={
            "description": "Model for reflection."
        },
    )

    answer_model: str = Field(
        default=DEFAULTS["answer"],
        json_schema_extra={
            "description": "Model for final answer generation."
        },
    )
```

---

### Phase 3: Update All References

**Files to Update:**

#### Backend Source
- [ ] `backend/src/agent/research_tools.py`
  ```python
  from models.registry import ModelRegistry
  
  MODEL_TOKEN_LIMITS = ModelRegistry.get_token_limits()
  ```

- [ ] `backend/src/agent/nodes.py` - Search and replace inline model strings
- [ ] `backend/src/agent/rag.py` - Search and replace inline model strings
- [ ] `backend/src/config/app_config.py` - Use centralized defaults

#### Tests
- [ ] `backend/tests/test_nodes.py`
  ```python
  from models.registry import ModelRegistry, get_default_models
  
  DEFAULTS = get_default_models("testing")  # Use Gemma for tests
  
  @pytest.fixture
  def config():
      return RunnableConfig(
          configurable={
              "model": DEFAULTS["query_generator"],
              ...
          }
      )
  ```

- [ ] `backend/tests/test_graph_mock.py` - Use testing defaults
- [ ] `backend/tests/test_configuration.py` - Update assertions
- [ ] All other test files - Use `get_default_models("testing")`

#### Frontend
- [ ] `frontend/src/components/InputForm.tsx`
  ```typescript
  // Fetch available models from backend API endpoint
  // Or maintain a synced list
  const AVAILABLE_MODELS = [
    { id: 'gemini-2.5-flash-lite', name: '2.5 Flash Lite', class: 'fast' },
    { id: 'gemini-2.5-flash', name: '2.5 Flash', class: 'balanced' },
    { id: 'gemini-2.5-pro', name: '2.5 Pro', class: 'premium' },
  ];
  ```

- [ ] `frontend/src/hooks/useAgentState.ts` - Use default from config

#### Notebooks
- [ ] `notebooks/01_Agent_Deep_Research.ipynb` - Use registry
- [ ] `notebooks/02_MCP_Tools_Integration.ipynb` - Use registry
- [ ] `notebooks/03_Benchmarking_Pipeline.ipynb` - Use registry
- [ ] `notebooks/04_SOTA_Comparison.ipynb` - Use registry
- [ ] `notebooks/agent_architecture_demo.ipynb` - Use registry
- [ ] `notebooks/deep_research_demo.ipynb` - Use registry
- [ ] `notebooks/colab_setup.ipynb` - Use registry

#### Scripts
- [ ] `update_models.py` - Use registry for migrations

---

## Phase 4: Add Backend API Endpoint

**File**: `backend/src/api/models.py`

```python
from fastapi import APIRouter
from models.registry import ModelRegistry, ModelClass

router = APIRouter()

@router.get("/api/models")
async def get_available_models():
    """Get list of available models"""
    return {
        "fast": [
            {"id": m.id, "description": m.description, "token_limit": m.token_limit}
            for m in ModelRegistry.get_models_by_class(ModelClass.FAST)
        ],
        "balanced": [
            {"id": m.id, "description": m.description, "token_limit": m.token_limit}
            for m in ModelRegistry.get_models_by_class(ModelClass.BALANCED)
        ],
        "premium": [
            {"id": m.id, "description": m.description, "token_limit": m.token_limit}
            for m in ModelRegistry.get_models_by_class(ModelClass.PREMIUM)
        ],
    }

@router.get("/api/models/defaults")
async def get_default_models_endpoint():
    """Get default models for current environment"""
    from models.registry import get_default_models
    return get_default_models()
```

---

## Phase 5: Documentation

- [ ] Update `README.md` with model configuration section
- [ ] Document environment variables (`APP_ENV=testing` for Gemma)
- [ ] Add migration guide for users with custom configs
- [ ] Update API documentation

---

## Testing Strategy

1. **Unit Tests**
   - Test ModelRegistry methods
   - Test get_default_models() for each environment
   - Verify token limits match

2. **Integration Tests**
   - Ensure config loads correctly with registry
   - Test environment switching (prod/test/dev)
   - Verify frontend can fetch models from API

3. **Regression Tests**
   - Run full test suite with Gemma models
   - Verify no hardcoded model strings remain
   - Check all notebooks run with new config

---

## Rollout Plan

### Step 1: Create Registry (Week 1)
- Create `backend/src/models/registry.py`
- Add all current models
- Write unit tests

### Step 2: Update Backend (Week 1-2)
- Update configuration.py
- Update research_tools.py
- Update all source files
- Update all test files

### Step 3: Update Frontend (Week 2)
- Add API endpoint
- Update frontend to fetch from API
- Update model selector component

### Step 4: Update Notebooks (Week 2)
- Update all notebooks
- Add environment switching examples

### Step 5: Cleanup (Week 2-3)
- Remove old hardcoded references
- Run full regression suite
- Update documentation
- Code review

---

## Success Criteria

- ✅ Zero hardcoded model strings in source code (except registry)
- ✅ All tests pass with Gemma models  
- ✅ All notebooks run with registry-based config
- ✅ Frontend dynamically loads models from backend
- ✅ Environment variable switches between prod/test/dev models
- ✅ Documentation complete and clear

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing configs | High | Add backward compatibility layer |
| Frontend/backend sync issues | Medium | Use API endpoint, not hardcoded lists |
| Notebook compatibility | Low | Update all notebooks in same PR |
| Test failures with Gemma | Medium | Verify Gemma capabilities first |

---

## Follow-up Tasks

After centralization is complete:

1. **Add cost tracking** - Log model usage and compute costs
2. **Add model auto-selection** - Choose model based on query complexity
3. **Add provider fallbacks** - Switch providers if one is down
4. **Performance monitoring** - Track latency by model

---

## References

- PR #19 Analysis: `PR19_ANALYSIS.md`
- Conflict Resolution: `PR19_CONFLICT_RESOLUTION.md`
- Current model usage: grep for "gemini-" and "gemma-" in codebase

---

**Estimated Effort**: 2-3 weeks (40-60 hours)  
**Assigned To**: TBD  
**Priority**: Complete before next major feature release
