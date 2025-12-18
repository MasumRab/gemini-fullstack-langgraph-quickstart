#!/bin/bash
set -e

echo "========================================"
echo "  Gemini Fullstack Agent - Setup Script"
echo "========================================"

# 1. Backend Setup
echo ""
echo "[1/3] Setting up Backend..."
cd backend

if command -v uv &> /dev/null; then
    echo "Using uv for dependency management..."
    # Sync dependencies including dev (which now has playwright)
    uv sync --dev

    # Also install the package itself in editable mode if not covered by sync
    uv pip install -e .
else
    echo "uv not found. Falling back to pip..."
    echo "Recommendation: Install uv for faster, more reliable setups."
    pip install -e ".[dev]"
fi

# Install Playwright browsers for the backend verification scripts
echo "Installing Playwright browsers..."
if command -v uv &> /dev/null; then
    uv run playwright install chromium
else
    playwright install chromium
fi

cd ..

# 2. Frontend Setup
echo ""
echo "[2/3] Setting up Frontend..."
cd frontend

if command -v pnpm &> /dev/null; then
    echo "Using pnpm..."
    pnpm install
else
    echo "pnpm not found. Please install pnpm."
    exit 1
fi

cd ..

# 3. Final Check
echo ""
echo "[3/3] Verifying Setup..."
echo "Backend dependencies installed."
echo "Frontend dependencies installed."
echo "Playwright browsers installed."

echo ""
echo "Setup Complete! 🚀"
echo "To run the backend: cd backend && uv run langgraph dev"
echo "To run the frontend: cd frontend && pnpm dev"
