# Gemini 2.5 Model Configuration Guide

**Updated:** 2025-12-11 15:05 AEDT

## Configuration Changes Applied

### Backend Configuration (`backend/src/agent/configuration.py`)

✅ **Updated to Gemini 2.5 series:**

```python
class Configuration(BaseModel):
    query_generator_model: str = Field(
        default="gemini-2.5-flash",  # ← Updated from gemini-1.5-flash
    )

    reflection_model: str = Field(
        default="gemini-2.5-flash",  # ← Updated from gemini-1.5-flash
    )

    answer_model: str = Field(
        default="gemini-2.5-pro",  # ← Updated from gemini-1.5-pro
    )
```

### Frontend Configuration (`frontend/src/hooks/useAgentState.ts`)

✅ **Updated to match backend:**

```typescript
const lastConfigRef = useRef({
  initial_search_query_count: 1,
  max_research_loops: 1,
  reasoning_model: "gemini-2.5-flash",  // ← Updated from preview version
});
```

### Research Tools (`backend/src/agent/research_tools.py`)

✅ **Updated hardcoded model:**

```python
writer_model = init_chat_model(model="gemini-2.5-pro", max_tokens=16000)
```

✅ **Added token limits for Gemini 2.5 series:**

```python
MODEL_TOKEN_LIMITS = {
    # Gemini 2.5 series (current stable)
    "google:gemini-2.5-flash": 1048576,
    "gemini-2.5-flash": 1048576,
    "gemini-2.5-flash-lite": 1048576,
    "google:gemini-2.5-pro": 2097152,
    "gemini-2.5-pro": 2097152,
    # ... other models
}
```

---

## Model Usage Strategy

### Gemini 2.5 Flash (`gemini-2.5-flash`)

**Used For:**
- Query generation (creative search queries)
- Reflection (reasoning and gap analysis)
- Web research (factual retrieval)

**Benefits:**
- 22% more computationally efficient than 1.5 Flash
- Faster response times
- Optimized for low-latency interactions
- Cost-effective for high-volume tasks

**Token Limit:** 1,048,576 tokens

---

### Gemini 2.5 Pro (`gemini-2.5-pro`)

**Used For:**
- Final answer synthesis
- Complex reasoning tasks
- Research report refinement

**Benefits:**
- Most powerful Gemini model
- Advanced reasoning capabilities
- 1 million token context window
- Deep Think mode for complex problems
- Best for quality-critical outputs

**Token Limit:** 2,097,152 tokens

---

### Gemini 2.5 Flash-Lite (`gemini-2.5-flash-lite`)

**Available For:**
- High-volume, simple tasks
- Cost optimization scenarios
- Testing and development

**Benefits:**
- Ultra-efficient for simple tasks
- Lowest cost option
- Optimized for massive scale

**Token Limit:** 1,048,576 tokens

**How to Use:**
```python
# Override via environment variable
export QUERY_GENERATOR_MODEL=gemini-2.5-flash-lite

# Or via RunnableConfig
config = {
    "configurable": {
        "query_generator_model": "gemini-2.5-flash-lite"
    }
}
```

---

## Environment Variable Configuration

### Override Defaults

You can override any model via environment variables:

```bash
# Backend .env file
QUERY_GENERATOR_MODEL=gemini-2.5-flash
REFLECTION_MODEL=gemini-2.5-flash
ANSWER_MODEL=gemini-2.5-pro

# Or for cost optimization
QUERY_GENERATOR_MODEL=gemini-2.5-flash-lite
REFLECTION_MODEL=gemini-2.5-flash-lite
ANSWER_MODEL=gemini-2.5-flash
```

### API Key

Ensure your Gemini API key is set:

```bash
GEMINI_API_KEY=your_api_key_here
```

---

## Runtime Configuration

### Frontend Model Selection

Users can select models via the frontend UI (if implemented):

```typescript
// In handleSubmit
const config = {
  initial_search_query_count,
  max_research_loops,
  reasoning_model: model,  // User-selected model
};

thread.submit({
  messages: newMessages,
  ...config,
});
```

### Backend State Override

Models can be overridden per-execution via state:

```python
# In nodes.py - reflection and finalize_answer
reasoning_model = state.get("reasoning_model", configurable.reflection_model)
```

---

## Migration Notes

### From Gemini 1.5 to 2.5

**Breaking Changes:** None - API compatible

