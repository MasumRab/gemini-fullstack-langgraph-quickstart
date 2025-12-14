# Palette's Journal

This journal tracks critical UX and accessibility learnings. It is NOT a log of routine work.

## 2024-05-24 - Focus Visibility Constraints
**Learning:** The design system intentionally suppressed default focus rings (`focus:ring-0`) on the main input to create a "clean" look, inadvertently confusing keyboard users who rely on focus indicators.
**Action:** When customizing input styles, explicitly define `focus-visible` states that harmonize with the design (e.g., using neutral rings) rather than removing them entirely.
