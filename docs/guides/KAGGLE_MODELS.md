# Kaggle Models Integration Guide

This guide explains how to integrate arbitrary models hosted on [Kaggle Models](https://www.kaggle.com/models) into the Research Agent. This allows leveraging a vast library of open-weights models (Gemma, Llama, Mistral, etc.) running locally or on custom infrastructure.

## 1. Prerequisites

Since Kaggle models are typically downloaded as raw weights, you need a runtime environment to execute them.

**Dependencies:**
Add the following to your environment (e.g., `backend/requirements.txt` or install manually):

```bash
pip install kagglehub transformers torch accelerate
```

*   `kagglehub`: Official library to download models from Kaggle.
*   `transformers`: Hugging Face library to load and run models.
*   `torch`: PyTorch backend.
*   `accelerate`: For efficient model loading (e.g., `device_map="auto"`).

**Hardware:**
Local inference requires significant RAM and/or VRAM.
*   **Gemma 2B:** ~2-4GB VRAM (runs on most modern laptops/Colab free tier).
*   **Gemma 7B / Llama 3 8B:** ~16GB+ VRAM (requires decent GPU).

## 2. Usage Strategy

Most open models on Kaggle are "Text Generation" models. They do not natively support "Function Calling" (Tool Use) APIs like OpenAI or Gemini.

To solve this, we use a **ReAct (Reasoning + Acting)** wrapper:
1.  **Prompt Engineering:** We inject a system prompt telling the model *how* to use tools (formatting).
2.  **Parsing:** We parse the model's text output to find "Action:" and "Action Input:".
3.  **Execution:** We run the tool Python code.
4.  **Loop:** We feed the tool output back to the model as an "Observation".

## 3. Implementation Steps

We have provided scaffolding code in `backend/examples/kaggle_integration.py`.

### Step A: Download a Model

Find a model handle on Kaggle (e.g., `google/gemma/pyTorch/2b`).

```python
from examples.kaggle_integration import KaggleModelLoader

# Downloads to local cache (e.g., ~/.cache/kagglehub)
path = KaggleModelLoader.download("google/gemma/pyTorch/2b")
```

### Step B: Initialize the Client

Wrap the downloaded path in our adapter.

```python
from examples.kaggle_integration import KaggleHuggingFaceClient

# 'device="auto"' automatically puts layers on GPU if available
client = KaggleHuggingFaceClient(path, device="auto")
```

### Step C: Create a Tool-Enabled Agent

Wrap the client with the ReAct logic and your tools.

```python
from examples.kaggle_integration import SimpleReActAgent
from agent.tools_and_schemas import get_tools_from_mcp

# Assuming you have tools loaded
tools = [...]

agent = SimpleReActAgent(client, tools)
response = agent.run("What is the stock price of AAPL?")
```

## 4. Integration into Main Agent

To make this a permanent part of the `Research Agent`:

1.  **Modify `backend/src/agent/llm_client.py`:**
    *   Add a new provider type (e.g., `KAGGLE_LOCAL`).
    *   Lazy import `transformers` and `kagglehub` inside the client to avoid bloat for users not using this feature.
2.  **Configuration:**
    *   Add `KAGGLE_MODEL_HANDLE` to `backend/src/config/app_config.py`.

## 5. Troubleshooting

*   **Out of Memory (OOM):** Try smaller models (2B parameters) or use quantization (requires `bitsandbytes` library).
*   **Slow Inference:** Ensure `torch.cuda.is_available()` is True. If running on CPU, it will be slow.
*   **Login Issues:** `kagglehub` might require authentication. Run `kagglehub.login()` or ensure `~/.kaggle/kaggle.json` exists.
