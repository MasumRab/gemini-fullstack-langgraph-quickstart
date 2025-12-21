# Gemini 2.5 Model Configuration Guide

**Updated:** 2025-12-12 15:40 AEDT
**Status:** ✅ Production Ready

## ⚠️ Important: Model Availability Update

**As of December 2024:**
- ❌ **Gemini 1.5 models** (1.5-flash, 1.5-flash-8b, 1.5-pro): **NOT accessible via API**
- ❌ **Gemini 2.0 models** (2.0-flash, 2.0-flash-exp, 2.0-flash-lite): **Deprecated**
- ✅ **Gemini 2.5 models** (2.5-flash, 2.5-flash-lite, 2.5-pro): **Currently accessible**

## Available Gemini 2.5 Models

### Gemini 2.5 Flash (`gemini-2.5-flash`) - **Recommended**

**Best for:** Price-performance balance, general-purpose use

**Capabilities:**
- 22% more computationally efficient than 1.5 Flash
- Optimized for low-latency, high-volume tasks
- Excellent for agentic use cases
- Thinking and reasoning capabilities

**Specifications:**
- **Token Limit:** 1,048,576 tokens (input + output)
- **Temperature Range:** 0.0 - 2.0
- **Max Output Tokens:** 8,192
- **Supported Features:** Text, images, video, audio, code execution

**Rate Limits (Free Tier):**
- **RPM** (Requests Per Minute): 15
- **TPM** (Tokens Per Minute): 1,000,000
- **RPD** (Requests Per Day): 1,500

**Use Cases:**
- Query generation
- Web research and summarization
- Reflection and gap analysis
- General agent operations

---

### Gemini 2.5 Flash-Lite (`gemini-2.5-flash-lite`) - **Fastest**

**Best for:** High-throughput, cost-efficiency, simple tasks

**Capabilities:**
- Fastest Gemini model
- Optimized for massive scale
- Ultra-efficient for simple tasks
- Lowest cost option

**Specifications:**
- **Token Limit:** 1,048,576 tokens
- **Temperature Range:** 0.0 - 2.0
- **Max Output Tokens:** 8,192
- **Supported Features:** Text, images

**Rate Limits (Free Tier):**
- **RPM**: 15
- **TPM**: 1,000,000
- **RPD**: 1,500

**Use Cases:**
- High-volume query generation
- Simple text transformations
- Cost-sensitive applications
- Development and testing

---

### Gemini 2.5 Pro (`gemini-2.5-pro`) - **Best Quality**

**Best for:** Complex reasoning, highest quality outputs

**Capabilities:**
- State-of-the-art thinking model
- Advanced reasoning over complex problems
- Excellent for code, math, and STEM
- Large dataset and codebase analysis
- Long context understanding

**Specifications:**
- **Token Limit:** 2,097,152 tokens (2M tokens!)
- **Temperature Range:** 0.0 - 2.0
- **Max Output Tokens:** 8,192
- **Supported Features:** Text, images, video, audio, code execution, thinking mode

**Rate Limits (Free Tier):**
- **RPM**: 10 (lower than Flash)
- **TPM**: 1,000,000
- **RPD**: 1,000

**Use Cases:**
- Final answer synthesis
- Complex research reports
- Deep analysis and reasoning
- Quality-critical outputs

---

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
        default="gemini-2.5-flash",  # ← Updated from gemini-1.5-pro
    )
