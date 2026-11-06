# Render Free Tier Deployment Guide (Lite Mode)

This repository includes a specialized "Lite" configuration optimized for Render.com's Free Tier limits (512MB RAM, 0.1 CPU).

By leveraging the `google-genai` package and external APIs (like Gemini) instead of running heavy, local embedding and LLM models (e.g., `sentence-transformers`, `ollama`), the application footprint remains minimal.

---

## Deployment Instructions: Manual Web Service

> **Note:** We recommend deploying via a **Manual Web Service** to bypass Blueprint payment requirements and maintain Free Tier usage.

### 1. Create a New Web Service
1. Go to your Render Dashboard -> **New +** -> **Web Service**.
2. Connect your Git repository.
3. Choose a name (e.g., `gemini-fullstack-agent`).

### 2. Configure Settings
Set the following properties:
*   **Environment:** `Python 3`
*   **Region:** Select your preferred region
*   **Branch:** `main` (or your deployment branch)
*   **Build Command:** `./setup_env.sh`
*   **Start Command:**
    ```bash
    cd backend && export PYTHONPATH=$PYTHONPATH:$(pwd)/src && python -m uvicorn agent.app:app --host 0.0.0.0 --port $PORT
    ```
*   **Instance Type:** `Free` (0.1 CPU, 512MB RAM)

### 3. Environment Variables
Add the following Environment Variables in the Render dashboard:

| Key | Value | Notes |
| :--- | :--- | :--- |
| `RENDER` | `true` | Instructs the build script to skip heavy dev dependencies (e.g., Playwright). |
| `PYTHON_VERSION` | `3.12.0` | Ensures native Python compatibility. |
| `NODE_VERSION` | `20.11.0` | Required for building the frontend. |
| `RAG_EMBEDDING_PROVIDER` | `google_genai` | **Critical for Lite Mode.** Skips local `sentence-transformers` models in favor of Google API. |
| `GEMMA_PROVIDER` | `google_genai` | **Critical for Lite Mode.** Skips local Ollama inference in favor of Google API. |
| `GEMINI_API_KEY` | `<YOUR_API_KEY>` | Required for RAG Embeddings and LLM inference. Get it from Google AI Studio. |

*Optional Variables for external APIs:*
*   `TAVILY_API_KEY` or `SERPER_API_KEY` if using those search providers.

### 4. Deploy
Click **Create Web Service**.
* The build step will download Node, build the frontend, and install production Python packages.
* Wait a few minutes. Once successful, Render will provide a public URL for your agent!

### Optional Configuration
If you wish to customize models further for Lite mode, you can override the defaults:
*   `GEMMA_MODEL_NAME`: Default is `gemini-1.5-flash` (when `GEMMA_PROVIDER` is `google_genai`).
*   `RAG_EMBEDDING_PROVIDER`: The model used for generating embeddings. Default is `text-embedding-004`.
