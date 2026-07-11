# Stage 1: Build Frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install --frozen-lockfile

COPY frontend/ ./
RUN pnpm run build

# Stage 2: Build Backend & Serve
FROM python:3.11-slim
WORKDIR /app/backend

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Install dependencies
COPY backend/pyproject.toml .
# Install uvicorn explicitly as it's the server
RUN pip install --no-cache-dir . uvicorn

# Copy backend code
COPY backend/ .

# Copy frontend build to locations expected by app.py
# app.py expects: ../frontend/dist
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Change ownership to the non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check probing the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Expose port 8000 (standard for langgraph-api)
EXPOSE 8000

# Run the LangGraph API server
# We use the python module execution to ensure it picks up the environment and config
CMD ["python", "-m", "langgraph_api.server"]
