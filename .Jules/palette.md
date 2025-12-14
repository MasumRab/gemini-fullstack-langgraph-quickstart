# Palette's Journal

## 2024-05-22 - Accessibility Gaps in Icon-Only Buttons
**Learning:** The codebase frequently uses icon-only buttons (like the "Stop Generating" button) without associated `aria-label` or accessible names, making them invisible to screen readers.
**Action:** Audit icon-only buttons during component creation and strictly enforce `aria-label` or `sr-only` text descriptions.
