"""Shape tools: create solid-colored rectangles, rounded rectangles, and
ellipses as raster layers. Vector shape layers (with editable paths and
strokes) are planned for a later phase.
"""
from __future__ import annotations

import re

from .._app import mcp
from ..transport import run_jsx
from ._jsx_helpers import FIND_LAYER_BY_NAME, REQUIRE_ACTIVE_DOC, js_string


def _clean_hex(color: str) -> str:
    c = color.lstrip("#").strip().upper()
    if not re.fullmatch(r"[0-9A-F]{6}", c):
        raise ValueError(f"color must be a 6-char hex string (got {color!r})")
    return c


def _color_setup_js(hex_color: str) -> str:
    return f"""
    var _fill = new SolidColor();
    _fill.rgb.hexValue = {js_string(hex_color)};
    """


@mcp.tool()
def create_rectangle(
    x: float,
    y: float,
    width: float,
    height: float,
    color: str = "#000000",
    name: str = "Rectangle",
) -> dict:
    """Create a new layer with a filled rectangle at (x, y) of the given size.
    Coordinates are in pixels from the top-left corner of the canvas.
    """
    hex_color = _clean_hex(color)
    code = REQUIRE_ACTIVE_DOC + _color_setup_js(hex_color) + f"""
    var l = doc.artLayers.add();
    l.name = {js_string(name)};
    doc.activeLayer = l;
    doc.selection.select([
        [{x}, {y}],
        [{x + width}, {y}],
        [{x + width}, {y + height}],
        [{x}, {y + height}]
    ], SelectionType.REPLACE, 0, false);
    doc.selection.fill(_fill);
    doc.selection.deselect();
    _result = {{ id: l.id, name: l.name }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def create_rounded_rectangle(
    x: float,
    y: float,
    width: float,
    height: float,
    radius: float,
    color: str = "#000000",
    name: str = "Rounded Rectangle",
) -> dict:
    """Create a new layer with a filled rounded rectangle. `radius` is the
    corner radius in pixels. Approximated via four corner squares + two cross
    bars + four corner ellipses, all filled in one stroke.
    """
    hex_color = _clean_hex(color)
    r = min(radius, width / 2, height / 2)
    code = REQUIRE_ACTIVE_DOC + _color_setup_js(hex_color) + f"""
    var l = doc.artLayers.add();
    l.name = {js_string(name)};
    doc.activeLayer = l;

    function fillRect(x1, y1, x2, y2) {{
        doc.selection.select([
            [x1, y1], [x2, y1], [x2, y2], [x1, y2]
        ], SelectionType.REPLACE, 0, false);
        doc.selection.fill(_fill);
    }}
    function fillEllipse(cx, cy, rad) {{
        doc.selection.select([
            [cx - rad, cy - rad],
            [cx + rad, cy - rad],
            [cx + rad, cy + rad],
            [cx - rad, cy + rad]
        ], SelectionType.REPLACE, 0, false);
        // Switch to elliptical via the marquee action
        doc.selection.deselect();
        var ovalBounds = [
            [cx - rad, cy - rad],
            [cx + rad, cy + rad]
        ];
        var idx = 0;
        var desc = new ActionDescriptor();
        var ref = new ActionReference();
        ref.putProperty(charIDToTypeID("Chnl"), charIDToTypeID("fsel"));
        desc.putReference(charIDToTypeID("null"), ref);
        var region = new ActionDescriptor();
        region.putUnitDouble(charIDToTypeID("Top "), charIDToTypeID("#Pxl"), cy - rad);
        region.putUnitDouble(charIDToTypeID("Left"), charIDToTypeID("#Pxl"), cx - rad);
        region.putUnitDouble(charIDToTypeID("Btom"), charIDToTypeID("#Pxl"), cy + rad);
        region.putUnitDouble(charIDToTypeID("Rght"), charIDToTypeID("#Pxl"), cx + rad);
        desc.putObject(charIDToTypeID("T   "), charIDToTypeID("Elps"), region);
        desc.putBoolean(charIDToTypeID("AntA"), true);
        executeAction(charIDToTypeID("setd"), desc, DialogModes.NO);
        doc.selection.fill(_fill);
    }}

    var r = {r};
    // Center bars
    fillRect({x + r}, {y}, {x + width - r}, {y + height});
    fillRect({x}, {y + r}, {x + width}, {y + height - r});
    // Four rounded corners (full ellipses at each corner center)
    fillEllipse({x + r}, {y + r}, r);
    fillEllipse({x + width - r}, {y + r}, r);
    fillEllipse({x + width - r}, {y + height - r}, r);
    fillEllipse({x + r}, {y + height - r}, r);
    doc.selection.deselect();
    _result = {{ id: l.id, name: l.name }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def create_ellipse(
    x: float,
    y: float,
    width: float,
    height: float,
    color: str = "#000000",
    name: str = "Ellipse",
) -> dict:
    """Create a new layer with a filled ellipse inscribed in the given bounding box."""
    hex_color = _clean_hex(color)
    code = REQUIRE_ACTIVE_DOC + _color_setup_js(hex_color) + f"""
    var l = doc.artLayers.add();
    l.name = {js_string(name)};
    doc.activeLayer = l;
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
    doc.selection.fill(_fill);
    doc.selection.deselect();
    _result = {{ id: l.id, name: l.name }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def fill_layer_with_color(name: str, color: str) -> str:
    """Fill the entire named layer with a solid color. Useful for backgrounds."""
    hex_color = _clean_hex(color)
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + _color_setup_js(hex_color) + f"""
    var l = requireLayer({js_string(name)});
    doc.activeLayer = l;
    doc.selection.selectAll();
    doc.selection.fill(_fill);
    doc.selection.deselect();
    _result = l.name;
    """
    return run_jsx(code)["result"]
