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
import tempfile
from pathlib import Path

from PIL import Image, ImageFilter

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


def _render_design_placeholder_bbox(bounds: dict, fill_hex: str = "#E0E0E0") -> Path:
    """Create a simple WxH solid-color rectangle sized to the screen bbox.

    This becomes the smart object's internal canvas — when the user double-
    clicks "Your Design" they get a clean rectangular canvas matching the
    screen area exactly. No dynamic-island cutouts inside the SO; those are
    handled by a layer mask in the main doc.
    """
    r = int(fill_hex.lstrip("#")[0:2], 16)
    g = int(fill_hex.lstrip("#")[2:4], 16)
    b = int(fill_hex.lstrip("#")[4:6], 16)
    placeholder = Image.new("RGBA", (int(bounds["width"]), int(bounds["height"])), (r, g, b, 255))
    out_path = Path(tempfile.gettempdir()) / "justtwod_design_placeholder.png"
    placeholder.save(out_path, "PNG")
    return out_path


def _render_mask_with_alpha(mask_path: Path, feather: float = 0.8) -> Path:
    """Re-encode the screen mask so its grayscale value becomes the alpha
    channel. A sub-pixel Gaussian blur is applied first because Blender's
    IDMask compositor node emits a binary mask (no anti-aliasing) — without
    feathering, the resulting layer-mask edges show stair-step jaggies in
    Photoshop at any significant zoom.
    """
    with Image.open(mask_path) as img:
        alpha = img.convert("L")
    if feather > 0:
        alpha = alpha.filter(ImageFilter.GaussianBlur(feather))
    w, h = alpha.size
    rgb = Image.new("RGB", (w, h), (128, 128, 128))
    out_img = Image.merge("RGBA", (*rgb.split(), alpha))
    out_path = Path(tempfile.gettempdir()) / f"justtwod_mask_rgba_{mask_path.stem}.png"
    out_img.save(out_path, "PNG")
    return out_path


