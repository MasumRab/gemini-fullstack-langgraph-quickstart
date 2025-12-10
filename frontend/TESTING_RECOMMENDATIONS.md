# Frontend Testing Setup Recommendations

## Overview
The frontend currently has no test setup. This document outlines recommendations for implementing comprehensive testing for the React + TypeScript frontend, particularly for the new `useAgentState` hook.

## Recommended Testing Stack

### Core Testing Libraries
```json
{
  "devDependencies": {
    "@testing-library/react": "^14.0.0",
    "@testing-library/react-hooks": "^8.0.1",
    "@testing-library/jest-dom": "^6.1.0",
    "@testing-library/user-event": "^14.5.0",
    "vitest": "^1.0.0",
    "@vitest/ui": "^1.0.0",
    "jsdom": "^23.0.0",
    "happy-dom": "^12.10.0"
  }
}
```

## Recommended Test Files

### 1. `frontend/src/hooks/useAgentState.test.ts`

```typescript
import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useAgentState } from './useAgentState';

// Mock the LangGraph SDK
vi.mock('@langchain/langgraph-sdk/react', () => ({
  useStream: vi.fn(() => ({
    messages: [],
    isLoading: false,
    submit: vi.fn(),
    stop: vi.fn(),
  })),
}));

describe('useAgentState', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should initialize with default state', () => {
    const { result } = renderHook(() => useAgentState());

    expect(result.current.processedEventsTimeline).toEqual([]);
    expect(result.current.historicalActivities).toEqual({});
    expect(result.current.planningContext).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('should update planning context on planning_mode event', () => {
    const { result } = renderHook(() => useAgentState());
    
    act(() => {
      // Simulate planning mode event
      result.current.thread.onUpdateEvent?.({
        planning_mode: {
          planning_steps: [{ id: '1', title: 'Step 1' }],
          planning_status: 'awaiting_confirmation',
          planning_feedback: ['Review the plan'],
        },
      });
    });

    expect(result.current.planningContext).toEqual({
      steps: [{ id: '1', title: 'Step 1' }],
      status: 'awaiting_confirmation',
      feedback: ['Review the plan'],
    });
  });

  it('should handle submit with correct effort mapping', () => {
    const { result } = renderHook(() => useAgentState());
    const mockSubmit = vi.fn();
    result.current.thread.submit = mockSubmit;

    act(() => {
      result.current.handleSubmit('Test query', 'medium', 'gemini-2.5-flash');
    });

    expect(mockSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        initial_search_query_count: 3,
        max_research_loops: 3,
        reasoning_model: 'gemini-2.5-flash',
      })
    );
  });

  it('should handle planning commands', () => {
    const { result } = renderHook(() => useAgentState());
    const mockSubmit = vi.fn();
    result.current.thread.submit = mockSubmit;

    act(() => {
      result.current.handlePlanningCommand('/confirm_plan');
    });

    expect(mockSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        messages: expect.arrayContaining([
          expect.objectContaining({ content: '/confirm_plan' }),
        ]),
      })
    );
  });

  it('should process web_research events correctly', () => {
    const { result } = renderHook(() => useAgentState());

    act(() => {
      result.current.thread.onUpdateEvent?.({
        web_research: {
          sources_gathered: [
            { label: 'Source1' },
            { label: 'Source2' },
          ],
        },
      });
    });

    expect(result.current.processedEventsTimeline).toHaveLength(1);
    expect(result.current.processedEventsTimeline[0].title).toBe('Web Research');
  });

  it('should handle errors correctly', () => {
    const { result } = renderHook(() => useAgentState());

    act(() => {
      result.current.thread.onError?.({ message: 'Test error' });
    });

    expect(result.current.error).toBe('Test error');
  });

  it('should clear planning context on new submit', () => {
    const { result } = renderHook(() => useAgentState());
    
    // Set initial planning context
    act(() => {
      result.current.thread.onUpdateEvent?.({
        planning_mode: {
          planning_steps: [{ id: '1' }],
          planning_status: 'confirmed',
          planning_feedback: [],
        },
      });
    });

    expect(result.current.planningContext).not.toBeNull();

    // Submit new query
    act(() => {
      result.current.handleSubmit('New query', 'low', 'model');
    });

    expect(result.current.planningContext).toBeNull();
  });

  it('should map effort levels correctly', () => {
    const { result } = renderHook(() => useAgentState());
    const mockSubmit = vi.fn();
    result.current.thread.submit = mockSubmit;

    // Test low effort
    act(() => {
      result.current.handleSubmit('Query', 'low', 'model');
    });
    expect(mockSubmit).toHaveBeenLastCalledWith(
      expect.objectContaining({
        initial_search_query_count: 1,
        max_research_loops: 1,
      })
    );

    // Test high effort
    act(() => {
      result.current.handleSubmit('Query', 'high', 'model');
    });
    expect(mockSubmit).toHaveBeenLastCalledWith(
      expect.objectContaining({
        initial_search_query_count: 5,
        max_research_loops: 10,
      })
    );
  });

  it('should track historical activities after finalization', async () => {
    const { result } = renderHook(() => useAgentState());

    // Simulate finalize event
    act(() => {
      result.current.thread.onUpdateEvent?.({
        finalize_answer: { data: 'Done' },
      });
    });

    // Simulate completion with AI message
    act(() => {
      result.current.thread.messages = [
        { type: 'ai', id: 'msg-1', content: 'Answer' },
      ];
      result.current.thread.isLoading = false;
    });

    await waitFor(() => {
      expect(Object.keys(result.current.historicalActivities).length).toBe(1);
    });
  });

  it('should handle cancel correctly', () => {
    const { result } = renderHook(() => useAgentState());
    const mockStop = vi.fn();
    const mockReload = vi.fn();
    
    result.current.thread.stop = mockStop;
    global.location = { reload: mockReload } as any;

    act(() => {
      result.current.handleCancel();
    });

    expect(mockStop).toHaveBeenCalled();
    expect(mockReload).toHaveBeenCalled();
  });
});
```

