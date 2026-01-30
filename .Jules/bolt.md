## 2024-05-23 - Lazy Loading Search Providers
**Learning:** Moving heavy SDK imports (like `google.genai`) inside methods significantly improves startup time and robustness.
**Action:** Use local imports inside factory methods for optional integrations or heavy dependencies. When testing, patch the class at its *source definition*, not the module namespace.
