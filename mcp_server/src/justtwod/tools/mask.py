"""Mask tools: add/apply/delete layer masks, and create/release clipping masks."""
from __future__ import annotations

from typing import Literal

from .._app import mcp
from ..transport import run_jsx
from ._jsx_helpers import FIND_LAYER_BY_NAME, REQUIRE_ACTIVE_DOC, js_string

MaskFrom = Literal["reveal_all", "hide_all", "reveal_selection", "hide_selection"]

_MASK_MODE = {
    "reveal_all":       'charIDToTypeID("RvlA")',
    "hide_all":         'charIDToTypeID("HdAl")',
    "reveal_selection": 'charIDToTypeID("RvlS")',
    "hide_selection":   'charIDToTypeID("HdSl")',
}


@mcp.tool()
def add_layer_mask(name: str, mode: MaskFrom = "reveal_all") -> str:
    """Add a layer mask to the named layer.

    Modes:
    - `reveal_all` (default): white mask, layer fully visible
    - `hide_all`: black mask, layer fully hidden
    - `reveal_selection`: mask built from the current selection (selection = visible)
    - `hide_selection`: mask built from the inverse of the current selection
    """
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    doc.activeLayer = l;
    var desc = new ActionDescriptor();
    desc.putClass(charIDToTypeID("Nw  "), charIDToTypeID("Chnl"));
    var ref = new ActionReference();
    ref.putEnumerated(charIDToTypeID("Chnl"), charIDToTypeID("Chnl"), charIDToTypeID("Msk "));
    desc.putReference(charIDToTypeID("At  "), ref);
    desc.putEnumerated(charIDToTypeID("Usng"), charIDToTypeID("UsrM"), {_MASK_MODE[mode]});
    executeAction(charIDToTypeID("Mk  "), desc, DialogModes.NO);
    _result = l.name;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def apply_mask(name: str) -> str:
    """Apply the layer mask to the layer and remove the mask. The mask's effect
    is baked permanently into the layer's pixels.
    """
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    doc.activeLayer = l;
    var desc = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putEnumerated(charIDToTypeID("Chnl"), charIDToTypeID("Chnl"), charIDToTypeID("Msk "));
    desc.putReference(charIDToTypeID("null"), ref);
    desc.putBoolean(charIDToTypeID("Aply"), true);
    executeAction(charIDToTypeID("Dlt "), desc, DialogModes.NO);
    _result = l.name;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def delete_mask(name: str) -> str:
    """Remove the layer's mask without applying it. The layer's pixels are unchanged."""
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    doc.activeLayer = l;
    var desc = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putEnumerated(charIDToTypeID("Chnl"), charIDToTypeID("Chnl"), charIDToTypeID("Msk "));
    desc.putReference(charIDToTypeID("null"), ref);
    desc.putBoolean(charIDToTypeID("Aply"), false);
    executeAction(charIDToTypeID("Dlt "), desc, DialogModes.NO);
    _result = l.name;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def create_clipping_mask(name: str) -> str:
    """Clip the named layer to the layer directly beneath it (Cmd/Ctrl-Opt-G).
    The clipped layer's visible area is limited to the base layer's opaque area.
    """
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    if (l.typename !== "ArtLayer") throw new Error("Clipping masks only apply to art layers.");
    doc.activeLayer = l;
    l.grouped = true;
    _result = l.name;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def release_clipping_mask(name: str) -> str:
    """Release the clipping relationship so the layer is no longer clipped."""
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    if (l.typename !== "ArtLayer") throw new Error("Clipping masks only apply to art layers.");
    doc.activeLayer = l;
    l.grouped = false;
    _result = l.name;
    """
    return run_jsx(code)["result"]
