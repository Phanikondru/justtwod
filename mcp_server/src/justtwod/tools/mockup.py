"""Composed tools: build a layered mockup PSD from a folder of render passes.

This is the flagship high-level tool justtwod was originally built for. It
chains the primitives in document / smart_object / layer / shape / selection
to produce a clean, named, editable PSD.

Expected input (produced by the justthreed Blender MCP):

    renders/
    ├── phone_body_0001.(png|tif)     required — the hero pass
    ├── phone_shadow_0001.png          required — contact shadow
    ├── phone_reflections_0001.png     optional — specular highlights
    ├── screen_mask_0001.png           required — white screen area
    └── mockup_manifest.json           optional — canvas size + editable regions

If `mockup_manifest.json` is absent, the canvas size defaults to the passes'
dimensions and the screen region is measured on the fly from `screen_mask`.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from .._app import mcp
from ..transport import run_jsx
from ._jsx_helpers import js_string

_PASSES: dict[str, tuple[str, ...]] = {
    "phone_body":        ("tif", "tiff", "png"),
    "phone_shadow":      ("png",),
    "phone_reflections": ("png",),
    "screen_mask":       ("png",),
}


def _find_latest(folder: Path, base: str, exts: tuple[str, ...]) -> Path | None:
    """Find the latest file in `folder` whose name starts with `base` or `base_`
    and ends with one of `exts`. Latest = last alphabetically (matches trailing
    version suffixes like _v02 or _0001).
    """
    matches: list[Path] = []
    base_lower = base.lower()
    for entry in folder.iterdir():
        if not entry.is_file():
            continue
        name = entry.name.lower()
        if not name.startswith(base_lower):
            continue
        after_base = name[len(base_lower):len(base_lower) + 1]
        if after_base not in (".", "_"):
            continue
        suffix = entry.suffix.lstrip(".").lower()
        if suffix not in exts:
            continue
        matches.append(entry)
    if not matches:
        return None
    matches.sort(reverse=True)
    return matches[0]


def _measure_screen_mask(mask_path: Path) -> dict:
    """Measure the screen mask's canvas size and white-pixel bounding box
    using Pillow. For a high-contrast mask, any pixel brighter than 127 counts
    as "inside" the mask. Returns {canvas, bounds, corner_radius}.

    Corner radius is estimated by fitting a circle to the top-left arc of
    the white region.
    """
    with Image.open(mask_path) as img:
        gray = img.convert("L")
        w, h = gray.size
        bbox = gray.point(lambda v: 255 if v > 127 else 0, mode="L").getbbox()
    if bbox is None:
        raise ValueError(f"Mask has no visible (white) pixels: {mask_path}")
    left, top, right, bottom = bbox  # Pillow bbox: (left, top, right, bottom); right/bottom exclusive
    bounds = {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "width": right - left,
        "height": bottom - top,
    }
    corner_radius = _estimate_corner_radius(mask_path, bounds)
    return {
        "canvas": {"width": w, "height": h},
        "bounds": bounds,
        "corner_radius": corner_radius,
    }


def _estimate_corner_radius(mask_path: Path, bounds: dict) -> float | None:
    """Estimate the rounded-corner radius by scanning the top-left arc.

    For a rounded rectangle, row y=top has its leftmost white pixel offset
    inward by r (the corner radius); at row y=top+r the leftmost white pixel
    hits the bbox's left edge. So the row index where x_first == left is
    approximately r.
    """
    if bounds["width"] < 20 or bounds["height"] < 20:
        return None

    with Image.open(mask_path) as img:
        gray = img.convert("L")
        pixels = gray.load()

    left = bounds["left"]
    top = bounds["top"]
    right = bounds["right"]
    scan_rows = min(bounds["height"] // 2, 500)
    first_left_row = None
    for dy in range(scan_rows):
        y = top + dy
        for x in range(left, right):
            if pixels[x, y] > 127:
                if x == left:
                    first_left_row = dy
                break
        if first_left_row is not None:
            break
    if first_left_row is None or first_left_row < 2:
        return 0.0
    return float(first_left_row)


@mcp.tool()
def build_product_mockup(
    renders_folder: str,
    output_psd: str | None = None,
    canvas_width: int | None = None,
    canvas_height: int | None = None,
    manifest: str | None = None,
) -> dict:
    """Build a layered mockup PSD from a folder of Blender render passes.

    Looks for `phone_body`, `phone_shadow`, `phone_reflections` (optional),
    and `screen_mask` files in the folder (trailing version suffixes OK).
    Creates a new document, places each pass as its own layer with the
    correct blend mode, and adds a "Your Design" smart-object placeholder
    sized to the screen mask's bounding box.

    If `manifest` points to a `mockup_manifest.json` produced by justthreed,
    its canvas dimensions and editable-region bounds are used directly,
    skipping the on-the-fly measurement.

    If `output_psd` is given, saves the finished PSD to that path.
    """
    folder = Path(renders_folder).expanduser().resolve()
    if not folder.is_dir():
        raise ValueError(f"Not a directory: {folder}")

    found: dict[str, Path | None] = {
        name: _find_latest(folder, name, exts) for name, exts in _PASSES.items()
    }
    missing = [
        name for name in ("phone_body", "phone_shadow", "screen_mask")
        if found[name] is None
    ]
    if missing:
        raise ValueError(
            f"Missing required passes in {folder}: {', '.join(missing)}. "
            f"Found: {sorted(p.name for p in folder.iterdir() if p.is_file())}"
        )

    manifest_data: dict | None = None
    if manifest:
        manifest_data = json.loads(Path(manifest).read_text())
    elif (folder / "mockup_manifest.json").exists():
        manifest_data = json.loads((folder / "mockup_manifest.json").read_text())

    if manifest_data:
        canvas_w = int(manifest_data["canvas"]["width"])
        canvas_h = int(manifest_data["canvas"]["height"])
        screen_region = manifest_data["editable_regions"][0]
        bounds = screen_region["bounds"]
        corner_radius = screen_region.get("corner_radius")
    else:
        measured = _measure_screen_mask(found["screen_mask"])  # type: ignore[arg-type]
        canvas_w = canvas_width or int(measured["canvas"]["width"])
        canvas_h = canvas_height or int(measured["canvas"]["height"])
        bounds = measured["bounds"]
        corner_radius = measured.get("corner_radius")

    paths_js = {
        "body":        js_string(str(found["phone_body"])),
        "shadow":      js_string(str(found["phone_shadow"])),
        "screen_mask": js_string(str(found["screen_mask"])),
    }
    refl = found["phone_reflections"]
    reflections_js = js_string(str(refl)) if refl else "null"

    save_js = ""
    if output_psd:
        out = str(Path(output_psd).expanduser().resolve())
        save_js = f"""
        var saveFile = new File({js_string(out)});
        var opts = new PhotoshopSaveOptions();
        opts.embedColorProfile = true;
        opts.alphaChannels = true;
        opts.layers = true;
        opts.spotColors = true;
        doc.saveAs(saveFile, opts, true);
        """

    corner_radius_js = (
        f"{float(corner_radius)}" if isinstance(corner_radius, (int, float)) else "null"
    )

    code = f"""
    var doc = app.documents.add(
        new UnitValue({canvas_w}, "px"),
        new UnitValue({canvas_h}, "px"),
        72,
        "Product Mockup",
        NewDocumentMode.RGB,
        DocumentFill.TRANSPARENT,
        1.0,
        BitsPerChannelType.SIXTEEN
    );

    function placeFile(path, layerName) {{
        var f = new File(path);
        if (!f.exists) throw new Error("File missing: " + f.fsName);
        var desc = new ActionDescriptor();
        desc.putPath(charIDToTypeID("null"), f);
        desc.putEnumerated(charIDToTypeID("FTcs"), charIDToTypeID("QCSt"), charIDToTypeID("Qcsa"));
        executeAction(charIDToTypeID("Plc "), desc, DialogModes.NO);
        var l = doc.activeLayer;
        l.name = layerName;
        return l;
    }}

    // Stack bottom-up so each new placement sits above the previous.
    var shadow = placeFile({paths_js["shadow"]}, "Shadow");
    shadow.blendMode = BlendMode.MULTIPLY;

    var body = placeFile({paths_js["body"]}, "Phone Body");

    var reflectionsPath = {reflections_js};
    if (reflectionsPath !== null) {{
        var refl = placeFile(reflectionsPath, "Reflections");
        refl.blendMode = BlendMode.SCREEN;
        refl.opacity = 40;
    }}

    var mask = placeFile({paths_js["screen_mask"]}, "Screen Mask");
    mask.visible = false;

    // Smart object placeholder: a solid-color smart object sized to the
    // screen bbox. User double-clicks it and replaces with their design.
    var bounds = {json.dumps(bounds)};
    var cornerRadius = {corner_radius_js};

    // Create a new layer, draw a rounded rect on it, convert to smart object.
    var placeholder = doc.artLayers.add();
    placeholder.name = "Your Design (smart object)";
    doc.activeLayer = placeholder;
    var fill = new SolidColor();
    fill.rgb.hexValue = "E0E0E0";

    if (cornerRadius && cornerRadius > 0) {{
        var r = cornerRadius;
        var x1 = bounds.left, y1 = bounds.top, x2 = bounds.right, y2 = bounds.bottom;
        function fillRect(a, b, c, d) {{
            doc.selection.select([[a,b],[c,b],[c,d],[a,d]], SelectionType.REPLACE, 0, false);
            doc.selection.fill(fill);
        }}
        function fillEllipse(cx, cy, rad) {{
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
            doc.selection.fill(fill);
        }}
        fillRect(x1 + r, y1, x2 - r, y2);
        fillRect(x1, y1 + r, x2, y2 - r);
        fillEllipse(x1 + r, y1 + r, r);
        fillEllipse(x2 - r, y1 + r, r);
        fillEllipse(x2 - r, y2 - r, r);
        fillEllipse(x1 + r, y2 - r, r);
    }} else {{
        doc.selection.select([
            [bounds.left,  bounds.top],
            [bounds.right, bounds.top],
            [bounds.right, bounds.bottom],
            [bounds.left,  bounds.bottom]
        ], SelectionType.REPLACE, 0, false);
        doc.selection.fill(fill);
    }}
    doc.selection.deselect();
    doc.activeLayer = placeholder;
    executeAction(stringIDToTypeID("newPlacedLayer"), undefined, DialogModes.NO);

    // Reorder: placeholder above Phone Body, below Screen Mask (which is hidden).
    var placeholderLayer = doc.activeLayer;
    try {{
        placeholderLayer.move(body, ElementPlacement.PLACEBEFORE);
    }} catch (e) {{}}

    {save_js}

    _result = {{
        document: {{
            id: doc.id,
            name: doc.name,
            width: doc.width.value,
            height: doc.height.value,
            layer_count: doc.layers.length
        }},
        screen_bounds: bounds,
        corner_radius: cornerRadius,
        saved_to: {js_string(str(Path(output_psd).expanduser().resolve())) if output_psd else "null"}
    }};
    """
    return run_jsx(code, timeout=120.0)["result"]
