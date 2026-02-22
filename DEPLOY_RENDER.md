# Deploying Gemini Agent to Render (Free Tier Compatible)

This guide provides instructions for deploying the Gemini Fullstack Agent to [Render.com](https://render.com) using their **Free Tier**.

We have optimized the setup to use **Gemma via the Gemini API** (Google GenAI) instead of heavy local models, ensuring compatibility with the 512MB RAM limit.

## Prerequisites

1.  **Render Account**: [Sign up for free](https://dashboard.render.com/register).
2.  **Google Gemini API Key**: [Get it here](https://aistudio.google.com/app/apikey).
3.  **Tavily API Key**: [Get it here](https://tavily.com/).

## Manual Deployment Instructions (Free Tier)

Follow these exact steps to create a free Web Service without needing payment information.

1.  Go to your [Render Dashboard](https://dashboard.render.com/).
2.  Click **New +** and select **Web Service**.
3.  Connect your GitHub repository containing this code.
4.  Configure the following settings:

### Basic Settings

| Setting | Value | Notes |
| :--- | :--- | :--- |
| **Name** | `gemini-agent` (or unique name) | Any unique name for your service. |
| **Region** | `Oregon, US` (or closest) | Choose the region nearest you. |
| **Branch** | `main` | The branch you want to deploy. |
| **Root Directory** | *(Leave Empty)* | Defaults to the repository root. |
| **Runtime** | `Python 3` | |
| **Build Command** | `./setup_env.sh` | Installs Python & Node dependencies. |
| **Start Command** | `cd backend && export PYTHONPATH=$PYTHONPATH:$(pwd)/src && python -m uvicorn agent.app:app --host 0.0.0.0 --port $PORT` | Starts the backend API. |
| **Instance Type** | **Free** | 512 MB RAM, 0.1 CPU. |

### Environment Variables

Scroll down to the **Environment Variables** section and add the following key-value pairs. These are critical for the application to function.

| Key | Value | Purpose |
| :--- | :--- | :--- |
| `PYTHON_VERSION` | `3.12.0` | Ensures compatibility with `pyproject.toml`. |
| `NODE_VERSION` | `20.11.0` | Required for frontend build. |
| `RENDER` | `true` | Tells the build script to skip heavy installs. |
| `GEMMA_PROVIDER` | `google_genai` | **Critical**: Uses API instead of local inference. |
| `GEMMA_MODEL_NAME` | `gemma-2-27b-it` | Or `gemini-2.5-flash` for faster responses. |
| `GEMINI_API_KEY` | *(Paste your API Key)* | From Google AI Studio. |
| `TAVILY_API_KEY` | *(Paste your API Key)* | From Tavily. |
| `ALLOWED_HOSTS` | `*` | **Required**: Allows Render's domain to access the API. |

### Advanced Settings (Optional)

*   **Auto-Deploy**: Yes (default). Pushing to `main` will automatically redeploy.
*   **Health Check Path**: `/health` (Recommended to ensure zero downtime deploys).

5.  Click **Create Web Service**.

## How It Works (Free Tier Optimization)

To fit within the Free Tier limits:

1.  **Gemma via API**: Instead of running Gemma locally (which requires >16GB RAM), we use the `google_genai` provider to call Gemma models hosted by Google via your API Key.
2.  **Smart Build Script**: The `setup_env.sh` script detects `RENDER=true` and skips installing Playwright browsers (Chromium/Firefox), saving build time and disk space.
3.  **Static Frontend**: The React frontend is built into static files served directly by FastAPI, eliminating the need for a separate Node.js server instance.

## Troubleshooting

*   **Build Failures**: Check the logs. If you see memory errors, ensure `RENDER=true` is set.
*   **502 Bad Gateway / 400 Bad Request**:
    *   **502**: The server might be taking too long to start. The Free Tier spins down after inactivity. Give it a minute to wake up.
    *   **400**: Check your `ALLOWED_HOSTS` variable. It must be set (e.g., to `*` or your specific Render URL) because the application uses `TrustedHostMiddleware` which blocks unknown hosts by default.
*   **"Model not found"**: Ensure your `GEMINI_API_KEY` has access to the requested model.
