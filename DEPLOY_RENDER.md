# Deploying Gemini Agent to Render (Free Tier Compatible)

This guide walks you through deploying the Gemini Fullstack Agent to [Render.com](https://render.com) using their **Free Tier**.

We have optimized the setup to use **Gemma via the Gemini API** (Google GenAI) instead of heavy local models, making it compatible with the limited resources of the free tier.

## Prerequisites

1.  **Render Account**: [Sign up for free](https://dashboard.render.com/register).
2.  **Google Gemini API Key**: [Get it here](https://aistudio.google.com/app/apikey).
3.  **Tavily API Key**: [Get it here](https://tavily.com/).

## One-Click Deployment (Blueprints)

The easiest way to deploy is using the `render.yaml` Blueprint included in this repository.

1.  Go to your [Render Dashboard](https://dashboard.render.com/).
2.  Click **New +** and select **Blueprint**.
3.  Connect your GitHub repository containing this code.
4.  Give the blueprint a name (e.g., `gemini-agent`).
5.  **Environment Variables**: Render will ask you to fill in the following keys:
    *   `GEMINI_API_KEY`: Paste your key from Google AI Studio.
    *   `TAVILY_API_KEY`: Paste your key from Tavily.
6.  Click **Apply**.

Render will now:
*   Build the frontend (React/Vite).
*   Install Python dependencies.
*   Start the backend server (FastAPI + LangGraph).

## Manual Deployment Settings (If not using Blueprint)

If you prefer to configure the service manually:

*   **Service Type**: Web Service
*   **Runtime**: Python 3
*   **Build Command**: `./setup_env.sh`
*   **Start Command**: `cd backend && export PYTHONPATH=$PYTHONPATH:$(pwd)/src && python -m uvicorn agent.app:app --host 0.0.0.0 --port $PORT`
*   **Environment Variables**:
    *   `PYTHON_VERSION`: `3.12.0`
    *   `NODE_VERSION`: `20.11.0`
    *   `RENDER`: `true`
    *   `GEMMA_PROVIDER`: `google_genai`
    *   `GEMMA_MODEL_NAME`: `gemma-2-27b-it` (or `gemini-2.5-flash` for speed)
    *   `GEMINI_API_KEY`: (Your Key)
    *   `TAVILY_API_KEY`: (Your Key)

## How It Works (Free Tier Optimization)

To make this work on the Free Tier (512MB RAM, 0.1 CPU):

1.  **Gemma via API**: Instead of running Gemma locally (which requires >16GB RAM), we use the `google_genai` provider to call Gemma models hosted by Google. This uses your `GEMINI_API_KEY`.
2.  **Skip Heavy Installs**: The `setup_env.sh` script detects the `RENDER=true` environment variable and skips installing Playwright browsers (Chromium/Firefox), saving build time and disk space.
3.  **Lightweight Frontend**: The React frontend is built as a static asset bundle served directly by FastAPI, eliminating the need for a separate Node.js server.

## Troubleshooting

*   **Build Failures**: Check the logs. If you see memory errors during `uv sync`, ensure `RENDER=true` is set.
*   **502 Bad Gateway**: The server might be taking too long to start. The Free Tier spins down after inactivity. Give it a minute to wake up.
*   **"Model not found"**: Ensure your `GEMINI_API_KEY` has access to the requested model.
