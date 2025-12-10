# Testing Guide

This document describes the comprehensive test suite added for the recent code changes.

## Overview

Tests have been added for all modified and new files in this branch:
- **Backend (Python/pytest)**: 4 new test files covering nodes, registry, configuration, and utilities
- **Frontend (TypeScript/Vitest)**: 1 new test file covering the useAgentState hook

## Backend Tests

### Running Backend Tests

```bash
cd backend
pytest tests/ -v
```

### Test Files

#### 1. `tests/test_nodes.py` (most comprehensive)
Tests all node functions in `src/agent/nodes.py`:
- `generate_query` - Query generation from user input
- `planning_mode` - Planning step creation and management
- `planning_wait` - Planning confirmation workflow
- `web_research` - Web search and scraping
- `validate_web_results` - Result validation and filtering
- `reflection` - Knowledge gap identification
- `finalize_answer` - Final answer generation

**Test Coverage**:
- Happy path scenarios
- Edge cases (empty inputs, errors, large datasets)
- Integration workflows
- State immutability
- Error handling

**Run specific test class**:
```bash
pytest tests/test_nodes.py::TestGenerateQuery -v
pytest tests/test_nodes.py::TestPlanningMode -v
```

#### 2. `tests/test_registry.py`
Tests the `NodeRegistry` class in `src/agent/registry.py`:
- Node registration and retrieval
- Node listing
- Duplicate handling
- Special character support
- Edge cases

**Run**:
```bash
pytest tests/test_registry.py -v
```

#### 3. `tests/test_configuration.py`
Tests the `Configuration` model in `src/agent/configuration.py`:
- Default values
- Custom initialization
- Field validation
- Type checking
- Serialization

**Run**:
```bash
pytest tests/test_configuration.py -v
```

#### 4. `tests/test_utils.py`
Tests utility functions in `src/agent/utils.py`:
- `format_sources` function
- Source formatting and numbering
- Edge cases (empty, malformed data)
- Unicode and special character handling

**Run**:
```bash
pytest tests/test_utils.py -v
```

### Running with Coverage

```bash
cd backend
pytest tests/ --cov=src/agent --cov-report=html
# Open htmlcov/index.html to view coverage report
```

## Frontend Tests

### Setup Required

First, install the new test dependencies:

```bash
cd frontend
npm install
```

New dependencies added:
- `vitest` - Test runner
- `@testing-library/react` - React testing utilities
- `@testing-library/jest-dom` - DOM matchers
- `jsdom` - DOM environment for tests
- `@vitest/ui` - Visual test UI

### Running Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage
```

### Test Files

#### `src/hooks/useAgentState.test.ts`
Comprehensive tests for the `useAgentState` hook:
- Initialization
- Event handling (web_research, planning_mode, planning_wait, reflection, finalize_answer)
- State updates
- Activity log management
- State reset
- Edge cases and error handling
- Type safety
- Integration scenarios

**Test Coverage**:
- All event types
- State immutability
- Rapid successive events
- Malformed data handling
- Large datasets
- Complete workflow integration

### Test Configuration

- **`vitest.config.ts`**: Vitest configuration with React support
- **`src/test/setup.ts`**: Global test setup (matchers, cleanup, mocks)

## Test Organization

### Backend Test Structure