**Performance Improvements:**
- 22% better efficiency (Flash)
- Faster response times
- Better reasoning capabilities (Pro)

**Deprecation Timeline:**
- Gemini 1.5 series: Retiring April 29, 2025 for new projects
- Existing projects: May retain access for legacy integrations

### From Preview to Stable

**Previous:** `gemini-2.5-flash-preview-04-17`
**Current:** `gemini-2.5-flash` (stable)

**Benefits:**
- Production-ready stability
- No scheduled deprecation
- Official support and SLAs

---

## Testing Configuration

### Verify Model Availability

```bash
# Test backend configuration
cd backend
python -c "from agent.configuration import Configuration; c = Configuration(); print(f'Query: {c.query_generator_model}, Reflection: {c.reflection_model}, Answer: {c.answer_model}')"
```

Expected output:
```
Query: gemini-2.5-flash, Reflection: gemini-2.5-flash, Answer: gemini-2.5-pro
```

### Test API Connection

```python
# test_gemini_connection.py
import os
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
)

response = llm.invoke("Hello, test message")
print(f"Success! Response: {response.content[:100]}...")
```

---

## Cost Optimization Strategies

### Strategy 1: All Flash (Lowest Cost)

```python
query_generator_model = "gemini-2.5-flash-lite"
reflection_model = "gemini-2.5-flash-lite"
answer_model = "gemini-2.5-flash"
```

**Use Case:** High-volume, cost-sensitive applications

---

### Strategy 2: Balanced (Recommended - Current)

```python
query_generator_model = "gemini-2.5-flash"
reflection_model = "gemini-2.5-flash"
answer_model = "gemini-2.5-pro"
```

**Use Case:** Production applications balancing cost and quality

---

### Strategy 3: Maximum Quality

```python
query_generator_model = "gemini-2.5-pro"
reflection_model = "gemini-2.5-pro"
answer_model = "gemini-2.5-pro"
```

**Use Case:** Research, analysis, or quality-critical applications

---

## Monitoring and Observability

### Track Model Usage

Models are logged in the observability spans:

```python
with observe_span("generate_query", config):
    llm = ChatGoogleGenerativeAI(
        model=configurable.query_generator_model,
        # ...
    )
```

### Monitor Token Usage

Token limits are enforced and can be monitored:

```python
from agent.research_tools import get_model_token_limit

limit = get_model_token_limit("gemini-2.5-flash")
print(f"Token limit: {limit}")  # 1048576
```

---

## Troubleshooting

### Issue: Model Not Found

**Error:** `Model 'gemini-2.5-flash' not found`

**Solution:**
1. Verify API key has access to Gemini 2.5 models
2. Check if model is available in your region
3. Fallback to `gemini-2.0-flash-exp` temporarily

### Issue: Token Limit Exceeded

**Error:** `Token limit exceeded`

**Solution:**
1. Check `get_model_token_limit()` for your model
2. Reduce input size or use Pro model (2M tokens)
3. Implement chunking for large inputs

### Issue: Slow Response Times

**Solution:**
1. Use `gemini-2.5-flash-lite` for simple tasks
2. Reduce `max_research_loops` in configuration
3. Optimize prompts to be more concise

---

## Next Steps

### Immediate Actions

- [ ] Test backend with new configuration
- [ ] Test frontend with new configuration
- [ ] Verify API key has access to Gemini 2.5 models
- [ ] Update tests to use new model names
- [ ] Monitor performance and costs

### Future Enhancements

- [ ] Add model selection UI in frontend
- [ ] Implement automatic model fallback
- [ ] Add model performance tracking
- [ ] Create cost estimation dashboard
- [ ] Add model A/B testing capability

---

## Related Files

**Modified:**
- `backend/src/agent/configuration.py` - Default model configuration
- `backend/src/agent/research_tools.py` - Token limits and hardcoded model
- `frontend/src/hooks/useAgentState.ts` - Frontend default model

**Affected:**
- `backend/src/agent/nodes.py` - Uses configuration models
- `backend/tests/test_configuration.py` - May need test updates

---

## References

- [Gemini API Models Documentation](https://ai.google.dev/gemini-api/docs/models)
- [Gemini 2.5 Release Notes](https://developers.googleblog.com/)
- [MODEL_USAGE_ANALYSIS.md](./MODEL_USAGE_ANALYSIS.md) - Detailed usage analysis
