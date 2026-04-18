"""Layer tools: create, duplicate, delete, rename, group, reorder, and
modify common properties (visibility, opacity, blend mode)."""
from __future__ import annotations

from typing import Literal

from .._app import mcp
from ..transport import run_jsx
from ._jsx_helpers import FIND_LAYER_BY_NAME, REQUIRE_ACTIVE_DOC, js_string

BlendMode = Literal[
    "normal", "dissolve",
    "darken", "multiply", "color_burn", "linear_burn", "darker_color",
    "lighten", "screen", "color_dodge", "linear_dodge", "lighter_color",
    "overlay", "soft_light", "hard_light", "vivid_light", "linear_light", "pin_light", "hard_mix",
    "difference", "exclusion", "subtract", "divide",
    "hue", "saturation", "color", "luminosity",
]

_BLEND_MODE_MAP = {
    "normal": "BlendMode.NORMAL",
    "dissolve": "BlendMode.DISSOLVE",
    "darken": "BlendMode.DARKEN",
    "multiply": "BlendMode.MULTIPLY",
    "color_burn": "BlendMode.COLORBURN",
    "linear_burn": "BlendMode.LINEARBURN",
    "darker_color": "BlendMode.DARKERCOLOR",
    "lighten": "BlendMode.LIGHTEN",
    "screen": "BlendMode.SCREEN",
    "color_dodge": "BlendMode.COLORDODGE",
    "linear_dodge": "BlendMode.LINEARDODGE",
    "lighter_color": "BlendMode.LIGHTERCOLOR",
    "overlay": "BlendMode.OVERLAY",
    "soft_light": "BlendMode.SOFTLIGHT",
    "hard_light": "BlendMode.HARDLIGHT",
    "vivid_light": "BlendMode.VIVIDLIGHT",
    "linear_light": "BlendMode.LINEARLIGHT",
    "pin_light": "BlendMode.PINLIGHT",
    "hard_mix": "BlendMode.HARDMIX",
    "difference": "BlendMode.DIFFERENCE",
    "exclusion": "BlendMode.EXCLUSION",
    "subtract": "BlendMode.SUBTRACT",
    "divide": "BlendMode.DIVIDE",
    "hue": "BlendMode.HUE",
    "saturation": "BlendMode.SATURATION",
    "color": "BlendMode.COLOR",
    "luminosity": "BlendMode.LUMINOSITY",
}

ReorderPosition = Literal["top", "bottom", "up", "down"]


@mcp.tool()
def create_layer(name: str, above: str | None = None) -> dict:
    """Create a new empty layer in the active document.

    If `above` is given, the new layer is inserted directly above that layer;
    otherwise it sits at the top of the stack. Returns the new layer's id/name.
    """
    above_code = (
        f"""
        var ref = requireLayer({js_string(above)});
        l.move(ref, ElementPlacement.PLACEBEFORE);
        """
        if above
        else ""
    )
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = doc.artLayers.add();
    l.name = {js_string(name)};
    {above_code}
    _result = {{ id: l.id, name: l.name }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def duplicate_layer(name: str, new_name: str | None = None) -> dict:
    """Duplicate the named layer. The copy sits directly above the original."""
    rename_code = (
        f"copy.name = {js_string(new_name)};" if new_name else ""
    )
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var src = requireLayer({js_string(name)});
    var copy = src.duplicate();
    {rename_code}
    _result = {{ id: copy.id, name: copy.name }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def delete_layer(name: str) -> str:
    """Delete the named layer. Returns the deleted name."""
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    var n = l.name;
    l.remove();
    _result = n;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def rename_layer(name: str, new_name: str) -> str:
    """Rename a layer. Returns the new name."""
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    l.name = {js_string(new_name)};
    _result = l.name;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def group_layers(names: list[str], group_name: str = "Group") -> dict:
    """Group the given layers into a new LayerSet. Layers are moved into the
    new group in the order they appear in `names`. The group is inserted at
    the position of the first-named layer.
    """
    if not names:
        raise ValueError("names must contain at least one layer")
    names_js = "[" + ",".join(js_string(n) for n in names) + "]"
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var names = {names_js};
    var first = requireLayer(names[0]);
    var group = doc.layerSets.add();
    group.name = {js_string(group_name)};
    group.move(first, ElementPlacement.PLACEBEFORE);
    for (var i = 0; i < names.length; i++) {{
        var l = requireLayer(names[i]);
        l.move(group, ElementPlacement.PLACEATEND);
    }}
    _result = {{ id: group.id, name: group.name, layer_count: group.layers.length }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def set_layer_blend_mode(name: str, mode: BlendMode) -> str:
    """Set a layer's blend mode (normal, multiply, screen, overlay, etc.)."""
    blend_enum = _BLEND_MODE_MAP[mode]
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    l.blendMode = {blend_enum};
    _result = String(l.blendMode);
    """
    return run_jsx(code)["result"]


@mcp.tool()
def set_layer_opacity(name: str, opacity: float) -> float:
    """Set a layer's opacity, 0–100."""
    opacity = max(0.0, min(100.0, float(opacity)))
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    l.opacity = {opacity};
    _result = l.opacity;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def set_layer_visibility(name: str, visible: bool) -> bool:
    """Show or hide a layer."""
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    l.visible = {"true" if visible else "false"};
    _result = l.visible;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def reorder_layer(name: str, position: ReorderPosition) -> dict:
    """Reorder a layer in the stack.
    - `top` / `bottom`: move to absolute top or bottom of its parent
    - `up` / `down`: shift one position
    """
    actions = {
        "top": """
            var parent = l.parent;
            if (parent.layers && parent.layers.length > 0) {
                l.move(parent.layers[0], ElementPlacement.PLACEBEFORE);
            }
        """,
        "bottom": """
            var parent = l.parent;
            if (parent.layers && parent.layers.length > 0) {
                l.move(parent.layers[parent.layers.length - 1], ElementPlacement.PLACEAFTER);
            }
        """,
        "up": """
            var parent = l.parent;
            var idx = -1;
            for (var i = 0; i < parent.layers.length; i++) if (parent.layers[i].id === l.id) { idx = i; break; }
            if (idx > 0) l.move(parent.layers[idx - 1], ElementPlacement.PLACEBEFORE);
        """,
        "down": """
            var parent = l.parent;
            var idx = -1;
            for (var i = 0; i < parent.layers.length; i++) if (parent.layers[i].id === l.id) { idx = i; break; }
            if (idx >= 0 && idx < parent.layers.length - 1) l.move(parent.layers[idx + 1], ElementPlacement.PLACEAFTER);
        """,
    }
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    {actions[position]}
    _result = {{ id: l.id, name: l.name }};
    """
    return run_jsx(code)["result"]