```

### Research Tools (`backend/src/agent/research_tools.py`)

✅ **Updated hardcoded model:**

```python
writer_model = init_chat_model(model="gemini-2.5-flash", max_tokens=16000)
```

✅ **Updated token limits:**

```python
MODEL_TOKEN_LIMITS = {
    # Gemini 2.5 series (current, accessible)
    "google:gemini-2.5-pro": 2097152,
    "google:gemini-2.5-flash": 1048576,
    "google:gemini-2.5-flash-lite": 1048576,
    "gemini-2.5-pro": 2097152,
    "gemini-2.5-flash": 1048576,
    "gemini-2.5-flash-lite": 1048576,
    # Legacy models (deprecated, kept for reference)
    "gemini-1.5-pro": 2097152,
    "gemini-1.5-flash": 1048576,
    # ...
}
```

---

## Rate Limiting Strategy

### Understanding Rate Limits

Rate limits are measured across three dimensions:
1. **RPM** (Requests Per Minute)
2. **TPM** (Tokens Per Minute)
3. **RPD** (Requests Per Day)

**Important:** Exceeding ANY limit triggers a 429 error. Quotas reset at midnight Pacific time.

### Free Tier Limits Summary

| Model | RPM | TPM | RPD |
|-------|-----|-----|-----|
| gemini-2.5-flash | 15 | 1M | 1,500 |
| gemini-2.5-flash-lite | 15 | 1M | 1,500 |
| gemini-2.5-pro | 10 | 1M | 1,000 |

### Rate Limit Best Practices

1. **Use Flash-Lite for high-volume operations**
   - Maximizes throughput within RPM limits
   - Lowest cost per request

2. **Implement exponential backoff**
   ```python
   from tenacity import retry, stop_after_attempt, wait_exponential

   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=4, max=10)
   )
   def call_gemini_api():
       # Your API call here
       pass
   ```

3. **Monitor daily quotas**
   - Track RPD usage
   - Implement daily quota warnings
   - Reset counters at midnight PT

4. **Batch requests when possible**
   - Group similar operations
   - Use async/parallel processing within limits

---

## Model Usage Strategy

### Strategy 1: Balanced (Default - Recommended)

```python
query_generator_model = "gemini-2.5-flash"
reflection_model = "gemini-2.5-flash"
answer_model = "gemini-2.5-flash"
```

**Benefits:**
- Consistent performance across all operations
- Simple configuration
- Good quality-to-cost ratio

**Use Case:** General production applications

---

### Strategy 2: Cost-Optimized

```python
query_generator_model = "gemini-2.5-flash-lite"
reflection_model = "gemini-2.5-flash-lite"
answer_model = "gemini-2.5-flash"
```

**Benefits:**
- Maximum cost savings
- Highest throughput
- Still good quality

**Use Case:** High-volume, cost-sensitive applications

---

### Strategy 3: Quality-Optimized

```python
query_generator_model = "gemini-2.5-flash"
reflection_model = "gemini-2.5-flash"
answer_model = "gemini-2.5-pro"
```

**Benefits:**
- Best quality final outputs
- Pro model's advanced reasoning
- 2M token context for answers

**Use Case:** Research, analysis, premium applications

**⚠️ Note:** Pro model has lower RPM (10 vs 15)

---

### Strategy 4: Maximum Quality

```python
query_generator_model = "gemini-2.5-flash"
reflection_model = "gemini-2.5-pro"
answer_model = "gemini-2.5-pro"
```

**Benefits:**
- Highest quality across all operations
- Best reasoning capabilities
- Premium outputs

**Use Case:** Critical research, complex analysis

**⚠️ Caution:** Higher cost, lower throughput (10 RPM)

---

## Environment Variable Configuration

### Required

```bash
GEMINI_API_KEY=your_api_key_here
```

### Optional Model Overrides

```bash
# Default strategy (balanced)
QUERY_GENERATOR_MODEL=gemini-2.5-flash
REFLECTION_MODEL=gemini-2.5-flash
ANSWER_MODEL=gemini-2.5-flash

# Or cost-optimized
QUERY_GENERATOR_MODEL=gemini-2.5-flash-lite
REFLECTION_MODEL=gemini-2.5-flash-lite
ANSWER_MODEL=gemini-2.5-flash

