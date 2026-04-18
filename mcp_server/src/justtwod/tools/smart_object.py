"""Smart object tools: place external files as smart objects, convert
existing layers, replace contents (the "swap in your design" flow), edit
contents, reset transforms.
"""
from __future__ import annotations

from pathlib import Path

from .._app import mcp
from ..transport import run_jsx
from ._jsx_helpers import FIND_LAYER_BY_NAME, REQUIRE_ACTIVE_DOC, js_string


@mcp.tool()
def place_as_smart_object(path: str, name: str | None = None) -> dict:
    """Place an external file (PNG, JPG, PSD, AI, etc.) into the active
    document as a new smart-object layer. The layer is fit to the canvas
    and becomes the active layer.
    """
    abs_path = str(Path(path).expanduser().resolve())
    rename_code = (
        f"doc.activeLayer.name = {js_string(name)};" if name else ""
    )
    code = REQUIRE_ACTIVE_DOC + f"""
    var f = new File({js_string(abs_path)});
    if (!f.exists) throw new Error("File not found: " + f.fsName);
    var desc = new ActionDescriptor();
    desc.putPath(charIDToTypeID("null"), f);
    desc.putEnumerated(charIDToTypeID("FTcs"), charIDToTypeID("QCSt"), charIDToTypeID("Qcsa"));
    executeAction(charIDToTypeID("Plc "), desc, DialogModes.NO);
    {rename_code}
    var l = doc.activeLayer;
    _result = {{ id: l.id, name: l.name, kind: String(l.kind) }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def create_smart_object(name: str) -> dict:
    """Convert the named layer into a smart object. Returns the converted layer info."""
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    doc.activeLayer = l;
    executeAction(stringIDToTypeID("newPlacedLayer"), undefined, DialogModes.NO);
    var converted = doc.activeLayer;
    _result = {{ id: converted.id, name: converted.name, kind: String(converted.kind) }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def replace_contents(name: str, path: str) -> dict:
    """Replace the contents of a smart-object layer with the file at `path`.
    This is the core "swap in your design" operation — the smart object keeps
    its transforms, filters, and position; only the source is swapped.
    """
    abs_path = str(Path(path).expanduser().resolve())
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    doc.activeLayer = l;
    var f = new File({js_string(abs_path)});
    if (!f.exists) throw new Error("File not found: " + f.fsName);
    var desc = new ActionDescriptor();
    desc.putPath(charIDToTypeID("null"), f);
    desc.putInteger(charIDToTypeID("PgNm"), 1);
    executeAction(stringIDToTypeID("placedLayerReplaceContents"), desc, DialogModes.NO);
    var updated = doc.activeLayer;
    _result = {{ id: updated.id, name: updated.name, source: f.fsName }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def edit_contents(name: str) -> str:
    """Open the contents of a smart-object layer as a separate document for editing.
    The new document becomes active; save-and-close it to propagate changes back.
    """
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    doc.activeLayer = l;
    executeAction(stringIDToTypeID("placedLayerEditContents"), undefined, DialogModes.NO);
    _result = app.activeDocument.name;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def reset_smart_object_transforms(name: str) -> str:
    """Reset any transforms (scale, rotation, skew) applied to a smart-object
    layer, restoring it to its original size and orientation.
    """
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    doc.activeLayer = l;
    executeAction(stringIDToTypeID("placedLayerResetTransforms"), undefined, DialogModes.NO);
    _result = l.name;
    """
    return run_jsx(code)["result"]
