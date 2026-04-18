"""Text tools: create text layers and edit their content, font, size, color,
and alignment.
"""
from __future__ import annotations

import re
from typing import Literal

from .._app import mcp
from ..transport import run_jsx
from ._jsx_helpers import FIND_LAYER_BY_NAME, REQUIRE_ACTIVE_DOC, js_string

Alignment = Literal["left", "center", "right"]

_ALIGN_MAP = {
    "left": "Justification.LEFT",
    "center": "Justification.CENTER",
    "right": "Justification.RIGHT",
}


def _clean_hex(color: str) -> str:
    c = color.lstrip("#").strip().upper()
    if not re.fullmatch(r"[0-9A-F]{6}", c):
        raise ValueError(f"color must be a 6-char hex string (got {color!r})")
    return c


@mcp.tool()
def create_text_layer(
    text: str,
    x: float = 100,
    y: float = 100,
    font_size: float = 36,
    font: str = "Helvetica",
    color: str = "#000000",
    name: str | None = None,
    alignment: Alignment = "left",
) -> dict:
    """Create a point-text layer at (x, y) with the given content and style.

    `color` is a hex string like "#FF0000". `font` should be the font's
    PostScript name when possible (e.g. "Helvetica", "ArialMT", "Inter-Bold").
    Position (x, y) is the baseline anchor in pixels from the top-left.
    """
    hex_color = _clean_hex(color)
    layer_name = name or (text[:30] if text else "Text")
    code = REQUIRE_ACTIVE_DOC + f"""
    var tl = doc.artLayers.add();
    tl.kind = LayerKind.TEXT;
    tl.name = {js_string(layer_name)};
    var ti = tl.textItem;
    ti.kind = TextType.POINTTEXT;
    ti.contents = {js_string(text)};
    ti.position = [new UnitValue({x}, "px"), new UnitValue({y}, "px")];
    ti.size = new UnitValue({font_size}, "px");
    ti.font = {js_string(font)};
    ti.justification = {_ALIGN_MAP[alignment]};
    var c = new SolidColor();
    c.rgb.hexValue = {js_string(hex_color)};
    ti.color = c;
    _result = {{ id: tl.id, name: tl.name }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def create_paragraph_text(
    text: str,
    x: float,
    y: float,
    width: float,
    height: float,
    font_size: float = 18,
    font: str = "Helvetica",
    color: str = "#000000",
    alignment: Alignment = "left",
    name: str | None = None,
) -> dict:
    """Create a paragraph text layer inside a bounding box at (x, y) of size
    (width, height). Text wraps inside the box.
    """
    hex_color = _clean_hex(color)
    layer_name = name or (text[:30] if text else "Paragraph")
    code = REQUIRE_ACTIVE_DOC + f"""
    var tl = doc.artLayers.add();
    tl.kind = LayerKind.TEXT;
    tl.name = {js_string(layer_name)};
    var ti = tl.textItem;
    ti.kind = TextType.PARAGRAPHTEXT;
    ti.contents = {js_string(text)};
    ti.position = [new UnitValue({x}, "px"), new UnitValue({y}, "px")];
    ti.width = new UnitValue({width}, "px");
    ti.height = new UnitValue({height}, "px");
    ti.size = new UnitValue({font_size}, "px");
    ti.font = {js_string(font)};
    ti.justification = {_ALIGN_MAP[alignment]};
    var c = new SolidColor();
    c.rgb.hexValue = {js_string(hex_color)};
    ti.color = c;
    _result = {{ id: tl.id, name: tl.name }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def set_text_content(name: str, text: str) -> str:
    """Replace the contents of a text layer."""
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    if (l.kind !== LayerKind.TEXT) throw new Error("Layer is not a text layer: " + l.name);
    l.textItem.contents = {js_string(text)};
    _result = l.textItem.contents;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def set_font(name: str, font: str) -> str:
    """Change the font of a text layer (PostScript name recommended)."""
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    if (l.kind !== LayerKind.TEXT) throw new Error("Layer is not a text layer: " + l.name);
    l.textItem.font = {js_string(font)};
    _result = l.textItem.font;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def set_text_size(name: str, font_size: float) -> float:
    """Change the font size (in pixels) of a text layer."""
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    if (l.kind !== LayerKind.TEXT) throw new Error("Layer is not a text layer: " + l.name);
    l.textItem.size = new UnitValue({font_size}, "px");
    _result = l.textItem.size.value;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def set_text_color(name: str, color: str) -> str:
    """Change the color of a text layer (hex string like '#FF0000')."""
    hex_color = _clean_hex(color)
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    if (l.kind !== LayerKind.TEXT) throw new Error("Layer is not a text layer: " + l.name);
    var c = new SolidColor();
    c.rgb.hexValue = {js_string(hex_color)};
    l.textItem.color = c;
    _result = l.textItem.color.rgb.hexValue;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def set_text_alignment(name: str, alignment: Alignment) -> str:
    """Set text alignment: left, center, or right."""
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    if (l.kind !== LayerKind.TEXT) throw new Error("Layer is not a text layer: " + l.name);
    l.textItem.justification = {_ALIGN_MAP[alignment]};
    _result = String(l.textItem.justification);
    """
    return run_jsx(code)["result"]
