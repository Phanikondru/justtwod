"""Inspection tools: list and introspect documents and layers."""
from __future__ import annotations

from .._app import mcp
from ..transport import run_jsx
from ._jsx_helpers import REQUIRE_ACTIVE_DOC, js_string


@mcp.tool()
def get_document_info() -> dict:
    """Return metadata for the active document: id, name, size, resolution, color mode, layer count, saved path."""
    code = REQUIRE_ACTIVE_DOC + """
    _result = {
        id: doc.id,
        name: doc.name,
        width: doc.width.value,
        height: doc.height.value,
        resolution: doc.resolution,
        mode: String(doc.mode),
        bits_per_channel: (function () {
            var s = String(doc.bitsPerChannel);
            if (s === "BitsPerChannelType.EIGHT") return 8;
            if (s === "BitsPerChannelType.SIXTEEN") return 16;
            if (s === "BitsPerChannelType.THIRTYTWO") return 32;
            return null;
        })(),
        layer_count: doc.layers.length,
        path: (function () { try { return doc.fullName.fsName; } catch (e) { return null; } })()
    };
    """
    return run_jsx(code)["result"]


@mcp.tool()
def list_documents() -> list:
    """List all currently open documents with id, name, and active flag."""
    code = """
    var active = (app.documents.length > 0) ? app.activeDocument : null;
    var out = [];
    for (var i = 0; i < app.documents.length; i++) {
        var d = app.documents[i];
        out.push({
            id: d.id,
            name: d.name,
            width: d.width.value,
            height: d.height.value,
            is_active: (active !== null && d.id === active.id)
        });
    }
    _result = out;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def list_layers(recursive: bool = True) -> list:
    """List all layers in the active document. With `recursive=True` (default),
    descends into layer sets (groups) and includes a `depth` field. Flat order
    is top-to-bottom as seen in the Layers panel."""
    code = REQUIRE_ACTIVE_DOC + f"""
    var recursive = {str(recursive).lower()};
    function walk(layers, depth, out) {{
        for (var i = 0; i < layers.length; i++) {{
            var l = layers[i];
            var isGroup = (l.typename === "LayerSet");
            var entry = {{
                id: l.id,
                name: l.name,
                typename: l.typename,
                kind: isGroup ? "group" : String(l.kind),
                visible: l.visible,
                opacity: l.opacity,
                blend_mode: String(l.blendMode),
                depth: depth
            }};
            out.push(entry);
            if (recursive && isGroup) walk(l.layers, depth + 1, out);
        }}
        return out;
    }}
    _result = walk(doc.layers, 0, []);
    """
    return run_jsx(code)["result"]


@mcp.tool()
def get_layer_info(name: str) -> dict:
    """Return detailed info for a single layer (by name). Searches recursively
    and returns the first match.
    """
    code = REQUIRE_ACTIVE_DOC + f"""
    var target = {js_string(name)};
    function find(layers) {{
        for (var i = 0; i < layers.length; i++) {{
            var l = layers[i];
            if (l.name === target) return l;
            if (l.typename === "LayerSet") {{
                var r = find(l.layers);
                if (r) return r;
            }}
        }}
        return null;
    }}
    var l = find(doc.layers);
    if (!l) throw new Error("Layer not found: " + target);
    var bounds = null;
    try {{
        bounds = {{
            left:   l.bounds[0].value,
            top:    l.bounds[1].value,
            right:  l.bounds[2].value,
            bottom: l.bounds[3].value
        }};
    }} catch (e) {{ bounds = null; }}
    _result = {{
        id: l.id,
        name: l.name,
        typename: l.typename,
        kind: (l.typename === "LayerSet") ? "group" : String(l.kind),
        visible: l.visible,
        opacity: l.opacity,
        blend_mode: String(l.blendMode),
        bounds: bounds
    }};
    """
    return run_jsx(code)["result"]
