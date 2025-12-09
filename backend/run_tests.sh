#!/bin/bash
# Comprehensive test runner for backend tests

set -e

echo "================================"
echo "Running Backend Test Suite"
echo "================================"

cd "$(dirname "$0")"

echo ""
echo "1. Running MCP Config Tests..."
python -m pytest tests/test_mcp_config.py -v

echo ""
echo "2. Running MCP Integration Tests..."
python -m pytest tests/test_mcp_integration.py -v

echo ""
echo "3. Running Registry Tests..."
python -m pytest tests/test_registry.py -v

echo ""
echo "4. Running Utils Tests..."
python -m pytest tests/test_utils.py -v

echo ""
echo "5. Running Nodes Helper Tests..."
python -m pytest tests/test_nodes_helpers.py -v

echo ""
echo "6. Running Planning Tests..."
python -m pytest tests/test_planning.py -v

echo ""
echo "7. Running Validation Tests..."
python -m pytest tests/test_validate_web_results.py -v

echo ""
echo "8. Running Graph Integration Tests..."
python -m pytest tests/test_graph_integration.py -v

echo ""
echo "================================"
echo "All Tests Completed Successfully!"
echo "================================"

# Run with coverage if requested
if [ "${1:-}" = "--coverage" ]; then
    echo ""
    echo "Generating Coverage Report..."
    python -m pytest tests/ --cov=agent --cov-report=html --cov-report=term
    echo "Coverage report generated in htmlcov/index.html"
fi