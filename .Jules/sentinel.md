# Sentinel's Journal

## 2024-05-22 - [Inconsistent Markdown Sanitization]
**Vulnerability:** The project uses `react-markdown` in multiple places. While `ArtifactView` correctly used `rehype-sanitize` (especially important as it uses `rehype-raw`), `ChatMessagesView` did not use `rehype-sanitize`. Although `react-markdown` is safe by default against HTML injection, it relies on implicit default behavior for protocol sanitization (`javascript:` links).
**Learning:** Inconsistent application of security libraries (like `rehype-sanitize`) is a common gap. Developers might assume "Markdown is safe" without considering malicious links or future addition of `rehype-raw`.
**Prevention:** Enforce a reusable `MarkdownRenderer` component that includes `rehype-sanitize` by default, rather than configuring `ReactMarkdown` individually in every view. For this codebase, I added it explicitly to `ChatMessagesView` to match `ArtifactView`'s safety level.
