# Gemma 3 & 27B Configuration

User research has confirmed that `gemma-3-27b-it` (Gemma 3 27B Instruction Tuned) and its predecessor `gemma-2-27b-it` offer significantly higher daily API limits compared to standard Gemini models. These models are available via the Google AI SDK and can be used as the primary engine for high-volume research tasks.

## Key Specifications

- **Model ID**: `gemma-3-27b-it` (and `gemma-2-27b-it`)
- **Context Window**: ~8,192 tokens.
- **Use Case**: High-volume query generation, reasoning, and summarization where extreme context length is not required.
- **Availability**: Confirmed via Google GenAI SDK.

## Default Configuration

The project is now configured to use `gemma-3-27b-it` by default for:
- Query Generation
- Reflection
- Scoping
- Validation
- Final Answer Synthesis

## How to Override

If you need the 1M+ context window of Gemini 2.5 for a specific task, you can override the defaults:

### 1. In `configuration.py` or `.env`
Set the model overrides:

```env
MODEL_QUERY_GENERATOR=gemini-2.5-flash
MODEL_ANSWER=gemini-2.5-pro
```

### 2. In CLI
```bash
python examples/cli_research.py "My query" --reasoning-model gemini-2.5-pro
```

### 3. Programmatic Usage
```python
from agent.models import GEMINI_PRO
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(model=GEMINI_PRO)
```

## Considerations

- **Context Window**: Unlike Gemini's 1M/2M window, Gemma is limited to ~8k. The agent automatically handles summarization, but for extremely large documents, Gemini Flash may be preferred.
- **Reasoning**: Gemma 3 27B is highly capable and optimized for instruction following.
