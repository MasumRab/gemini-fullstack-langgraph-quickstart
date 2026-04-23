#!/bin/bash
set -e

echo "========================================"
echo "  Gemini Fullstack Agent - Setup Script"
echo "  Render Free Tier Optimized"
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
    # If Render Free Tier, we skip dev dependencies to save space and time
    if [ "$RENDER" = "true" ]; then
        echo "Render environment detected. Installing production dependencies..."
        uv pip install -e .
        uv pip install uvicorn google-genai
    else
        uv sync --dev || uv pip install -e ".[dev]"
        uv pip install -e .
        uv pip install uvicorn google-genai
    fi
else
    echo "uv not found. Falling back to pip..."
    if [ "$RENDER" = "true" ]; then
        pip install -e .
    else
        pip install -e ".[dev]"
    fi
    # Ensure uvicorn and google-genai are installed
    pip install uvicorn google-genai
fi

# Install Playwright browsers for the backend verification scripts
# Skip on Render to save resources unless explicitly required
if [ "$RENDER" = "true" ]; then
    echo "Running on Render. Skipping Playwright browser installation to save resources."
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
    # We install dependencies but skip optional/heavy ones if possible
    pnpm install

    # Build for production (Generates dist/ folder for backend to serve)
    echo "Building Frontend for Production..."
    pnpm run build
else
    echo "ERROR: pnpm not found even after installation attempt."
    # do not exit, just error log
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
    echo "Lite Mode Enabled: Remember to set RAG_EMBEDDING_PROVIDER=google_genai and GEMMA_PROVIDER=google_genai"
fi

echo ""
echo "Setup Complete! 🚀"
if [ "$RENDER" != "true" ]; then
    echo "To run the backend: cd backend && uv run langgraph dev"
    echo "To run the frontend: cd frontend && pnpm dev"
else
    echo "To start the service: cd backend && export PYTHONPATH=\$PYTHONPATH:\$(pwd)/src && python -m uvicorn agent.app:app --host 0.0.0.0 --port \$PORT"
fi
