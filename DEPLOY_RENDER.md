# Deploying to Render (Free Tier)

This guide covers how to deploy the Gemini Fullstack Agent to Render using the **Free Tier** (512MB RAM, 0.1 CPU).

Due to the limited resources of the Free Tier, we use a "Lite Mode" configuration that disables heavy local computations (like local RAG embeddings or Ollama inference) and relies entirely on cloud APIs (Google Gemini).

## Prerequisites

1. A [Render.com](https://render.com) account.
2. A Google Gemini API Key.
3. Your code pushed to a GitHub or GitLab repository connected to Render.

## Why Manual Web Service Deployment?

Render occasionally attempts to charge or block deployments initialized via `render.yaml` (Blueprints) if they detect you are trying to bypass plan restrictions or simply because Blueprints are sometimes considered a paid feature depending on your account state.

**Creating a manual Web Service** bypasses this completely and guarantees you can use your Free Tier allowance.

---

## Deployment Steps

### 1. Create a New Web Service
1. Log in to your Render dashboard.
2. Click **New +** and select **Web Service**.
3. Choose **Build and deploy from a Git repository**.
4. Connect your GitHub/GitLab repository and select it.

### 2. Configure the Service

Fill out the form with the following details exactly:

*   **Name:** `gemini-fullstack-agent` (or your preferred name)
*   **Region:** (Select the one closest to you)
*   **Branch:** `main` (or the branch you want to deploy)
*   **Root Directory:** *(Leave blank! Do not put `backend` or `frontend` here)*
*   **Runtime:** `Python 3`
*   **Build Command:**
    ```bash
    ./setup_env.sh
    ```
*   **Start Command:**
    ```bash
    cd backend && export PYTHONPATH=$PYTHONPATH:$(pwd)/src && python -m uvicorn agent.app:app --host 0.0.0.0 --port $PORT
    ```
*   **Instance Type:** `Free` (512 MB RAM • 0.1 CPU)

### 3. Configure Environment Variables

Scroll down to the **Environment Variables** section and click **Add Environment Variable**. You must add all of the following:

| Key | Value | Purpose |
| :--- | :--- | :--- |
| `RENDER` | `true` | Tells `setup_env.sh` to skip downloading heavy Playwright browsers. |
| `PYTHON_VERSION` | `3.12.0` | Forces Render to use Python 3.12 (required by `uv` and langgraph). |
| `NODE_VERSION` | `20.11.0` | Informs the build script which node version to use. |
| `GEMINI_API_KEY` | `your-gemini-api-key` | Your Google API Key for LLM reasoning. |
| `GEMMA_PROVIDER` | `google_genai` | Uses the API for Gemma tasks instead of local Ollama. |
| `RAG_ENABLED` | `false` | (Recommended) Disables local vector embeddings to save RAM. If you need RAG, set to `true` and set `RAG_EMBEDDING_PROVIDER=google_genai`. |
| `TRUST_PROXY_HEADERS` | `true` | Ensures rate-limiting works correctly behind Render's load balancer. |

### 4. Deploy

Click **Create Web Service**.

Render will now run the `./setup_env.sh` script. This script is smart enough to detect the Render environment:
1. It will download a standalone version of Node.js (since Render's Python runtime doesn't have it).
2. It will install `uv` and sync the Python dependencies.
3. It will install `pnpm` and build the React frontend for production.
4. It will start the FastAPI backend using `uvicorn`, serving the built frontend on the `/app` route and the API on `/`.

### 5. Access the App

Once the deployment is marked as **Live**, click the URL provided by Render (e.g., `https://gemini-fullstack-agent-abc1.onrender.com`).

Because it's a single-service architecture, navigating to the root URL will automatically redirect you to `/app`, where the frontend interface lives.

## Troubleshooting

*   **Memory Limit Exceeded (OOM):** If the build or runtime fails due to memory limits, ensure `RAG_ENABLED=false` is set. The Free tier (512MB) struggles to load sentence-transformers or FAISS indexes.
*   **Node.js Not Found Error:** If the build fails saying `node` or `pnpm` is not found, ensure you are using the exact `./setup_env.sh` as the build command, as it installs Node on the fly for the Python environment.
*   **Rate Limiting Issues:** If you get "Too Many Requests" errors instantly, ensure `TRUST_PROXY_HEADERS=true` is set so the backend sees real client IPs, not just Render's internal proxy IP.
