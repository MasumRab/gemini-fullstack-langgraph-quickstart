# TODO: Benmarking & Evaluation Framework

We need to implement a systematic evaluation framework to measure improvements in report quality, relevance, and accuracy.

## 1. Port Evaluators
Create `backend/tests/evaluators.py`. This module will define Pydantic models for structured grading.

### Pseudocode (`backend/tests/evaluators.py`)
```python
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Initialize Judge Model (Configurable)
judge_model = ChatOpenAI(model="gpt-4o") # or Gemini 2.5 Pro

class QualityScore(BaseModel):
    """Score for overall quality."""
    score: int = Field(..., description="1-5 score")
    reasoning: str

def eval_quality(inputs, outputs, reference_outputs=None):
    """Evaluates the quality of the final report."""
    report = outputs.get("final_report", "")
    request = inputs.get("request", "")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert critique. meaningful feedback."),
        ("user", f"Request: {request}\n\nReport: {report}")
    ])
    
    # Use with_structured_output for reliable scoring
    grader = judge_model.with_structured_output(QualityScore)
    result = grader.invoke(prompt.format_messages())
    
    return {
        "key": "quality",
        "score": result.score / 5.0, # Normalize to 0-1
        "comment": result.reasoning
    }

# Implement similar functions for:
# - eval_groundedness (Are claims supported by citations?)
# - eval_coherence (Is the flow logical?)
```

## 2. Create Benchmark Script
Create `backend/scripts/benchmark.py` to run evaluations against a dataset using LangSmith.

### Pseudocode (`backend/scripts/benchmark.py`)
```python
import asyncio
from langsmith import Client
from backend.src.agent.graph import graph # Import your main agent graph
from backend.tests.evaluators import eval_quality, eval_groundedness

client = Client()

# dataset_name = "Golden Research Questions"

async def run_benchmark():
    # 1. Define or Load Dataset
    # examples = client.list_examples(dataset_name=dataset_name)
    
    # 2. Define Target Function (The Agent)
    async def target(inputs):
        # Map dataset inputs to agent inputs
        response = await graph.ainvoke({"messages": [("user", inputs["question"])]})
        # Map agent output to evaluation format
        return {
            "final_report": response["messages"][-1].content,
            "messages": response["messages"]
        }

    # 3. Run Evaluation
    results = await client.aevaluate(
        target,
        data="Golden Research Questions", # Create this dataset in LangSmith UI first
        evaluators=[
            eval_quality, 
            eval_groundedness
        ],
        experiment_prefix="Gemini-2.5-Flash-Update",
        metadata={
            "model": "gemini-2.5-flash",
            "version": "2.0.0"
        }
    )
    
    print(results)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
```

## 3. Search Performance Evaluation
To robustly check search performance, we need to measure **Recall** and **Precision**.

### Metrics to Track
- **Hit Rate @ 3**: Does the correct answer appear in the top 3 results?
- **Purity**: Percentage of results that are non-spam/valid domains.
- **Latency**: Time to first byte for search results.

### Implementation Plan
1. **Create Golden Dataset**: `backend/tests/data/search_golden.json`
   ```json
   [
       {
           "query": "Who is the CEO of Google?",
           "expected_url_substring": "google.com",
           "expected_fact": "Sundar Pichai"
       }
   ]
   ```
2. **Integration Test**:
   Create `test_search_quality.py` (marked `@pytest.mark.external`) that:
   - Runs these queries against the live Tavily/Google adapter.
   - Asserts that at least one result matches `expected_url_substring`.
   - Checks that `content` contains `expected_fact`.

## 4. Observability Integration
Ensure `backend/src/config/app_config.py` loads LangSmith environment variables.
- `LANGCHAIN_TRACING_V2=true`
- `LANGCHAIN_API_KEY=...`
- `LANGCHAIN_PROJECT=...`

This is already handled by the standard LangChain environment setup, so `client = Client()` in the script will automatically connect to your existing project.
