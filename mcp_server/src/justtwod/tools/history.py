"""History tools: step through the active document's history stack."""
from __future__ import annotations

from .._app import mcp
from ..transport import run_jsx
from ._jsx_helpers import REQUIRE_ACTIVE_DOC

_FIND_CURRENT_INDEX = """
var states = doc.historyStates;
var currentIndex = -1;
for (var i = 0; i < states.length; i++) {
    if (states[i] === doc.activeHistoryState) { currentIndex = i; break; }
}
if (currentIndex === -1) throw new Error("Could not locate the active history state.");
"""


@mcp.tool()
def undo(steps: int = 1) -> dict:
    """Step backward through the active document's history (Cmd/Ctrl+Z).

    `steps` is clamped to the oldest available state, so asking for more steps
    than exist is safe — the return value reports how many were actually applied.
    """
    if steps < 1:
        raise ValueError("steps must be >= 1")
    code = REQUIRE_ACTIVE_DOC + _FIND_CURRENT_INDEX + f"""
    var requested = {int(steps)};
    var targetIndex = Math.max(0, currentIndex - requested);
    doc.activeHistoryState = states[targetIndex];
    _result = {{
        steps_applied: currentIndex - targetIndex,
        steps_requested: requested,
        current_state: doc.activeHistoryState.name,
        current_index: targetIndex,
        can_undo: targetIndex > 0,
        can_redo: targetIndex < states.length - 1
    }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def redo(steps: int = 1) -> dict:
    """Step forward through the active document's history (Cmd/Ctrl+Shift+Z).

    `steps` is clamped to the newest available state; the return value reports
    how many were actually applied.
    """
    if steps < 1:
        raise ValueError("steps must be >= 1")
    code = REQUIRE_ACTIVE_DOC + _FIND_CURRENT_INDEX + f"""
    var requested = {int(steps)};
    var targetIndex = Math.min(states.length - 1, currentIndex + requested);
    doc.activeHistoryState = states[targetIndex];
    _result = {{
        steps_applied: targetIndex - currentIndex,
        steps_requested: requested,
        current_state: doc.activeHistoryState.name,
        current_index: targetIndex,
        can_undo: targetIndex > 0,
        can_redo: targetIndex < states.length - 1
    }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def get_history_states() -> dict:
    """Return the active document's full history stack plus the current position.

    Useful for deciding how many `undo` or `redo` steps to take, or for jumping
    back to a named state via `execute_jsx`.
    """
    code = REQUIRE_ACTIVE_DOC + """
    var states = doc.historyStates;
    var out = [];
    var currentIndex = -1;
    for (var i = 0; i < states.length; i++) {
        var s = states[i];
        out.push({ name: s.name, snapshot: s.snapshot === true });
        if (s === doc.activeHistoryState) currentIndex = i;
    }
    _result = {
        total: out.length,
        current_index: currentIndex,
        current_state: currentIndex >= 0 ? out[currentIndex].name : null,
        can_undo: currentIndex > 0,
        can_redo: currentIndex >= 0 && currentIndex < out.length - 1,
        states: out
    };
    """
    return run_jsx(code)["result"]
