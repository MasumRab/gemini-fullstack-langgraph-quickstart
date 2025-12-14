# mypy: disable - error - code = "no-untyped-def,misc"
import pathlib
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from backend.src.config.validation import check_env_strict

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup validation
    if not check_env_strict():
        print("WARNING: Environment validation failed. Check logs for details.")
    yield
    # Shutdown logic if any

from agent.mcp_config import load_mcp_settings
from agent.tools_and_schemas import get_tools_from_mcp, MCP_TOOLS

@asynccontextmanager
async def lifespan(app: FastAPI):
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
