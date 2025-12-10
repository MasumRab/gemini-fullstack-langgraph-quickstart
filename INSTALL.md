# Installation Guide

This guide covers installation steps for the backend of the Gemini Fullstack LangGraph Quickstart.

## Supported Python Versions

The backend is compatible with Python 3.12 and 3.13.

- **Recommended:** Python 3.12.x
- **Supported:** Python 3.12.3, 3.12.12, 3.13.9+

---

## 1. Standard Pip Installation (Linux/macOS)

For standard environments using Python 3.12:

```bash
cd backend
pip install .
```

### Python 3.13 Compatibility Note

If you are using **Python 3.13**, you may encounter issues with dependencies like `torch` or `faiss-cpu` if stable wheels are not yet available for your specific platform.

**Fix:** Install the pre-release (nightly) version of PyTorch before installing the backend package:

```bash
# Install PyTorch Nightly (CPU version)
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cpu

# Then install the backend
cd backend
pip install .
```

---

## 2. Windows Installation

Ensure you have Python 3.12 or 3.13 installed.

### Standard Install

```powershell
cd backend
pip install .
```

### Troubleshooting Windows Issues

If you encounter "Microsoft Visual C++ 14.0 or greater is required" errors (common with `faiss-cpu` or `sentence-transformers`):

1.  **Option A (Recommended):** Use Conda (see below). Conda handles binary dependencies automatically.
2.  **Option B:** Install [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).
3.  **Option C:** For Python 3.13 on Windows, `torch` support is available but might require the nightly command mentioned in the Linux section above.

---

## 3. Conda Installation (Recommended for Cross-Platform Compatibility)

Conda is the most reliable way to handle dependencies across Windows, Linux, and macOS, especially for varying Python versions.

1.  **Install Anaconda or Miniconda.**
2.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```
3.  **Create the environment:**
    ```bash
    conda env create -f environment.yml
    ```
    *This creates an environment named `gemini-fullstack-langgraph` with Python and necessary binaries.*
4.  **Activate the environment:**
    ```bash
    conda activate gemini-fullstack-langgraph
    ```

---

## 4. Google Colab

To run the agent in Google Colab, you can use the provided setup notebook:

- [Open notebooks/colab_setup.ipynb](../notebooks/colab_setup.ipynb)

**Quick Instructions for Colab:**

1.  Clone the repository.
2.  Run the setup cell in the notebook, which handles:
    - Cloning the code.
    - Uninstalling conflicting pre-installed packages (e.g., legacy `tensorflow` or `google-ai-generativelanguage` which require older Protobuf versions).
    - Installing the agent backend.
3.  Set your `GEMINI_API_KEY`.

*Note: If you choose to install manually in a Colab cell, run `!pip uninstall -y google-ai-generativelanguage tensorflow` first to avoid `pip` dependency resolver errors.*

---

## 5. Verification

To verify your installation was successful, run the CLI example:

```bash
# Ensure you are in the backend directory and your .env has the GEMINI_API_KEY
python ../examples/cli_research.py "What is LangGraph?"
```

## Troubleshooting

### Protobuf Conflicts (e.g., `google-ai-generativelanguage` or `tensorflow`)

If you see an error like:
> `google-ai-generativelanguage 0.6.15 requires protobuf!=...<6.0.0dev, but you have protobuf 6.33.2`

This happens because the agent requires a newer version of `protobuf` (via `langgraph-api`), while some pre-installed environment packages require an older version.

**Solution:** Uninstall the conflicting packages if you are not using them (which is usually the case for this agent).

```bash
pip uninstall -y google-ai-generativelanguage tensorflow grpcio-status
pip install .
```
