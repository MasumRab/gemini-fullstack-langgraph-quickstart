# mypy: disable - error - code = "no-untyped-def,misc"
import pathlib
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from backend.src.config.validation import check_env_strict
from agent.mcp_config import load_mcp_settings
from agent.tools_and_schemas import get_tools_from_mcp, MCP_TOOLS

@asynccontextmanager
async def lifespan(app: FastAPI):
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
    # For now, langchain_mcp_adapters handles session lifecycle via tool execution context?
    # Actually, if load_mcp_tools establishes a persistent session, we should close it here.
    # But get_tools_from_mcp returns list of tools.
    MCP_TOOLS.clear()


# Define the FastAPI app
app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Import the graph to serve
try:
    from agent.graph import graph
except ImportError as e:
    print(f"ERROR: Failed to import graph. Agent endpoints will fail. {e}")
    graph = None

from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

class InvokeRequest(BaseModel):
    input: Dict[str, Any]
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)

@app.post("/agent/invoke")
async def invoke_agent(request: InvokeRequest):
    if not graph:
        # Response is imported from fastapi at top of file
        return Response("Graph not loaded", status_code=500)

    # Simple adapter to expose graph.invoke
    # This allows using uvicorn instead of langgraph-cli
    try:
        result = await graph.invoke(request.input, request.config)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response(f"Execution Error: {str(e)}", status_code=500)

from fastapi.responses import StreamingResponse
import json

@app.post("/agent/stream")
async def stream_agent(request: InvokeRequest):
    if not graph:
         return Response("Graph not loaded", status_code=500)

    async def _stream_generator():
        try:
            async for chunk in graph.astream(request.input, request.config):
                # LangGraph stream output needs to be serialized
                # Chunk is usually a dict of node updates
                # We yield it as JSON lines
                yield json.dumps(chunk, default=str) + "\n"
        except Exception as e:
            yield json.dumps({"error": str(e)}) + "\n"

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
            f"WARN: Frontend build directory not found or incomplete at {build_path}. Serving frontend will likely fail."
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
