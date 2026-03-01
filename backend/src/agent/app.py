# mypy: disable - error - code = "no-untyped-def,misc"
"""FastAPI application for the agent."""

import json
import logging
import pathlib
import traceback
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware

from agent.mcp_config import load_mcp_settings
from agent.security import RateLimitMiddleware, SecurityHeadersMiddleware
from agent.tools_and_schemas import MCP_TOOLS, get_tools_from_mcp
from config.app_config import config as app_config
from config.validation import check_env_strict

logger = logging.getLogger(__name__)


# Define Middleware for Content Size Limit (Defense against DoS)
class ContentSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit the size of the request body."""

    def __init__(self, app, max_upload_size: int = 10 * 1024 * 1024):  # 10MB
        """Initialize the middleware."""
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next):
        """Process the request and enforce size limits."""
        if request.method in ("POST", "PUT", "PATCH"):
            # 🛡️ Sentinel: Reject 'Transfer-Encoding: chunked' to prevent Content-Length bypass (Request Smuggling/DoS)
            transfer_encoding = request.headers.get("transfer-encoding", "").lower()
            if "chunked" in transfer_encoding:
                logger.warning("Request blocked: Chunked encoding not allowed")
                return Response("Chunked encoding not allowed", status_code=411)

            content_length = request.headers.get("content-length")
            if not content_length:
                # 🛡️ Sentinel: Enforce Content-Length for state-changing methods to prevent streaming DoS
                logger.warning("Request blocked: Content-Length required")
                return Response("Content-Length required", status_code=411)

            try:
                # 🛡️ Sentinel: Prevent 500 crashes from malformed Content-Length headers
                if int(content_length) > self.max_upload_size:
                    logger.warning(
                        f"Request blocked: Request entity too large ({content_length} > {self.max_upload_size})"
                    )
                    return Response("Request entity too large", status_code=413)
            except ValueError:
                logger.warning("Request blocked: Invalid Content-Length")
                return Response("Invalid Content-Length", status_code=400)
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage the application's lifespan, performing startup validation, optional MCP tool loading, and teardown cleanup.
    
    On startup, validates the runtime environment and logs a warning if validation fails. If MCP settings indicate tools are enabled, attempts to load tools from the configured MCP endpoint, appending them to the module-level MCP_TOOLS list and logging success or failure. On shutdown, clears MCP_TOOLS.
    """
    # Startup validation
    if not check_env_strict():
        logger.warning(
            "WARNING: Environment validation failed. Check logs for details."
        )

    # Load MCP Tools on startup
    mcp_settings = load_mcp_settings()
    if mcp_settings.enabled:
        logger.info(f"INFO: Initializing MCP tools from {mcp_settings.endpoint}...")
        try:
            tools = await get_tools_from_mcp(mcp_settings)
            MCP_TOOLS.extend(tools)
            logger.info(f"INFO: Successfully loaded {len(tools)} MCP tools.")
        except Exception as e:
            logger.error(f"ERROR: Failed to load MCP tools during startup: {e}")

    yield

    # Cleanup if needed (e.g. close MCP sessions if we held them)
    # For now, langchain_mcp_adapters handles session lifecycle via tool context?
    # Actually, if load_mcp_tools establishes a persistent session, we should close it.
    # But get_tools_from_mcp returns list of tools.
    MCP_TOOLS.clear()


