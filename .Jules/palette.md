# Palette's Journal

## 2025-02-18 - First Impressions
**Learning:** The codebase uses `SidebarProvider` which conveniently wraps the app in `TooltipProvider`. This is a good pattern as it avoids prop drilling or repeated wrapping for tooltips.
**Action:** Always check `root.tsx` or main layout providers before adding global providers like `TooltipProvider`.

## 2025-02-18 - Dependency Constraints
**Learning:** Adding new dependencies (even devDependencies like `@tailwindcss/vite`) to a `pnpm` workspace can cause major lockfile churn and conflicts.
**Action:** Strictly adhere to "Zero Dependency" for micro-UX tasks unless explicitly authorized. Use native HTML attributes or existing utilities.
