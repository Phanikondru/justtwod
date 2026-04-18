"""FastMCP server exposing Adobe Photoshop control tools.

Launched by an MCP-capable AI client (Claude Desktop, Claude Code, Cursor,
etc.) and drives Photoshop by sending ExtendScript (.jsx) via macOS `osascript`.

Tools are organized under `justtwod.tools.*` — importing that package
registers every tool with the shared FastMCP instance via side effects.
"""
from __future__ import annotations

from ._app import mcp
from . import tools  # noqa: F401 — side-effect import registers every @mcp.tool()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
