# 🔐 Authentication Guide: API Keys & OAuth

This guide explains how to authenticate with Google Gemini models using both **AI Studio (API Keys)** and **Vertex AI (OAuth/ADC)**, specifically tailored for Google Colab and local environments.

---

## 1. Google Colab Authentication

### Option A: API Key (Simplest, for AI Studio)
Best for: Quick prototyping, using the free tier of Gemini 1.5 Flash.

1.  **Get your Key**: Go to [Google AI Studio](https://aistudio.google.com/) and create an API key.
2.  **Add to Colab Secrets**:
    *   Open your Colab notebook.
    *   Click the **Key icon** (🔑) on the left sidebar.
    *   Add a new secret name: `GEMINI_API_KEY`.
    *   Paste your key value.
    *   Toggle "Notebook access" to **On**.
3.  **Access in Code**:
    ```python
    from google.colab import userdata
    import os

    os.environ["GEMINI_API_KEY"] = userdata.get('GEMINI_API_KEY')
    ```

### Option B: OAuth / Application Default Credentials (for Vertex AI)
Best for: Production workloads, higher quotas, enterprise data privacy.

1.  **Enable Vertex AI API**: Ensure the Vertex AI API is enabled in your Google Cloud Console project.
2.  **Authenticate in Cell**: Run the following code in your notebook.
    ```python
    from google.colab import auth
    auth.authenticate_user()
    print("Authenticated successfully with Google Cloud!")
    ```
    *   This opens a popup to login with your Google account.
3.  **Set Project ID**:
    ```python
    PROJECT_ID = "your-google-cloud-project-id"
    !gcloud config set project {PROJECT_ID}
    ```
4.  **Use Vertex AI Models**:
    Instead of `ChatGoogleGenerativeAI`, you would typically use `ChatVertexAI` (requires `langchain-google-vertexai`).
    ```python
    from langchain_google_vertexai import ChatVertexAI
    llm = ChatVertexAI(model="gemini-2.5-pro", project=PROJECT_ID)
    ```

---

## 2. Local Development Authentication

### Option A: API Key (Env File)
1.  Create a `.env` file in your root directory.
2.  Add: `GEMINI_API_KEY=your_api_key_here`.
3.  Load it in python:
    ```python
    from dotenv import load_dotenv
    load_dotenv()
    ```

### Option B: OAuth / ADC (Vertex AI)
1.  **Install gcloud CLI**: [Download and install](https://cloud.google.com/sdk/docs/install).
2.  **Login**:
    ```bash
    gcloud auth application-default login
    ```
    *   This saves a JSON credential file locally that libraries like LangChain and Google Cloud SDK automatically detect.
3.  **Set Quota Project**:
    ```bash
    gcloud auth application-default set-quota-project your-project-id
    ```

---

## 🔍 Which one should I use?

| Method | Best For | Quotas | Cost |
|--------|----------|--------|------|
| **API Key (AI Studio)** | Prototyping, Personal Projects | Free Tier Available (Strict limits on newer models) | Free (within limits), Pay-as-you-go |
| **OAuth (Vertex AI)** | Enterprise, Production, High Scale | Higher, adjustable per project | Pay-as-you-go (Google Cloud billing) |

> **Note on "Resource Exhausted"**: If you hit quota limits with an API Key on the free tier (especially with Gemini 2.0/2.5 models), switching to Vertex AI (OAuth) with a billing-enabled project often resolves this, as you move to a paid tier with higher limits.
