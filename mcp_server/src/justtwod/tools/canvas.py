"""Canvas-level tools: resize, crop, rotate, trim, flatten, merge-visible."""
from __future__ import annotations

from typing import Literal

from .._app import mcp
from ..transport import run_jsx
from ._jsx_helpers import REQUIRE_ACTIVE_DOC

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


@mcp.tool()
def resize_canvas(width: int, height: int, anchor: Anchor = "center") -> dict:
    """Resize the canvas to (width, height) pixels without rescaling the image.
    Use `anchor` to control where existing content lands in the new canvas.
    """
    code = REQUIRE_ACTIVE_DOC + f"""
    doc.resizeCanvas(new UnitValue({width}, "px"), new UnitValue({height}, "px"), {_ANCHOR_MAP[anchor]});
    _result = {{ width: doc.width.value, height: doc.height.value }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def crop(x: float, y: float, width: float, height: float) -> dict:
    """Crop the canvas to the rectangle (x, y, x+width, y+height) in pixels."""
    code = REQUIRE_ACTIVE_DOC + f"""
    doc.crop([
        new UnitValue({x}, "px"),
        new UnitValue({y}, "px"),
        new UnitValue({x + width}, "px"),
        new UnitValue({y + height}, "px")
    ]);
    _result = {{ width: doc.width.value, height: doc.height.value }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def rotate_canvas(degrees: float) -> dict:
    """Rotate the entire canvas by `degrees` (positive = clockwise)."""
    code = REQUIRE_ACTIVE_DOC + f"""
    doc.rotateCanvas({degrees});
    _result = {{ width: doc.width.value, height: doc.height.value }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def trim_transparent(top: bool = True, left: bool = True, bottom: bool = True, right: bool = True) -> dict:
    """Trim transparent edges of the canvas. Any side set to False is preserved."""
    code = REQUIRE_ACTIVE_DOC + f"""
    doc.trim(TrimType.TRANSPARENT, {str(top).lower()}, {str(left).lower()}, {str(bottom).lower()}, {str(right).lower()});
    _result = {{ width: doc.width.value, height: doc.height.value }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def flatten_image() -> dict:
    """Flatten all layers into a single background layer."""
    code = REQUIRE_ACTIVE_DOC + """
    doc.flatten();
    _result = { layer_count: doc.layers.length };
    """
    return run_jsx(code)["result"]


@mcp.tool()
def merge_visible() -> dict:
    """Merge all currently visible layers into a single layer."""
    code = REQUIRE_ACTIVE_DOC + """
    doc.mergeVisibleLayers();
    _result = { layer_count: doc.layers.length };
    """
    return run_jsx(code)["result"]