# Define the FastAPI app
app = FastAPI(lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Overridden handler to prevent RecursionError when serializing deeply nested invalid inputs.

    Standard FastAPI handler crashes on deep JSON because it tries to echo the input.
    """
    # We construct a simplified error list that doesn't include the full 'input' if it's huge
    errors = []
    for error in exc.errors():
        # Copy error dict but remove 'input' or 'ctx' if they might be huge
        # Pydantic v2 puts input in 'input' key.
        safe_error = error.copy()
        if "input" in safe_error:
            del safe_error["input"]
        if "ctx" in safe_error:
            # ctx might contain the exception which might contain the object
            # For ValueError, it's usually safe, but let's be careful.
            # We can convert ctx to str or just remove it if needed.
            # Usually ctx for ValueError is just the exception object.
            safe_error["ctx"] = str(safe_error["ctx"])
        errors.append(safe_error)

    return JSONResponse(
        status_code=422,
        content={"detail": errors},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=app_config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Trusted Host Middleware (Guard against Host Header attacks)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=app_config.allowed_hosts)

# Add Content Size Limit Middleware (Guard against DoS)
app.add_middleware(ContentSizeLimitMiddleware, max_upload_size=10 * 1024 * 1024)

# Add Rate Limiting (INNER - added before SecurityHeaders)
# Limit to 100 requests per minute per IP for sensitive API endpoints
app.add_middleware(
    RateLimitMiddleware,
    limit=100,
    window=60,
    protected_paths=["/agent", "/threads"],
    trust_proxy_headers=app_config.trust_proxy_headers,
)

# Add Security Headers (OUTERMOST - added last)
# This ensures even 429 responses from RateLimiter (inner) get headers.
# Re-verified: Starlette .add_middleware() uses .insert(0), so LAST added is OUTERMOST.
app.add_middleware(SecurityHeadersMiddleware)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/threads")
async def create_thread():
    """
    Create a new thread and return its identifier for frontend compatibility.
    
    Returns:
        thread (dict): Dictionary containing `thread_id` (str), a newly generated UUID string.
    """
    # Mock thread creation for frontend compatibility
    # The frontend SDK usually expects an ID or object back
    return {"thread_id": str(uuid.uuid4())}


# Import the graph to serve
try:
    from agent.graph import graph
except ImportError as e:
    logger.error(f"ERROR: Failed to import graph. Agent endpoints will fail. {e}")
    graph = None


class InvokeRequest(BaseModel):
    """Request schema for invoking the agent."""

    input: dict[str, Any]
    config: dict[str, Any] | None = Field(default_factory=dict)

    @field_validator("input")
    def validate_input_complexity(cls, v):
        """🛡️ Sentinel: Validate input complexity to prevent Denial of Service (DoS).

        Checks:
        1. Max String Length: 50,000 chars (prevents huge blobs)
        2. Max Total Size: 200,000 chars (prevents memory exhaustion)
        3. Max Nesting Depth: 50 (prevents RecursionError crashes)
        4. Max Item Count: 1000 (prevents CPU exhaustion in iteration)
        """
        MAX_INPUT_LENGTH = 50000
        MAX_TOTAL_CHARS = 200000
        MAX_DEPTH = 50
        MAX_ITEMS = 1000

        stats = {"chars": 0, "items": 0}

        def check_complexity(obj, depth):
            """
            Validate a nested input structure against configured depth, string length, total characters, and item count limits.
            
            Recursively inspects strings, lists, and dicts starting from `obj`, updating shared `stats` and raising a ValueError when any configured limit is exceeded (maximum depth, per-string length, total characters, or total item count). Designed to be called with an initial `depth` (typically 0) and relies on the surrounding scope for `MAX_DEPTH`, `MAX_INPUT_LENGTH`, `MAX_TOTAL_CHARS`, `MAX_ITEMS`, and the `stats` dictionary.
            
            Parameters:
                obj: The current value to validate (string, list, dict, or other JSON-serializable types).
                depth (int): Current nesting depth for `obj`; incremented for nested keys/values and elements.
            
            Raises:
                ValueError: If nesting exceeds `MAX_DEPTH`, a string exceeds `MAX_INPUT_LENGTH`, total characters exceed `MAX_TOTAL_CHARS`, or total items exceed `MAX_ITEMS`.
            """
            if depth > MAX_DEPTH:
                raise ValueError(f"Input too deeply nested (limit: {MAX_DEPTH})")

            if isinstance(obj, str):
                if len(obj) > MAX_INPUT_LENGTH:
                    raise ValueError(
                        f"Input string too long ({len(obj)} chars). Max allowed: {MAX_INPUT_LENGTH}"
                    )
                stats["chars"] += len(obj)
            elif isinstance(obj, dict):
                stats["items"] += len(obj)
                for key, value in obj.items():
                    # Keys also count towards depth and size
                    check_complexity(key, depth + 1)
                    check_complexity(value, depth + 1)
            elif isinstance(obj, list):
                stats["items"] += len(obj)
                for item in obj:
                    check_complexity(item, depth + 1)

            # Check limits at every step to fail fast
            if stats["chars"] > MAX_TOTAL_CHARS:
                raise ValueError(
                    f"Total input size too large ({stats['chars']} chars). Max allowed: {MAX_TOTAL_CHARS}"
                )
            if stats["items"] > MAX_ITEMS:
                raise ValueError(
                    f"Too many items in input ({stats['items']}). Max allowed: {MAX_ITEMS}"
                )

        check_complexity(v, 0)

        # 🛡️ Sentinel: Validate specific semantic configuration fields to prevent DoS
        if isinstance(v, dict):
            # Limit initial search query count
            if "initial_search_query_count" in v:
                try:
                    count = int(v["initial_search_query_count"])
                    if count > 10:
                        raise ValueError("initial_search_query_count cannot exceed 10")
                    if count < 1:
                        raise ValueError(
                            "initial_search_query_count must be at least 1"
                        )
                except ValueError as e:
                    if "cannot exceed" in str(e) or "must be at least" in str(e):
                        raise e
                    raise ValueError("initial_search_query_count must be an integer")

            # Limit max research loops
            if "max_research_loops" in v:
                try:
                    loops = int(v["max_research_loops"])
                    if loops > 10:
                        raise ValueError("max_research_loops cannot exceed 10")
                    if loops < 1:
                        raise ValueError("max_research_loops must be at least 1")
                except ValueError as e:
                    if "cannot exceed" in str(e) or "must be at least" in str(e):
                        raise e
                    raise ValueError("max_research_loops must be an integer")

        return v


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
    """
    Stream a thread run's events over Server-Sent Events (SSE).
    
    Parameters:
        request (InvokeRequest): Invocation payload containing `input` and optional `config`. The function will ensure `config` includes the provided `thread_id`.
    
    Returns:
        StreamingResponse: An SSE stream that emits a `metadata` event (run identifier), one or more `data` events with JSON-serialized chunks from the run, an `error` event with a generic message if processing fails, and a final `end` event.
    """
    # Bridge frontend SDK calls to our simpler agent/stream endpoint logic
    # The frontend SDK sends input in a slightly different format sometimes
    if not graph:
        return Response("Graph not loaded", status_code=500)

    async def _stream_generator():
        """
        Stream run events for a thread as Server-Sent Events (SSE)-style text chunks.
        
        Yields SSE-formatted strings representing run metadata and data chunks generated by the graph's async stream. On an internal error, yields a single generic `error` event (without exception details) and finally yields an `end` event.
        
        Returns:
            Async generator that yields UTF-8 text strings formatted as SSE events (e.g. "event: data\ndata: {...}\n\n").
        """
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
    """
    Invoke the agent with the provided input and configuration and return its result.
    
    Calls the global graph's `invoke` method with `request.input` and `request.config` and returns whatever the graph produces. If the graph is not loaded, returns an HTTP 500 Response with the body "Graph not loaded". If an exception occurs during invocation, returns an HTTP 500 Response with the body "Internal Server Error" (exception details are not exposed).
    
    Parameters:
        request (InvokeRequest): Contains `input` (the agent input payload) and optional `config` (invocation configuration).
    
    Returns:
        The value produced by the graph's `invoke` call on success, or a `fastapi.Response` with status_code=500 and a brief error message on failure.
    """
    if not graph:
        # Response is imported from fastapi at top of file
        return Response("Graph not loaded", status_code=500)

    # Simple adapter to expose graph.invoke
    # This allows using uvicorn instead of langgraph-cli
    try:
        result = await graph.invoke(request.input, request.config)
        return result
    except Exception:
        traceback.print_exc()
        # Security: Don't leak exception details to client
        return Response("Internal Server Error", status_code=500)


@app.post("/agent/stream")
async def stream_agent(request: InvokeRequest):
    """
    Stream agent execution results as NDJSON.
    
    Streams the agent's output from the internal graph as newline-delimited JSON objects. If the graph is not loaded, returns a 500 Response with message "Graph not loaded". If an error occurs while producing the stream, the stream yields a single NDJSON object: {"error": "Stream processing error"}.
    
    Parameters:
        request (InvokeRequest): Invocation payload containing `input` (a dict of agent input data) and optional `config` (agent configuration).
    
    Returns:
        StreamingResponse or Response: A StreamingResponse that emits NDJSON-encoded chunks representing agent output, or a 500 Response when the graph is not loaded.
    """
    if not graph:
        return Response("Graph not loaded", status_code=500)

    async def _stream_generator():
        """
        Produce newline-delimited JSON lines for each chunk emitted by the graph stream.
        
        Yields JSON-serialized representations of each chunk produced by graph.astream, one per line, suitable for NDJSON-style streaming. If an internal error occurs, yields a single JSON line containing {"error": "Stream processing error"}.
        
        Returns:
            str: A JSON string followed by a newline for each chunk (or the error object), e.g. '{"key": "value"}\n'.
        """
        try:
            async for chunk in graph.astream(request.input, request.config):
                # LangGraph stream output needs to be serialized
                # Chunk is usually a dict of node updates
                # We yield it as JSON lines
                yield json.dumps(chunk, default=str) + "\n"
        except Exception:
            traceback.print_exc()
            # Security: Don't leak exception details to client
            yield json.dumps({"error": "Stream processing error"}) + "\n"

    return StreamingResponse(_stream_generator(), media_type="application/x-ndjson")


def create_frontend_router(build_dir="../frontend/dist"):
    """Create a router to serve the React frontend.

    Args:
        build_dir: Path to the React build directory relative to this file.

    Returns:
        A Starlette application serving the frontend.
    """
    build_path = pathlib.Path(__file__).parent.parent.parent / build_dir

    if not build_path.is_dir() or not (build_path / "index.html").is_file():
        logger.warning(
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
