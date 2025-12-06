# Backend Test Suite

This directory contains comprehensive unit tests for the agent backend.

## Test Structure

### test_configuration.py
Tests for the Configuration class including:
- Default value validation
- Configuration from runnable config
- Environment variable handling
- Type conversion and validation
- Pydantic model validation

### test_nodes.py
Comprehensive tests for all LangGraph nodes including:
- `generate_query` - Query generation from user input
- `continue_to_web_research` - Fan-out routing logic
- `web_research` - Google Search API integration
- `planning_mode` - Planning step creation and command handling
- `planning_wait` - Planning confirmation flow
- `planning_router` - Routing logic for planning commands
- `validate_web_results` - Keyword-based result validation
- `reflection` - Knowledge gap identification
- `evaluate_research` - Research loop control
- `finalize_answer` - Final response synthesis
- Helper functions: `_flatten_queries`, `_keywords_from_queries`

### test_registry.py
Tests for the GraphRegistry documentation system:
- Node registration and metadata tracking
- Edge documentation
- Notes and annotations
- Overview rendering

### test_utils.py
Tests for utility functions:
- `get_citations` - Citation extraction from API responses
- `resolve_urls` - URL shortening and mapping
- `insert_citation_markers` - Citation insertion into text
- `get_research_topic` - Topic extraction from messages

## Running Tests

```bash
# Run all tests
cd backend
pytest

# Run specific test file
pytest tests/test_nodes.py

# Run with coverage
pytest --cov=agent --cov-report=html

# Run specific test
pytest tests/test_nodes.py::TestGenerateQuery::test_generate_query_basic

# Run with verbose output
pytest -v
```

## Test Coverage

The test suite aims for comprehensive coverage of:
- Happy path scenarios
- Edge cases and boundary conditions
- Error handling and graceful degradation
- State management and transitions
- Mock external dependencies (LLM calls, API requests)
- Configuration variations
- Type validation

## Mocking Strategy

- LLM calls are mocked to avoid external dependencies
- Google Search API responses are mocked with realistic structures
- Configuration is injected via RunnableConfig for isolation
- State is constructed programmatically for predictable test scenarios

## Contributing

When adding new features:
1. Add corresponding tests to the appropriate test file
2. Follow existing test naming conventions: `test_<feature>_<scenario>`
3. Use descriptive docstrings for test methods
4. Mock external dependencies consistently
5. Test both success and failure paths