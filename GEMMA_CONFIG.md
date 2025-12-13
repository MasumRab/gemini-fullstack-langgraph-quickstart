# Gemma 27B Configuration

User research indicates that `gemma-2-27b-it` (Gemma 2 27B Instruction Tuned) offers higher daily API limits compared to standard Gemini models on the current API tier. This model is available via the Google AI SDK and can be used as a robust fallback or primary model for specific high-volume tasks.

## Key Specifications

- **Model ID**: `gemma-2-27b-it`
- **Context Window**: ~8,192 tokens (Safe limit)
- **Use Case**: High-volume query generation, reasoning, and summarization where 1M context is not required.
- **Availability**: Confirmed via Google GenAI SDK.

## How to Use

To switch specific agents to use Gemma 27B:

### 1. In `configuration.py` or `.env`
Set the model overrides:

```env
MODEL_QUERY_GENERATOR=gemma-2-27b-it
MODEL_REFLECTION=gemma-2-27b-it
MODEL_VALIDATION=gemma-2-27b-it
```

### 2. In CLI
```bash
python examples/cli_research.py "My query" --reasoning-model gemma-2-27b-it
```

### 3. Programmatic Usage
```python
from agent.models import GEMMA_2_27B_IT
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(model=GEMMA_2_27B_IT)
```

## Considerations

- **Context Window**: Unlike Gemini's 1M/2M window, Gemma is limited to ~8k. Avoid using it for large-scale summarization of multiple long documents in a single pass.
- **Reasoning**: Gemma 2 27B is highly capable (comparable to Llama 3 70B in some benchmarks) but may differ slightly in instruction following compared to Gemini 1.5 Pro.
