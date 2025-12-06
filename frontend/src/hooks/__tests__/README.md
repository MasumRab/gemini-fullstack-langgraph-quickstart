# Frontend Hook Tests

This directory contains tests for custom React hooks.

## useAgentState.test.ts

Comprehensive tests for the `useAgentState` hook covering:

### Core Functionality
- Initialization with correct default state
- API URL selection based on environment
- Ref management for scroll behavior

### handleSubmit
- Input validation (empty, whitespace)
- Effort level mapping (low, medium, high)
- Message ID generation
- State reset on new submission
- Message history accumulation
- Planning context reset

### handlePlanningCommand
- Command submission with current config
- Config persistence across commands
- Message appending behavior

### handleCancel
- Stream stopping
- Page reload trigger

### Event Processing
- `generate_query` - Search query generation events
- `planning_mode` - Planning step creation
- `planning_wait` - Confirmation waiting state
- `web_research` - Source gathering and deduplication
- `reflection` - Research analysis events
- `finalize_answer` - Final answer composition
- Event timeline accumulation
- Unknown event handling

### Historical Activities
- Timeline saving after completion
- AI message filtering
- Message ID validation
- Loading state consideration

### Error Handling
- Error state updates
- Graceful handling of missing fields

## Running Tests

```bash
# Install dependencies
cd frontend
npm install

# Run tests
npm test

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage

# Run specific test file
npx vitest src/hooks/__tests__/useAgentState.test.ts

# Run in watch mode
npx vitest --watch
```

## Test Tools

- **Vitest** - Fast unit test framework
- **@testing-library/react** - React component testing utilities
- **jsdom** - DOM environment for Node.js

## Mocking Strategy

- `useStream` from LangGraph SDK is mocked to control stream behavior
- Event callbacks are tested by invoking them directly
- DOM interactions use Testing Library utilities
- Time-dependent logic (Date.now) is mocked where needed

## Contributing

When modifying the hook:
1. Update corresponding tests
2. Add tests for new event types
3. Test both success and error paths
4. Verify cleanup and memory management
5. Ensure tests are deterministic (no flaky tests)