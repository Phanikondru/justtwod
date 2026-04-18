"""Core tools: transport health and the JSX escape hatch."""
from __future__ import annotations

from .._app import mcp
from ..transport import PhotoshopError, run_jsx


@mcp.tool()
def ping() -> str:
    """Check that Adobe Photoshop is running and reachable from this MCP server.

    Returns a short identification string like "pong from Adobe Photoshop 27.5.0".
    """
    try:
        resp = run_jsx('_result = "pong from " + app.name + " " + app.version;')
    except PhotoshopError as exc:
        raise RuntimeError(str(exc)) from exc
    return resp.get("result", "ok")


@mcp.tool()
def execute_jsx(code: str) -> dict:
    """Run arbitrary ExtendScript inside Photoshop. **Danger mode.**

    The code runs with Photoshop's full DOM in scope (`app`, `activeDocument`,
    `ActionDescriptor`, etc.). A script that sets a top-level `_result`
    variable will surface that value in the response.

    Use this for operations not yet covered by curated tools. For anything
    you'll want to reproduce, ask to have it wrapped as a proper tool instead.
    """
    return run_jsx(code)
