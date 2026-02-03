## 2024-05-23 - Lazy Loading Providers
**Learning:** Eager initialization of external service adapters (like `SearchProvider`s) slows down startup and complicates testing. Using a registry of classes (`_PROVIDER_CLASSES`) and lazy instantiation on first access significantly improves startup performance and testability.
**Action:** When integrating multiple external services, always prefer lazy initialization patterns to avoid "pay for what you don't use" penalties.
