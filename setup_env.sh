#!/bin/bash
set -e

echo "========================================"
echo "  Gemini Fullstack Agent - Setup Script"
echo "========================================"

# 0. Ensure Node.js and pnpm are available (Required for Frontend)
# This is critical for Render.com native Python runtime which lacks Node by default.
echo ""
echo "[0/3] Checking System Dependencies..."

if ! command -v node &> /dev/null; then
    echo "Node.js not found. Installing Node.js v20 (Local Standalone)..."
    NODE_VERSION="v20.11.0"
    NODE_DIST="node-$NODE_VERSION-linux-x64"
    wget -q "https://nodejs.org/dist/$NODE_VERSION/$NODE_DIST.tar.xz"
    tar -xf "$NODE_DIST.tar.xz"
    rm "$NODE_DIST.tar.xz"

    # Add to PATH for this session
    export PATH="$PWD/$NODE_DIST/bin:$PATH"
    echo "Node.js installed to $PWD/$NODE_DIST"
else
    echo "Node.js found: $(node -v)"
fi

if ! command -v pnpm &> /dev/null; then
    echo "pnpm not found. Installing pnpm..."
    npm install -g pnpm
else
    echo "pnpm found: $(pnpm -v)"
fi


# 1. Backend Setup
echo ""
echo "[1/3] Setting up Backend..."
cd backend

if command -v uv &> /dev/null; then
    echo "Using uv for dependency management..."
    # Sync dependencies including dev (which now has playwright)
    uv sync --dev || uv pip install -e ".[dev]"

    # Also install the package itself in editable mode if not covered by sync
    uv pip install -e .
else
    echo "uv not found. Falling back to pip..."
    echo "Recommendation: Install uv for faster, more reliable setups."
    pip install -e ".[dev]"
    # Ensure uvicorn is installed for production run
    pip install uvicorn
fi

# Install Playwright browsers for the backend verification scripts
# Skip on Render to save resources unless explicitly required
if [ "$RENDER" = "true" ]; then
    echo "Running on Render. Skipping Playwright browser installation to save resources."
    echo "If you need Playwright, set RENDER=false or manually install."
else
    echo "Installing Playwright browsers..."
    if command -v uv &> /dev/null; then
        uv run playwright install chromium
    else
        playwright install chromium
    fi
fi

cd ..

# 2. Frontend Setup
echo ""
echo "[2/3] Setting up Frontend..."
cd frontend

if command -v pnpm &> /dev/null; then
    echo "Using pnpm..."
    pnpm install

    # Build for production (Generates dist/ folder for backend to serve)
    echo "Building Frontend for Production..."
    pnpm run build
else
    echo "ERROR: pnpm not found even after installation attempt."
    exit 1
fi

cd ..

# 3. Final Check
echo ""
echo "[3/3] Verifying Setup..."
echo "Backend dependencies installed."
echo "Frontend dependencies installed and built."
if [ "$RENDER" != "true" ]; then
    echo "Playwright browsers installed."
else
    echo "Playwright skipped (Render environment)."
fi

echo ""
echo "Setup Complete! 🚀"
echo "To run the backend: cd backend && uv run langgraph dev"
echo "To run the frontend: cd frontend && pnpm dev"