# Or quality-optimized
QUERY_GENERATOR_MODEL=gemini-2.5-flash
REFLECTION_MODEL=gemini-2.5-flash
ANSWER_MODEL=gemini-2.5-pro
```

---

## Testing & Verification

### Test Model Availability

```bash
python test_available_models.py
```

This script will:
- Load API key from `.env`
- Test all Gemini models
- Report which models are accessible
- Provide recommendations

### Verify Backend Configuration

```bash
cd backend
python -c "from agent.configuration import Configuration; c = Configuration(); print(f'Query: {c.query_generator_model}\\nReflection: {c.reflection_model}\\nAnswer: {c.answer_model}')"
```

Expected output:
```
Query: gemini-2.5-flash
Reflection: gemini-2.5-flash
Answer: gemini-2.5-flash
```

### Test API Connection

```python
from google import genai
import os

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Hello, test message"
)
print(f"Success! Response: {response.text}")
```

---

## Upgrading to Higher Tiers

### Usage Tiers

**Tier 1 (Free):**
- No billing required
- 15 RPM for Flash models
- 1,500 RPD
- Suitable for development and testing

**Tier 2:**
- Requires Google Cloud billing
- Qualification: $5+ cumulative spend
- Increased rate limits
- Production-ready

**Tier 3:**
- Qualification: $50+ cumulative spend
- Highest rate limits
- Enterprise-scale

### How to Upgrade

1. Navigate to [AI Studio API Keys](https://aistudio.google.com/app/apikey)
2. Locate your project
3. Click "Upgrade" (appears when eligible)
4. Enable Cloud Billing if needed

---

## Troubleshooting

### Issue: 404 Model Not Found

**Error:** `Model 'gemini-2.5-flash' not found`

**Solutions:**
1. Verify API key is valid and active
2. Check model is available in your region
3. Ensure you're using correct model name (no typos)
4. Test with `test_available_models.py`

### Issue: 429 Quota Exceeded

**Error:** `RESOURCE_EXHAUSTED` or `You exceeded your current quota`

**Solutions:**
1. **Check which limit:** RPM, TPM, or RPD
2. **Implement retry logic** with exponential backoff
3. **Switch to Flash-Lite** for higher throughput
4. **Reduce request frequency** or batch operations
5. **Upgrade tier** if consistently hitting limits

### Issue: Slow Response Times

**Solutions:**
1. Use `gemini-2.5-flash-lite` for simple tasks
2. Reduce `max_research_loops` configuration
3. Optimize prompts to be more concise
4. Use async/parallel processing

---

## Migration from 1.5/2.0 Models

### Automatic Migration

Run the update script:
```bash
python update_models.py flash
```

This will update:
- Backend configuration
- Research tools
- Environment files
- All notebooks

### Manual Migration

If you have custom code:

**Replace:**
- `gemini-1.5-flash` → `gemini-2.5-flash`
- `gemini-1.5-flash-8b` → `gemini-2.5-flash-lite`
- `gemini-1.5-pro` → `gemini-2.5-pro` or `gemini-2.5-flash`
- `gemini-2.0-flash` → `gemini-2.5-flash`
- `gemini-2.0-flash-exp` → `gemini-2.5-flash`

---

## References

- [Gemini Models Documentation](https://ai.google.dev/gemini-api/docs/models)
- [Rate Limits Guide](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Deprecations Schedule](https://ai.google.dev/gemini-api/docs/deprecations)
- [API Key Setup](https://ai.google.dev/gemini-api/docs/api-key)
- [Migration Guide](./docs/GEMINI_2_5_MIGRATION.md)

---

## Related Documentation

- [GEMINI_2_5_MIGRATION.md](./docs/GEMINI_2_5_MIGRATION.md) - Detailed migration guide
- [MODEL_USAGE_ANALYSIS.md](./MODEL_USAGE_ANALYSIS.md) - Model usage patterns
- [OPTIMIZED_MODEL_CONFIG.md](./OPTIMIZED_MODEL_CONFIG.md) - Cost optimization strategies
