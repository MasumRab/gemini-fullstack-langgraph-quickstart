# Palette's Journal

## 2024-05-22 - Accessibility Gaps in Icon-Only Buttons
**Learning:** The codebase frequently uses icon-only buttons (like the "Stop Generating" button) without associated `aria-label` or accessible names, making them invisible to screen readers.
**Action:** Audit icon-only buttons during component creation and strictly enforce `aria-label` or `sr-only` text descriptions.
## 2024-05-23 - Accessibility Gaps in Input Forms **Learning:** Several interactive elements (Textarea, icon-only Buttons) in the main `InputForm` lacked accessible names (`aria-label` or `<label>`), making them difficult for screen reader users to identify. **Action:** Audit all new interactive components for visible labels or `aria-label` attributes, especially when using icon-only designs or custom inputs.
