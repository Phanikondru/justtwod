"""Shared JSX snippets used by multiple tool modules."""
from __future__ import annotations

REQUIRE_ACTIVE_DOC = """
if (app.documents.length === 0) {
    throw new Error("No document is open. Create or open one first.");
}
var doc = app.activeDocument;
"""

FIND_LAYER_BY_NAME = """
function findLayerByName(layers, target) {
    for (var i = 0; i < layers.length; i++) {
        var l = layers[i];
        if (l.name === target) return l;
        if (l.typename === "LayerSet") {
            var r = findLayerByName(l.layers, target);
            if (r) return r;
        }
    }
    return null;
}
function requireLayer(name) {
    var l = findLayerByName(doc.layers, name);
    if (!l) throw new Error("Layer not found: " + name);
    return l;
}
"""


def js_string(s: str) -> str:
    """Escape a Python string for safe embedding in ExtendScript as a double-quoted string."""
    return '"' + (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    ) + '"'


def js_bool(b: bool) -> str:
    return "true" if b else "false"
