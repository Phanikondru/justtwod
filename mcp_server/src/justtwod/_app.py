"""Shared FastMCP instance. Imported by every tool module so all @mcp.tool()
decorators register onto the same server.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("justtwod")
