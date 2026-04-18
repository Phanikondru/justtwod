"""Transform tools: move, scale, rotate, and flip layers."""
from __future__ import annotations

from typing import Literal

from .._app import mcp
from ..transport import run_jsx
from ._jsx_helpers import FIND_LAYER_BY_NAME, REQUIRE_ACTIVE_DOC, js_string

Anchor = Literal[
    "top_left", "top_center", "top_right",
    "middle_left", "center", "middle_right",
    "bottom_left", "bottom_center", "bottom_right",
]

_ANCHOR_MAP = {
    "top_left":      "AnchorPosition.TOPLEFT",
    "top_center":    "AnchorPosition.TOPCENTER",
    "top_right":     "AnchorPosition.TOPRIGHT",
    "middle_left":   "AnchorPosition.MIDDLELEFT",
    "center":        "AnchorPosition.MIDDLECENTER",
    "middle_right":  "AnchorPosition.MIDDLERIGHT",
    "bottom_left":   "AnchorPosition.BOTTOMLEFT",
    "bottom_center": "AnchorPosition.BOTTOMCENTER",
    "bottom_right":  "AnchorPosition.BOTTOMRIGHT",
}

FlipDirection = Literal["horizontal", "vertical"]


@mcp.tool()
def move_layer(name: str, dx: float, dy: float) -> dict:
    """Translate the named layer by (dx, dy) pixels. Positive values move right/down."""
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    l.translate(new UnitValue({dx}, "px"), new UnitValue({dy}, "px"));
    _result = {{
        id: l.id,
        name: l.name,
        bounds: {{
            left:   l.bounds[0].value,
            top:    l.bounds[1].value,
            right:  l.bounds[2].value,
            bottom: l.bounds[3].value
        }}
    }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def move_layer_to(name: str, x: float, y: float) -> dict:
    """Move the named layer so its top-left bound is at (x, y) in canvas pixels."""
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    var curLeft = l.bounds[0].value;
    var curTop = l.bounds[1].value;
    var dx = {x} - curLeft;
    var dy = {y} - curTop;
    l.translate(new UnitValue(dx, "px"), new UnitValue(dy, "px"));
    _result = {{
        id: l.id,
        name: l.name,
        bounds: {{
            left:   l.bounds[0].value,
            top:    l.bounds[1].value,
            right:  l.bounds[2].value,
            bottom: l.bounds[3].value
        }}
    }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def scale_layer(
    name: str,
    width_pct: float = 100,
    height_pct: float = 100,
    anchor: Anchor = "center",
) -> dict:
    """Scale the named layer by percentage. `width_pct=150` scales to 1.5×.

    Anchor controls the point the scale is applied from.
    """
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    l.resize({width_pct}, {height_pct}, {_ANCHOR_MAP[anchor]});
    _result = {{
        id: l.id,
        name: l.name,
        bounds: {{
            left:   l.bounds[0].value,
            top:    l.bounds[1].value,
            right:  l.bounds[2].value,
            bottom: l.bounds[3].value
        }}
    }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def rotate_layer(
    name: str,
    degrees: float,
    anchor: Anchor = "center",
) -> dict:
    """Rotate the named layer by `degrees` around the given anchor point."""
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    l.rotate({degrees}, {_ANCHOR_MAP[anchor]});
    _result = {{
        id: l.id,
        name: l.name,
        bounds: {{
            left:   l.bounds[0].value,
            top:    l.bounds[1].value,
            right:  l.bounds[2].value,
            bottom: l.bounds[3].value
        }}
    }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def flip_layer(name: str, direction: FlipDirection) -> str:
    """Flip the named layer horizontally or vertically."""
    axis = "Hrzn" if direction == "horizontal" else "Vrtc"
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    doc.activeLayer = l;
    var desc = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putEnumerated(charIDToTypeID("Lyr "), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
    desc.putReference(charIDToTypeID("null"), ref);
    desc.putEnumerated(charIDToTypeID("Axis"), charIDToTypeID("Ornt"), charIDToTypeID("{axis}"));
    executeAction(charIDToTypeID("Flip"), desc, DialogModes.NO);
    _result = l.name;
    """
    return run_jsx(code)["result"]
