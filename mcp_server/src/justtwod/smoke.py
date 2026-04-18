"""Smoke test: verify the MCP server can reach Photoshop without an MCP client.

Run after install:

    uv run justtwod-ping

Expected output:

    [justtwod] Using Adobe Photoshop 2026
    [justtwod] pong from Adobe Photoshop 2026 26.x.x
    OK
"""
from __future__ import annotations

import sys

from . import tools  # noqa: F401 — ensure tools register (for a future richer smoke test)
from .transport import PHOTOSHOP_APP, PhotoshopError, run_jsx


def main() -> None:
    print(f"[justtwod] Using {PHOTOSHOP_APP}")
    try:
        resp = run_jsx(
            '_result = "pong from " + app.name + " " + app.version;',
            timeout=10.0,
        )
    except PhotoshopError as exc:
        print(f"[justtwod] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"[justtwod] {resp.get('result')}")
    print("OK")


if __name__ == "__main__":
    main()
