# mypy: disable - error - code = "no-untyped-def,misc"
"""FastAPI application for the agent."""

import json
import pathlib
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent.mcp_config import load_mcp_settings
from agent.security import SecurityHeadersMiddleware
from agent.tools_and_schemas import MCP_TOOLS, get_tools_from_mcp
from config.app_config import config as app_config
from config.validation import check_env_strict


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI app.

    Handles startup validation and MCP tool loading.
    """
    # Startup validation
    if not check_env_strict():
        print("WARNING: Environment validation failed. Check logs for details.")

    # Load MCP Tools on startup
    mcp_settings = load_mcp_settings()
    if mcp_settings.enabled:
        print(f"INFO: Initializing MCP tools from {mcp_settings.endpoint}...")
        try:
            tools = await get_tools_from_mcp(mcp_settings)
            MCP_TOOLS.extend(tools)
            print(f"INFO: Successfully loaded {len(tools)} MCP tools.")
        except Exception as e:
            print(f"ERROR: Failed to load MCP tools during startup: {e}")

    yield

    # Cleanup if needed (e.g. close MCP sessions if we held them)
    # For now, langchain_mcp_adapters handles session lifecycle via tool context?
    # Actually, if load_mcp_tools establishes a persistent session, we should close it.
    # But get_tools_from_mcp returns list of tools.
    MCP_TOOLS.clear()


# Define the FastAPI app
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=app_config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/threads")
async def create_thread():
    """Create a new thread."""
    # Mock thread creation for frontend compatibility
    # The frontend SDK usually expects an ID or object back
    import uuid

    return {"thread_id": str(uuid.uuid4())}


# Import the graph to serve
try:
    from agent.graph import graph
except ImportError as e:
    print(f"ERROR: Failed to import graph. Agent endpoints will fail. {e}")
    graph = None


class InvokeRequest(BaseModel):
    """Request schema for invoking the agent."""

    input: dict[str, Any]
    config: dict[str, Any] | None = Field(default_factory=dict)


@app.get("/threads/{thread_id}/state")
async def get_thread_state(thread_id: str):
    """Get the state of a thread."""
    # Mock state for frontend compatibility
    return {
        "values": {},
        "next": [],
        "metadata": {},
        "config": {},
        "createdAt": "2024-01-01T00:00:00Z",
    }


@app.post("/threads/{thread_id}/runs/stream")
async def stream_run(thread_id: str, request: InvokeRequest):
    """Stream the run of a thread."""
    # Bridge frontend SDK calls to our simpler agent/stream endpoint logic
    # The frontend SDK sends input in a slightly different format sometimes
    if not graph:
        return Response("Graph not loaded", status_code=500)

    async def _stream_generator():
        try:
            # We map the thread_id to config thread_id if needed, but for now just run
            # Note: This ignores thread persistence for now as we don't have
            # checkpointer configured in this simple app.py setup (unless graph has it).
            config = request.config or {}
            config["configurable"] = config.get("configurable", {})
            config["configurable"]["thread_id"] = thread_id

            async for chunk in graph.astream(request.input, config):
                # LangGraph SDK expects specific event formats (event: ...)
                # But simple stream might just be data.
                # Let's try to mimic Server-Sent Events (SSE) format if possible
                # or just return lines if that's what the SDK handles.
                # Actually, the SDK uses POST for stream and expects bytes.

                # Standard LangGraph SDK format:
                # event: values\ndata: ...

                # We will send a simplified version.
                # If the frontend uses the standard Client, it handles various events.
                # "messages/partial", "values", etc.

                # For simplicity, let's dump the chunk as a "data" event
                data = json.dumps(chunk, default=str)
                yield f"event: metadata\ndata: {json.dumps({'run_id': 'run_123'})}\n\n"
                yield f"event: data\ndata: {data}\n\n"
        except Exception:
            import traceback

            traceback.print_exc()
            # Security: Don't leak exception details to client
            yield (
                f"event: error\n"
                f"data: {json.dumps({'message': 'Stream processing error'})}\n\n"
            )

        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(_stream_generator(), media_type="text/event-stream")


@app.post("/agent/invoke")
async def invoke_agent(request: InvokeRequest):
    """Invoke the agent synchronously."""
    if not graph:
        # Response is imported from fastapi at top of file
        return Response("Graph not loaded", status_code=500)

    # Simple adapter to expose graph.invoke
    # This allows using uvicorn instead of langgraph-cli
    try:
        result = await graph.invoke(request.input, request.config)
        return result
    except Exception:
        import traceback

        traceback.print_exc()
        # Security: Don't leak exception details to client
        return Response("Internal Server Error", status_code=500)


@app.post("/agent/stream")
async def stream_agent(request: InvokeRequest):
    """Stream the agent execution."""
    if not graph:
        return Response("Graph not loaded", status_code=500)

    async def _stream_generator():
        try:
            async for chunk in graph.astream(request.input, request.config):
                # LangGraph stream output needs to be serialized
                # Chunk is usually a dict of node updates
                # We yield it as JSON lines
                yield json.dumps(chunk, default=str) + "\n"
        except Exception:
            import traceback

            traceback.print_exc()
            # Security: Don't leak exception details to client
            yield json.dumps({"error": "Stream processing error"}) + "\n"

    return StreamingResponse(_stream_generator(), media_type="application/x-ndjson")


def create_frontend_router(build_dir="../frontend/dist"):
    """Creates a router to serve the React frontend.

    Args:
        build_dir: Path to the React build directory relative to this file.

    Returns:
        A Starlette application serving the frontend.
    """
    build_path = pathlib.Path(__file__).parent.parent.parent / build_dir

    if not build_path.is_dir() or not (build_path / "index.html").is_file():
        print(
            f"WARN: Frontend build directory not found or incomplete at {build_path}. "
            "Serving frontend will likely fail."
        )
        # Return a dummy router if build isn't ready
        from starlette.routing import Route

        async def dummy_frontend(request):
            return Response(
                "Frontend not built. Run 'npm run build' in the frontend directory.",
                media_type="text/plain",
                status_code=503,
            )

        return Route("/{path:path}", endpoint=dummy_frontend)

    return StaticFiles(directory=build_path, html=True)


# Mount the frontend under /app to not conflict with the LangGraph API routes
app.mount(
    "/app",
    create_frontend_router(),
    name="frontend",
)
