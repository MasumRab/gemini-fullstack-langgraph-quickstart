# Frontend Testing Guide

This document outlines the testing setup for the React + TypeScript frontend.

## Testing Stack

The project uses the following tools for testing:
- **Unit/Integration Tests**: [Vitest](https://vitest.dev/) + [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- **End-to-End Tests**: [Playwright](https://playwright.dev/)

## Running Tests

### Unit and Integration Tests

To run the unit tests (Vitest):

```bash
cd frontend
pnpm test
```

To run in CI mode (single run, no watch):

```bash
pnpm test --run
```

To run with UI:

```bash
pnpm test:ui
```

To run coverage report:

```bash
pnpm test:coverage
```

### End-to-End Tests

To run the E2E tests (Playwright):

1.  Install browsers (first time only):
    ```bash
    cd frontend
    npx playwright install
    ```

2.  Run tests:
    ```bash
    npx playwright test
    ```

    This will automatically start the development server if configured in `playwright.config.ts`.

## Test Structure

### Unit Tests
Located in `src/` alongside components (e.g., `InputForm.test.tsx`) or in `__tests__` directories.

Key test files:
- `src/hooks/useAgentState.test.ts`: Tests for the main agent state logic.
- `src/components/InputForm.test.tsx`: Tests for the input form.
- `src/components/ActivityTimeline.test.tsx`: Tests for the activity timeline.

### E2E Tests
Located in `e2e/`.

Key test files:
- `e2e/autofocus.spec.ts`: verifies autofocus behavior.
- `e2e/clear-input.spec.ts`: verifies input clearing behavior.

## Writing Tests

### Unit Tests Example
```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import MyComponent from './MyComponent';

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });
});
```

### E2E Tests Example
```typescript
import { test, expect } from '@playwright/test';

test('has title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/Agent/);
});
```
