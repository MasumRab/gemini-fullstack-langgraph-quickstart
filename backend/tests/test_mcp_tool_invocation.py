from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.tools import StructuredTool

from agent.nodes import _exec_single_tool, _resolve_tool_result


async def _afetch(query: str) -> str:
    return f"async:{query}"


@pytest.fixture()
def async_tool() -> StructuredTool:
    """A tool shaped like one returned by ``load_mcp_tools()``.

    MCP tools wrap a coroutine, so ``StructuredTool.invoke()`` returns the
    coroutine object itself rather than its result.
    """
    return StructuredTool.from_function(
        func=_afetch, name="afetch", description="Fetch something asynchronously."
    )


def test_invoke_returns_an_unawaited_coroutine(async_tool):
    """Pin the LangChain behaviour the fix depends on."""
    raw = async_tool.invoke({"query": "x"})
    assert hasattr(raw, "__await__")

    # Close it so the test does not leak a "never awaited" warning.
    raw.close()


def test_resolve_awaits_the_coroutine(async_tool):
    raw = async_tool.invoke({"query": "x"})
    assert _resolve_tool_result(raw) == "async:x"


def test_resolve_passes_non_awaitables_through():
    assert _resolve_tool_result(["a", "b"]) == ["a", "b"]
    assert _resolve_tool_result("plain") == "plain"


def test_exec_single_tool_awaits_mcp_tools(async_tool):
    """End to end: the model gets the tool's result, not ``<coroutine object>``."""
    out = _exec_single_tool(
        {"name": "afetch", "args": {"query": "x"}}, {"afetch": async_tool}
    )
    assert out == "\nResult from afetch:\nasync:x\n"
    assert "coroutine object" not in out


def test_exec_single_tool_still_runs_sync_tools():
    tool = MagicMock()
    tool.invoke.return_value = "sync-ok"
    out = _exec_single_tool({"name": "t", "args": {}}, {"t": tool})
    assert out == "\nResult from t:\nsync-ok\n"


def test_exec_single_tool_reports_an_async_failure():
    tool = MagicMock()
    tool.invoke = MagicMock(return_value=AsyncMock(side_effect=RuntimeError("boom"))())
    out = _exec_single_tool({"name": "t", "args": {}}, {"t": tool})
    assert "Error executing t: boom" in out


def test_exec_single_tool_ignores_an_unknown_tool(async_tool):
    assert _exec_single_tool({"name": "nope", "args": {}}, {"afetch": async_tool}) == ""
