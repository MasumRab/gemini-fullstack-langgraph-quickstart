# Bolt's Journal

## 2024-05-22 - [Performance Persona Initialization]
**Learning:** Performance optimizations must be strictly measurable and non-breaking.
**Action:** Always verify with tests and linting before submitting.

## 2024-05-23 - [InputForm Re-renders]
**Learning:** Passing unstable function references (like inline arrow functions) to `onSubmit` or `onCancel` in `InputForm` breaks `React.memo`, causing the entire form to re-render on every parent update (like streaming tokens).
**Action:** Use `useCallback` for event handlers passed to memoized components.

## 2024-05-23 - [ChatMessagesView Prop Stability]
**Learning:** Even with `React.memo`, if specific props (like `isOverallLoading`) change for *all* items in a list, the entire list re-renders.
**Action:** Only pass dynamic props to the specific item that needs them (e.g., the last message), or split components so static history doesn't listen to active state.
