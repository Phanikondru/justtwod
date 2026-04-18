"""Selection tools: marquees, modify (feather/expand/contract/invert), and
loading selections from a layer's transparency.
"""
from __future__ import annotations

from .._app import mcp
from ..transport import run_jsx
from ._jsx_helpers import FIND_LAYER_BY_NAME, REQUIRE_ACTIVE_DOC, js_string


@mcp.tool()
def select_all() -> str:
    """Select the entire canvas."""
    code = REQUIRE_ACTIVE_DOC + """
    doc.selection.selectAll();
    _result = "selected all";
    """
    return run_jsx(code)["result"]


@mcp.tool()
def deselect() -> str:
    """Clear the current selection."""
    code = REQUIRE_ACTIVE_DOC + """
    try { doc.selection.deselect(); } catch (e) {}
    _result = "deselected";
    """
    return run_jsx(code)["result"]


@mcp.tool()
def select_rectangle(x: float, y: float, width: float, height: float) -> dict:
    """Create a rectangular marquee selection at (x, y) of the given size."""
    code = REQUIRE_ACTIVE_DOC + f"""
    doc.selection.select([
        [{x}, {y}],
        [{x + width}, {y}],
        [{x + width}, {y + height}],
        [{x}, {y + height}]
    ], SelectionType.REPLACE, 0, false);
    _result = {{ x: {x}, y: {y}, width: {width}, height: {height} }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def select_ellipse(x: float, y: float, width: float, height: float) -> dict:
    """Create an elliptical marquee selection inscribed in the given box."""
    code = REQUIRE_ACTIVE_DOC + f"""
    var desc = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putProperty(charIDToTypeID("Chnl"), charIDToTypeID("fsel"));
    desc.putReference(charIDToTypeID("null"), ref);
    var region = new ActionDescriptor();
    region.putUnitDouble(charIDToTypeID("Top "), charIDToTypeID("#Pxl"), {y});
    region.putUnitDouble(charIDToTypeID("Left"), charIDToTypeID("#Pxl"), {x});
    region.putUnitDouble(charIDToTypeID("Btom"), charIDToTypeID("#Pxl"), {y + height});
    region.putUnitDouble(charIDToTypeID("Rght"), charIDToTypeID("#Pxl"), {x + width});
    desc.putObject(charIDToTypeID("T   "), charIDToTypeID("Elps"), region);
    desc.putBoolean(charIDToTypeID("AntA"), true);
    executeAction(charIDToTypeID("setd"), desc, DialogModes.NO);
    _result = {{ x: {x}, y: {y}, width: {width}, height: {height} }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def invert_selection() -> str:
    """Invert the current selection."""
    code = REQUIRE_ACTIVE_DOC + """
    doc.selection.invert();
    _result = "inverted";
    """
    return run_jsx(code)["result"]


@mcp.tool()
def feather_selection(radius: float) -> float:
    """Feather (soften) the current selection by `radius` pixels."""
    code = REQUIRE_ACTIVE_DOC + f"""
    doc.selection.feather({radius});
    _result = {radius};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def expand_selection(pixels: float) -> float:
    """Expand (grow) the current selection outward by `pixels`."""
    code = REQUIRE_ACTIVE_DOC + f"""
    doc.selection.expand({pixels});
    _result = {pixels};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def contract_selection(pixels: float) -> float:
    """Contract (shrink) the current selection inward by `pixels`."""
    code = REQUIRE_ACTIVE_DOC + f"""
    doc.selection.contract({pixels});
    _result = {pixels};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def load_selection_from_layer(name: str) -> str:
    """Load a selection from the named layer's transparency (equivalent to
    Cmd/Ctrl-clicking the layer thumbnail in the Layers panel).
    """
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    var desc = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putProperty(charIDToTypeID("Chnl"), charIDToTypeID("fsel"));
    desc.putReference(charIDToTypeID("null"), ref);
    var src = new ActionReference();
    src.putEnumerated(charIDToTypeID("Chnl"), charIDToTypeID("Chnl"), charIDToTypeID("Trsp"));
    src.putIdentifier(charIDToTypeID("Lyr "), l.id);
    desc.putReference(charIDToTypeID("T   "), src);
    executeAction(charIDToTypeID("setd"), desc, DialogModes.NO);
    _result = l.name;
    """
    return run_jsx(code)["result"]