def _estimate_corner_radius(mask_path: Path, bounds: dict) -> float | None:
    """Estimate the rounded-corner radius by least-squares fitting a circle
    to the top-left arc of the mask.

    For each row near the top of the bbox, we find the leftmost white pixel
    — those (x, y) samples trace the corner arc. Fitting a circle through
    them recovers the radius with ~1 px accuracy (vs. the row-count heuristic
    which under-estimates on anti-aliased masks).
    """
    if bounds["width"] < 40 or bounds["height"] < 40:
        return None

    with Image.open(mask_path) as img:
        gray = img.convert("L")
        pixels = gray.load()

    left = bounds["left"]
    top = bounds["top"]
    width = bounds["width"]
    height = bounds["height"]

    max_scan = min(height // 3, 200)
    samples: list[tuple[float, float]] = []
    for dy in range(max_scan):
        y = top + dy
        for x in range(left, left + width // 3):
            if pixels[x, y] > 127:
                # Stop collecting once the arc reaches the bbox left edge —
                # straight-edge rows would skew the circle fit.
                if x == left:
                    dy = max_scan  # exit outer loop
                    break
                samples.append((float(x), float(y)))
                break
        if dy == max_scan:
            break

    if len(samples) < 8:
        return None

    # Algebraic least-squares circle fit: solve A·[a, b, c] = b for the
    # center (a, b) and c = r² − a² − b².
    n = len(samples)
    sx = sy = sxx = syy = sxy = sxxx = syyy = sxyy = sxxy = 0.0
    for x, y in samples:
        sx += x;       sy += y
        sxx += x * x;  syy += y * y
        sxy += x * y
        sxxx += x * x * x
        syyy += y * y * y
        sxyy += x * y * y
        sxxy += x * x * y

    A = [
        [sxx, sxy, sx],
        [sxy, syy, sy],
        [sx,  sy,  float(n)],
    ]
    rhs = [
        -(sxxx + sxyy),
        -(sxxy + syyy),
        -(sxx + syy),
    ]

    def _solve_3x3(mat: list[list[float]], b: list[float]) -> tuple[float, float, float] | None:
        m = [row[:] + [b[i]] for i, row in enumerate(mat)]
        for i in range(3):
            pivot = i
            for k in range(i + 1, 3):
                if abs(m[k][i]) > abs(m[pivot][i]):
                    pivot = k
            if abs(m[pivot][i]) < 1e-12:
                return None
            m[i], m[pivot] = m[pivot], m[i]
            for k in range(i + 1, 3):
                factor = m[k][i] / m[i][i]
                for j in range(i, 4):
                    m[k][j] -= factor * m[i][j]
        x = [0.0, 0.0, 0.0]
        for i in range(2, -1, -1):
            s = m[i][3]
            for j in range(i + 1, 3):
                s -= m[i][j] * x[j]
            x[i] = s / m[i][i]
        return x[0], x[1], x[2]

    sol = _solve_3x3(A, rhs)
    if sol is None:
        return None
    D, E, F = sol
    cx = -D / 2.0
    cy = -E / 2.0
    r2 = cx * cx + cy * cy - F
    if r2 <= 0:
        return None

    radius = r2 ** 0.5
    expected_cx = left + radius
    expected_cy = top + radius
    if abs(cx - expected_cx) > 5 or abs(cy - expected_cy) > 5:
        return None
    return round(radius, 1)


@mcp.tool()
def build_product_mockup(
    renders_folder: str,
    output_psd: str | None = None,
    canvas_width: int | None = None,
    canvas_height: int | None = None,
    manifest: str | None = None,
    background_color: str = "#F5F5F5",
    reflections_opacity: int = 20,
    corner_radius: int | None = None,
    placeholder_color: str = "#E0E0E0",
    add_guides: bool = True,
) -> dict:
    """Build a layered, grouped, color-managed mockup PSD from Blender renders.

    Produces a PSD with this structure:

        ┌ Screen (group)
        │   ├ Screen Mask (hidden, clipping source)
        │   └ Your Design (smart object, with layer mask)
        ├ Phone (group)
        │   ├ Reflections (Screen @ reflections_opacity%)
        │   ├ Phone Body
        │   └ Shadow (Multiply)
        └ Background (solid fill)

    Parameters:
    - `renders_folder`: directory containing phone_body, phone_shadow,
      phone_reflections (optional), screen_mask files.
    - `output_psd`: where to save the finished PSD. If None, the PSD stays
      open in Photoshop unsaved.
    - `manifest`: path to a `mockup_manifest.json` from justthreed — if
      present, its canvas / bounds / corner_radius are authoritative.
    - `background_color`: hex color for the bottom Background layer.
    - `reflections_opacity`: 0-100, strength of the reflections pass.
    - `corner_radius`: pixel radius override; defaults to the manifest's
      value or an auto-estimate from the mask.
    - `placeholder_color`: fill of the "Your Design" placeholder (visible
      until the user replaces the smart object contents).
    - `add_guides`: if True, adds ruler guides at the screen bbox edges.
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
        manifest_radius = screen_region.get("corner_radius")
    else:
        measured = _measure_screen_mask(found["screen_mask"])  # type: ignore[arg-type]
        canvas_w = canvas_width or int(measured["canvas"]["width"])
        canvas_h = canvas_height or int(measured["canvas"]["height"])
        bounds = measured["bounds"]
        manifest_radius = measured.get("corner_radius")

    if corner_radius is None:
        corner_radius = manifest_radius

    paths_js = {
        "body":        js_string(str(found["phone_body"])),
        "shadow":      js_string(str(found["phone_shadow"])),
        "screen_mask": js_string(str(found["screen_mask"])),
    }
    refl = found["phone_reflections"]
    reflections_js = js_string(str(refl)) if refl else "null"

    # Two helper PNGs:
    # - placeholder_bbox.png: simple WxH rect → becomes the SO's internal canvas
    # - mask_with_alpha.png: mask luminance encoded as alpha → lets Photoshop
    #   load the screen shape as a selection for the layer mask
    placeholder_path = _render_design_placeholder_bbox(bounds, placeholder_color)
    mask_rgba_path = _render_mask_with_alpha(found["screen_mask"])  # type: ignore[arg-type]
    placeholder_js = js_string(str(placeholder_path))
    mask_rgba_js = js_string(str(mask_rgba_path))

    bg_hex = background_color.lstrip("#").upper()
    if len(bg_hex) != 6:
        raise ValueError(f"background_color must be a 6-char hex string: {background_color!r}")
    reflections_opacity = max(0, min(100, int(reflections_opacity)))

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
    var bounds = {json.dumps(bounds)};
    var cornerRadius = {corner_radius_js};
    var addGuides = {str(add_guides).lower()};

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

    // Tag with sRGB so colors are consistent across machines.
    try {{ doc.colorProfileName = "sRGB IEC61966-2.1"; }} catch (e) {{}}

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

    // --- Background layer (solid fill, always the bottom of the stack) ---
    var bgLayer = doc.artLayers.add();
    bgLayer.name = "Background";
    doc.activeLayer = bgLayer;
    var bgFill = new SolidColor();
    bgFill.rgb.hexValue = "{bg_hex}";
    doc.selection.selectAll();
    doc.selection.fill(bgFill);
    doc.selection.deselect();

    // --- Phone passes stack (bottom-up: shadow, body, reflections) ---
    var shadow = placeFile({paths_js["shadow"]}, "Shadow");
    shadow.blendMode = BlendMode.MULTIPLY;

    var body = placeFile({paths_js["body"]}, "Phone Body");

    var refl = null;
    var reflectionsPath = {reflections_js};
    if (reflectionsPath !== null) {{
        refl = placeFile(reflectionsPath, "Reflections");
        refl.blendMode = BlendMode.SCREEN;
        refl.opacity = {reflections_opacity};
    }}

    // Place the alpha-encoded mask; its transparency carries the screen
    // shape we'll later apply as a layer mask on the smart object.
    var mask = placeFile({mask_rgba_js}, "Screen Mask");
    mask.visible = false;

    // Placeholder smart object: a clean WxH rectangle sized to the screen
    // bbox. When the user double-clicks, they edit on that simple canvas
    // (no dynamic-island cutouts inside) — the mask shape is applied
    // externally as a layer mask in this doc.
    var placeholder = placeFile({placeholder_js}, "Your Design (smart object)");
    doc.activeLayer = placeholder;
    // Undo the place-action's fit-to-canvas scaling so the SO is at 1:1.
    executeAction(stringIDToTypeID("placedLayerResetTransforms"), undefined, DialogModes.NO);
    // Translate placeholder to its target position (bbox top-left).
    var pb = placeholder.bounds;
    placeholder.translate(
        new UnitValue(bounds.left - pb[0].value, "px"),
        new UnitValue(bounds.top - pb[1].value, "px")
    );
    placeholder.move(body, ElementPlacement.PLACEBEFORE);

    // Load the mask layer's transparency as a selection, then add a layer
    // mask to the placeholder that "reveals the selection" — the SO now
    // renders clipped to the exact screen shape (dynamic island, corners).
    var selDesc = new ActionDescriptor();
    var selRef = new ActionReference();
    selRef.putProperty(charIDToTypeID("Chnl"), charIDToTypeID("fsel"));
    selDesc.putReference(charIDToTypeID("null"), selRef);
    var srcRef = new ActionReference();
    srcRef.putEnumerated(charIDToTypeID("Chnl"), charIDToTypeID("Chnl"), charIDToTypeID("Trsp"));
    srcRef.putIdentifier(charIDToTypeID("Lyr "), mask.id);
    selDesc.putReference(charIDToTypeID("T   "), srcRef);
    executeAction(charIDToTypeID("setd"), selDesc, DialogModes.NO);

    doc.activeLayer = placeholder;
    var maskDesc = new ActionDescriptor();
    maskDesc.putClass(charIDToTypeID("Nw  "), charIDToTypeID("Chnl"));
    var maskRef = new ActionReference();
    maskRef.putEnumerated(charIDToTypeID("Chnl"), charIDToTypeID("Chnl"), charIDToTypeID("Msk "));
    maskDesc.putReference(charIDToTypeID("At  "), maskRef);
    maskDesc.putEnumerated(charIDToTypeID("Usng"), charIDToTypeID("UsrM"), charIDToTypeID("RvlS"));
    executeAction(charIDToTypeID("Mk  "), maskDesc, DialogModes.NO);
    try {{ doc.selection.deselect(); }} catch (e) {{}}

    // --- Organize layers into groups (senior-designer hygiene) ---
    // Phone group: Reflections (optional) + Phone Body + Shadow
    var phoneGroup = doc.layerSets.add();
    phoneGroup.name = "Phone";
    phoneGroup.move(body, ElementPlacement.PLACEBEFORE);
    if (refl !== null) refl.move(phoneGroup, ElementPlacement.PLACEATEND);
    body.move(phoneGroup, ElementPlacement.PLACEATEND);
    shadow.move(phoneGroup, ElementPlacement.PLACEATEND);

    // Screen group: Screen Mask (hidden) + Your Design (clipped)
    var screenGroup = doc.layerSets.add();
    screenGroup.name = "Screen";
    screenGroup.move(phoneGroup, ElementPlacement.PLACEBEFORE);
    placeholder.move(screenGroup, ElementPlacement.PLACEATEND);
    mask.move(screenGroup, ElementPlacement.PLACEATEND);

    // --- Ruler guides at screen bbox edges for layout reference ---
    if (addGuides) {{
        try {{
            doc.guides.add(Direction.VERTICAL,   new UnitValue(bounds.left, "px"));
            doc.guides.add(Direction.VERTICAL,   new UnitValue(bounds.right, "px"));
            doc.guides.add(Direction.HORIZONTAL, new UnitValue(bounds.top, "px"));
            doc.guides.add(Direction.HORIZONTAL, new UnitValue(bounds.bottom, "px"));
        }} catch (e) {{}}
    }}

    // --- Cleanup: drop the empty default layer PS added at doc creation ---
    for (var i = doc.layers.length - 1; i >= 0; i--) {{
        var candidate = doc.layers[i];
        if (candidate.typename === "ArtLayer" && /^Layer \\d+$/.test(candidate.name)) {{
            try {{ candidate.remove(); }} catch (e) {{}}
        }}
    }}

    // --- Push Background to the bottom of the stack ---
    try {{
        bgLayer.move(doc.layers[doc.layers.length - 1], ElementPlacement.PLACEAFTER);
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