### 2. Vitest Configuration

Create `frontend/vitest.config.ts`:

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react-swc';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.test.{ts,tsx}',
        '**/*.spec.{ts,tsx}',
      ],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

### 3. Test Setup File

Create `frontend/src/test/setup.ts`:

```typescript
import { expect, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
import * as matchers from '@testing-library/jest-dom/matchers';

expect.extend(matchers);

afterEach(() => {
  cleanup();
});
```

### 4. Integration Tests for App.tsx

Create `frontend/src/App.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import App from './App';

vi.mock('@/hooks/useAgentState', () => ({
  useAgentState: () => ({
    thread: { messages: [], isLoading: false },
    processedEventsTimeline: [],
    historicalActivities: {},
    planningContext: null,
    error: null,
    scrollAreaRef: { current: null },
    handleSubmit: vi.fn(),
    handlePlanningCommand: vi.fn(),
    handleCancel: vi.fn(),
  }),
}));

describe('App', () => {
  it('should render welcome screen when no messages', () => {
    render(<App />);
    expect(screen.getByText(/welcome/i)).toBeInTheDocument();
  });

  it('should render error state when error exists', () => {
    // Mock with error state
    vi.mocked(useAgentState).mockReturnValue({
      thread: { messages: [{ type: 'human', content: 'Hi' }], isLoading: false },
      error: 'Test error',
      // ... other props
    } as any);

    render(<App />);
    expect(screen.getByText(/error/i)).toBeInTheDocument();
    expect(screen.getByText(/test error/i)).toBeInTheDocument();
  });

  it('should render chat view when messages exist', () => {
    vi.mocked(useAgentState).mockReturnValue({
      thread: {
        messages: [{ type: 'human', content: 'Hello', id: '1' }],
        isLoading: false,
      },
      error: null,
      // ... other props
    } as any);

    render(<App />);
    expect(screen.getByText(/hello/i)).toBeInTheDocument();
  });
});
```

## Installation Commands

```bash
cd frontend
npm install --save-dev \
  @testing-library/react \
  @testing-library/react-hooks \
  @testing-library/jest-dom \
  @testing-library/user-event \
  vitest \
  @vitest/ui \
  jsdom \
  happy-dom
```

## Running Tests

Add to `frontend/package.json`:

```json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest --coverage"
  }
}
```

Run tests:
```bash
npm run test           # Run tests in watch mode
npm run test:ui        # Run with UI
npm run test:coverage  # Run with coverage report
```

## Test Coverage Goals

- **Hooks**: 90%+ coverage for `useAgentState`
- **Components**: 80%+ coverage for UI components
- **Integration**: Key user flows tested end-to-end
- **Edge Cases**: Error states, loading states, empty states

## Additional Considerations

### Mocking External Dependencies

```typescript
// Mock LangGraph SDK
vi.mock('@langchain/langgraph-sdk/react', () => ({
  useStream: vi.fn(),
}));

// Mock API calls
vi.mock('@/lib/api', () => ({
  fetchData: vi.fn(),
}));
```

### Testing Async Behavior

```typescript
it('should handle async updates', async () => {
  const { result } = renderHook(() => useAgentState());
  
  await act(async () => {
    await result.current.handleSubmit('query', 'medium', 'model');
  });

  await waitFor(() => {
    expect(result.current.thread.isLoading).toBe(false);
  });
});
```

### Testing Custom Hooks

Use `@testing-library/react-hooks` for isolated hook testing:

```typescript
import { renderHook, act } from '@testing-library/react-hooks';

it('should update state correctly', () => {
  const { result } = renderHook(() => useAgentState());
  
  act(() => {
    result.current.handleSubmit('test', 'low', 'model');
  });
  
  expect(result.current.thread.messages.length).toBeGreaterThan(0);
});
```

## Benefits of This Setup

1. **Fast**: Vitest is significantly faster than Jest
2. **Type-Safe**: Full TypeScript support
3. **React-Friendly**: Testing Library best practices
4. **Coverage**: Built-in coverage reports
5. **Watch Mode**: Instant feedback during development
6. **UI Mode**: Visual test runner with Vitest UI

## Migration Path

1. Install dependencies
2. Create configuration files
3. Add test scripts to package.json
4. Write tests for critical paths first (useAgentState)
5. Gradually increase coverage
6. Set up CI/CD integration

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Frontend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: cd frontend && npm ci
      - run: cd frontend && npm run test -- --run
      - run: cd frontend && npm run test:coverage
```