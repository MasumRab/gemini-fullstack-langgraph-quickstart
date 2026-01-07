# Palette's Journal

This journal tracks critical UX and accessibility learnings. It is NOT a log of routine work.

## 2024-05-24 - Focus Visibility Constraints
**Learning:** The design system intentionally suppressed default focus rings (`focus:ring-0`) on the main input to create a "clean" look, inadvertently confusing keyboard users who rely on focus indicators.
**Action:** When customizing input styles, explicitly define `focus-visible` states that harmonize with the design (e.g., using neutral rings) rather than removing them entirely.

## 2024-05-22 - Accessibility Gaps in Icon-Only Buttons
**Learning:** The codebase frequently uses icon-only buttons (like the "Stop Generating" button) without associated `aria-label` or accessible names, making them invisible to screen readers.
**Action:** Audit icon-only buttons during component creation and strictly enforce `aria-label` or `sr-only` text descriptions.

## 2024-05-23 - Accessibility Gaps in Input Forms
**Learning:** Several interactive elements (Textarea, icon-only Buttons) in the main `InputForm` lacked accessible names (`aria-label` or `<label>`), making them difficult for screen reader users to identify.
**Action:** Audit all new interactive components for visible labels or `aria-label` attributes, especially when using icon-only designs or custom inputs.

## 2024-05-25 - Decorative Icons Creating Noise
**Learning:** Decorative icons placed inside semantic elements (like labels or buttons with text) were not hidden from assistive technology, potentially causing screen readers to announce them as "image" or similar, adding unnecessary noise.
**Action:** Systematically apply `aria-hidden="true"` to any icon that is purely decorative and accompanied by descriptive text.
## 2024-12-29 - Accessibility in Artifact Actions
**Learning:** Action buttons in the `ArtifactView` (Copy, Maximize, Close) relied solely on `title` tooltips, which may not be announced by all screen readers or accessible to touch users.
**Action:** Explicitly added `aria-label` to these buttons and `aria-hidden="true"` to their icons to ensure robust accessibility.

## 2025-05-18 - Accessibility in Dynamic Planning Status
**Learning:** The "Planning Mode" UI updates dynamically but lacked `aria-live` regions, making status changes invisible to screen readers without manual polling.
**Action:** Added `role="region"`, `aria-label`, and `aria-live="polite"` to the `PlanningStatus` component wrapper to ensure updates are announced.

## 2025-05-18 - Contrast on Dark Backgrounds
**Learning:** `text-neutral-500` on dark backgrounds (`neutral-900`) often fails WCAG AA contrast requirements for small text.
**Action:** Prefer `text-neutral-400` for secondary text or footers in dark mode to ensure accessibility compliance.
