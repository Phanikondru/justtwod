"""Run ExtendScript inside Adobe Photoshop via macOS `osascript`.

This transport writes the JSX to a temp file, tells Photoshop to run it, and
parses a JSON line the script prints as its final output. Every JSX snippet
this module runs is wrapped so exceptions bubble back as structured errors
instead of silent no-ops.

Photoshop app name is auto-detected by scanning `/Applications` for the
newest `Adobe Photoshop <year>.app`. Override with the `JUSTTWOD_PHOTOSHOP_APP`
environment variable if you have a non-standard install.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

RESULT_SENTINEL = "__JUSTTWOD_RESULT__"

_APPLICATIONS = Path("/Applications")
_APP_NAME_RE = re.compile(r"^Adobe Photoshop (\d{4})\.app$")


def _detect_photoshop_app() -> str:
    override = os.environ.get("JUSTTWOD_PHOTOSHOP_APP")
    if override:
        return override
    candidates: list[tuple[int, str]] = []
    try:
        for entry in _APPLICATIONS.iterdir():
            match = _APP_NAME_RE.match(entry.name)
            if match:
                candidates.append((int(match.group(1)), entry.stem))
    except OSError:
        pass
    if not candidates:
        return "Adobe Photoshop 2026"
    candidates.sort(reverse=True)
    return candidates[0][1]


PHOTOSHOP_APP = _detect_photoshop_app()


class PhotoshopError(RuntimeError):
    """Raised when Photoshop isn't running, the JSX fails, or parsing fails."""


_JSON_POLYFILL = r"""
var __jt_stringify = function (v) {
    if (v === null || v === undefined) return "null";
    var t = typeof v;
    if (t === "boolean") return v ? "true" : "false";
    if (t === "number") return isFinite(v) ? String(v) : "null";
    if (t === "string") {
        var s = "\"";
        for (var i = 0; i < v.length; i++) {
            var c = v.charCodeAt(i);
            var ch = v.charAt(i);
            if (ch === "\"") s += "\\\"";
            else if (ch === "\\") s += "\\\\";
            else if (ch === "\n") s += "\\n";
            else if (ch === "\r") s += "\\r";
            else if (ch === "\t") s += "\\t";
            else if (c < 32) {
                var hex = c.toString(16);
                while (hex.length < 4) hex = "0" + hex;
                s += "\\u" + hex;
            }
            else s += ch;
        }
        return s + "\"";
    }
    if (v instanceof Array) {
        var a = [];
        for (var j = 0; j < v.length; j++) a.push(__jt_stringify(v[j]));
        return "[" + a.join(",") + "]";
    }
    if (t === "object") {
        var p = [];
        for (var k in v) {
            if (v.hasOwnProperty(k)) p.push(__jt_stringify(k) + ":" + __jt_stringify(v[k]));
        }
        return "{" + p.join(",") + "}";
    }
    return "null";
};
"""


def _wrap(jsx_body: str) -> str:
    """Wrap user JSX so its final expression value is a JSON envelope.

    ExtendScript lacks a native JSON object, so a minimal `__jt_stringify`
    polyfill is embedded. Photoshop's `do javascript` returns the script's
    final expression value to stdout, so the wrapper ends with that call
    as the trailing expression (no trailing semicolon).
    """
    return f"""(function () {{
    {_JSON_POLYFILL}
    var _result;
    try {{
        {jsx_body}
    }} catch (e) {{
        return "{RESULT_SENTINEL}" + __jt_stringify({{
            ok: false,
            error: (e && e.message) ? e.message : String(e),
            line: (e && e.line) ? e.line : null
        }});
    }}
    return "{RESULT_SENTINEL}" + __jt_stringify({{
        ok: true,
        result: (typeof _result === "undefined") ? null : _result
    }});
}})()"""


def run_jsx(jsx_body: str, timeout: float = 60.0) -> dict:
    """Execute an ExtendScript snippet in Photoshop.

    The snippet may set a top-level `_result` variable; its value is returned
    in the `result` key of the response. Raises PhotoshopError on failure.
    """
    wrapped = _wrap(jsx_body)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsx", delete=False, encoding="utf-8"
    ) as f:
        f.write(wrapped)
        jsx_path = Path(f.name)

    try:
        applescript = (
            f'set jsxContent to read POSIX file "{jsx_path}" as «class utf8»\n'
            f'tell application "{PHOTOSHOP_APP}" to do javascript jsxContent'
        )
        try:
            proc = subprocess.run(
                ["osascript", "-e", applescript],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise PhotoshopError(
                f"Photoshop did not respond within {timeout}s. "
                "Check that Photoshop is running and not blocked by a modal dialog."
            ) from exc

        if proc.returncode != 0:
            stderr = proc.stderr.strip() or proc.stdout.strip()
            if "Application isn't running" in stderr or "-600" in stderr:
                raise PhotoshopError(
                    f"{PHOTOSHOP_APP} is not running. Open Photoshop and try again."
                )
            raise PhotoshopError(f"osascript failed: {stderr}")

        stdout = proc.stdout
        for line in stdout.splitlines():
            if RESULT_SENTINEL in line:
                payload = line.split(RESULT_SENTINEL, 1)[1].strip()
                try:
                    parsed = json.loads(payload)
                except json.JSONDecodeError as exc:
                    raise PhotoshopError(
                        f"Invalid JSON from JSX: {payload!r}"
                    ) from exc
                if not parsed.get("ok"):
                    raise PhotoshopError(parsed.get("error", "Unknown JSX error"))
                return parsed

        raise PhotoshopError(
            "JSX returned no result sentinel. "
            f"stdout: {stdout!r} stderr: {proc.stderr!r}"
        )
    finally:
        try:
            jsx_path.unlink()
        except OSError:
            pass
