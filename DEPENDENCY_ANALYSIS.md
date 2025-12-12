# Dependency Analysis & Optimization Strategy

This document details the package conflicts identified across different Python environments (Google Colab vs. Local Development) and provides optimized strategies for stability.

## 🚨 Critical Conflict Zones

### 1. Google AI SDKs (`google-genai` vs. `google-generativeai`)
*   **The Conflict:**
    *   **Project Requirement:** Uses `google-genai` (The new Python SDK for Gemini API) and `google-ai-generativelanguage>=0.9.0`.
    *   **Environment Conflict:** Google Colab and `langchain-google-genai` often pre-install or depend on `google-generativeai` (The older SDK), which strictly pins `google-ai-generativelanguage==0.6.15`.
*   **Impact:** `pip` dependency resolver errors, `ImportError` on new features.
*   **Resolution:** Prioritize the **New SDK**. Uninstall the old one if it conflicts.

### 2. Numpy (`v1` vs. `v2`)
*   **The Conflict:**
    *   **Project Requirement:** Modern data science stacks (Pandas 2+, etc.) are moving to Numpy 2.0.
    *   **Environment Conflict:** Many legacy ML libraries (e.g., `opencv-python-headless`, `numba`, `dopamine-rl` in Colab) explicitly pin `numpy<2.0` or `<1.25`.
*   **Impact:** Runtime warnings or binary incompatibility errors (C-extension mismatches).
*   **Resolution:** For Colab, stick to `numpy<2.0` explicitly if visual tools are used. For pure Agent logic, Numpy 2.0 is usually fine if we uninstall the complaining legacy libs.

### 3. Pydantic (`v1` vs. `v2`)
*   **The Conflict:**
    *   **Project Requirement:** `langchain` and `langgraph` heavily rely on Pydantic v2 for validation and serialization.
    *   **Environment Conflict:** `gradio` (version < 5.0) and some older serving frameworks pin `pydantic<2.0`.
*   **Impact:** `AttributeError` on model fields (e.g., `.dict()` vs `.model_dump()`).
*   **Resolution:** Enforce Pydantic v2. Upgrade conflicting tools (e.g., use `gradio>=5.0`).

---

## 🛠️ Optimization Strategies by Environment

### A. Google Colab (Python 3.10)
*   **Context:** Pre-loaded environment with older ML libraries (`tensorflow`, `numpy<2`, `google-generativeai`).
*   **Strategy:** "Aggressive Clean Slate"
    1.  **Uninstall Conflicts:** Remove `google-generativeai`, `tensorflow` (if unused by agent), and `google-ai-generativelanguage` before installation.
    2.  **Force Reinstall:** Install the project package with `--force-reinstall` to overwrite any lingering system packages.
    3.  **Runtime Restart:** Mandatory restart to unload the pre-imported incompatible modules.

**Recommended Setup Command:**
```python
!pip uninstall -y google-ai-generativelanguage google-generativeai tensorflow grpcio-status
!pip install -e .
# RESTART RUNTIME NOW
```

### B. Local Environment (Python 3.11 / 3.12)
*   **Context:** Clean, isolated virtual environment (conda or venv).
*   **Strategy:** "Modern Standard"
    1.  **Python Version:** Use Python 3.11 or 3.12. Avoid 3.13 for now (Torch support is still experimental/nightly).
    2.  **Dependency Manager:** `uv` or `poetry` are recommended over `pip` for faster resolution, but standard `pip` with `venv` works fine if `pyproject.toml` is respected.
    3.  **Constraint:** None usually needed. The project defaults (Numpy 2, Pydantic 2) work best here.

### C. Legacy/Production (Python 3.9 / 3.10)
*   **Context:** Existing servers where upgrading Python is hard.
*   **Strategy:** "Pinned Compatibility"
    1.  **Pin Numpy:** Add `numpy<2.0` to constraints.
    2.  **Pin Pydantic:** Ensure no V1 dependencies exist.
    3.  **Caveat:** `langgraph` features are optimized for 3.11+. Async performance may be lower on 3.10.

---

## 📦 Package Management Recommendation

For this specific project, we recommend managing dependencies via `pyproject.toml` (flexible) but providing a `constraints.txt` for specific environments if issues persist.

**Proposed Update to `pyproject.toml` rules:**
*   Lower `requires-python` to `>=3.10` to officially support Colab.
*   Keep `google-ai-generativelanguage>=0.9.0` to force the new SDK features.
*   Allow `numpy` range to be flexible (`>=1.26`) rather than strict if not required.
