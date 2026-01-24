## 2025-02-18 - [Inconsistent Markdown Sanitization]
**Vulnerability:** `ChatMessagesView` rendered user/AI markdown without explicit `rehype-sanitize` configuration, while `ArtifactView` correctly used it. Although `react-markdown` is generally safe by default, relying on defaults without explicit defense-in-depth is a risk, especially with `javascript:` vectors or if `rehype-raw` is accidentally enabled later.
**Learning:** Security dependencies (`rehype-sanitize`) were present in the project but applied inconsistently across components. Dependencies alone do not guarantee security; usage must be verified.
**Prevention:** Audit all `ReactMarkdown` usages to ensure a consistent security configuration (e.g., a shared `safeMarkdownPlugins` constant) is applied everywhere.
