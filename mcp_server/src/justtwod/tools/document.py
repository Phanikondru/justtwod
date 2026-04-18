"""Document tools: create, open, save, close, export."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from .._app import mcp
from ..transport import run_jsx
from ._jsx_helpers import REQUIRE_ACTIVE_DOC, js_bool, js_string

ColorMode = Literal["rgb", "cmyk", "grayscale", "lab", "bitmap"]
Fill = Literal["white", "black", "transparent", "background"]
SaveFormat = Literal["psd", "psb", "tiff", "jpg", "png"]
ExportFormat = Literal["png", "jpg", "webp"]

_COLOR_MODE = {
    "rgb": "NewDocumentMode.RGB",
    "cmyk": "NewDocumentMode.CMYK",
    "grayscale": "NewDocumentMode.GRAYSCALE",
    "lab": "NewDocumentMode.LAB",
    "bitmap": "NewDocumentMode.BITMAP",
}
_FILL = {
    "white": "DocumentFill.WHITE",
    "black": "DocumentFill.BLACK",
    "transparent": "DocumentFill.TRANSPARENT",
    "background": "DocumentFill.BACKGROUNDCOLOR",
}


@mcp.tool()
def new_document(
    width: int,
    height: int,
    resolution: float = 72.0,
    name: str = "Untitled",
    color_mode: ColorMode = "rgb",
    fill: Fill = "transparent",
    bits_per_channel: Literal[8, 16, 32] = 8,
) -> dict:
    """Create a new Photoshop document and make it active.

    Width and height are in pixels. Returns the new document's id and name.
    """
    bits_map = {8: "BitsPerChannelType.EIGHT", 16: "BitsPerChannelType.SIXTEEN", 32: "BitsPerChannelType.THIRTYTWO"}
    code = f"""
    var doc = app.documents.add(
        new UnitValue({width}, "px"),
        new UnitValue({height}, "px"),
        {resolution},
        {js_string(name)},
        {_COLOR_MODE[color_mode]},
        {_FILL[fill]},
        1.0,
        {bits_map[bits_per_channel]}
    );
    _result = {{ id: doc.id, name: doc.name, width: doc.width.value, height: doc.height.value }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def open_file(path: str) -> dict:
    """Open an image or PSD file. Returns the newly active document's metadata."""
    abs_path = str(Path(path).expanduser().resolve())
    code = f"""
    var f = new File({js_string(abs_path)});
    if (!f.exists) throw new Error("File not found: " + f.fsName);
    var doc = app.open(f);
    _result = {{ id: doc.id, name: doc.name, path: doc.fullName.fsName }};
    """
    return run_jsx(code)["result"]


@mcp.tool()
def save() -> str:
    """Save the active document to its existing path. Fails if the document has never been saved."""
    code = REQUIRE_ACTIVE_DOC + """
    if (!doc.saved && doc.path === undefined) {
        throw new Error("Document has no path yet. Use save_as instead.");
    }
    doc.save();
    _result = doc.fullName.fsName;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def save_as(path: str, format: SaveFormat = "psd", quality: int = 10) -> str:
    """Save the active document to a new path. `quality` only applies to jpg (1-12)."""
    abs_path = str(Path(path).expanduser().resolve())
    quality = max(1, min(12, int(quality)))
    code = REQUIRE_ACTIVE_DOC + f"""
    var targetFile = new File({js_string(abs_path)});
    var fmt = {js_string(format)};
    var opts;
    if (fmt === "psd") {{
        opts = new PhotoshopSaveOptions();
        opts.embedColorProfile = true;
        opts.alphaChannels = true;
        opts.layers = true;
        opts.spotColors = true;
    }} else if (fmt === "psb") {{
        opts = new PhotoshopSaveOptions();
        opts.maximizeCompatibility = true;
    }} else if (fmt === "tiff") {{
        opts = new TiffSaveOptions();
        opts.imageCompression = TIFFEncoding.TIFFLZW;
        opts.layers = true;
    }} else if (fmt === "jpg") {{
        opts = new JPEGSaveOptions();
        opts.quality = {quality};
    }} else if (fmt === "png") {{
        opts = new PNGSaveOptions();
    }} else {{
        throw new Error("Unsupported format: " + fmt);
    }}
    doc.saveAs(targetFile, opts, true);
    _result = doc.fullName.fsName;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def close_document(save_changes: bool = False) -> str:
    """Close the active document. If `save_changes` is false, unsaved changes are discarded."""
    code = REQUIRE_ACTIVE_DOC + f"""
    var name = doc.name;
    doc.close({"SaveOptions.SAVECHANGES" if save_changes else "SaveOptions.DONOTSAVECHANGES"});
    _result = name;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def export_as(path: str, format: ExportFormat = "png", quality: int = 90) -> str:
    """Export the active document as a flattened raster file (PNG/JPG/WebP).

    For JPG/WebP, `quality` is 1–100. PNG ignores quality.
    Use `save_as` if you need to keep the PSD's layers.
    """
    abs_path = str(Path(path).expanduser().resolve())
    quality = max(1, min(100, int(quality)))
    code = REQUIRE_ACTIVE_DOC + f"""
    var targetFile = new File({js_string(abs_path)});
    var fmt = {js_string(format)};
    if (fmt === "png") {{
        var opts = new ExportOptionsSaveForWeb();
        opts.format = SaveDocumentType.PNG;
        opts.PNG8 = false;
        opts.transparency = true;
        doc.exportDocument(targetFile, ExportType.SAVEFORWEB, opts);
    }} else if (fmt === "jpg") {{
        var opts = new ExportOptionsSaveForWeb();
        opts.format = SaveDocumentType.JPEG;
        opts.quality = {quality};
        doc.exportDocument(targetFile, ExportType.SAVEFORWEB, opts);
    }} else if (fmt === "webp") {{
        // WebP export was added in Photoshop 23.2 (2022). Uses the Action Manager.
        var desc = new ActionDescriptor();
        var fmtDesc = new ActionDescriptor();
        fmtDesc.putEnumerated(stringIDToTypeID("compression"), stringIDToTypeID("WebPCompression"), stringIDToTypeID("compressionLossy"));
        fmtDesc.putInteger(stringIDToTypeID("quality"), {quality});
        fmtDesc.putBoolean(stringIDToTypeID("includeXMPData"), false);
        fmtDesc.putBoolean(stringIDToTypeID("includeEXIFData"), false);
        fmtDesc.putBoolean(stringIDToTypeID("includePSExtras"), false);
        desc.putObject(stringIDToTypeID("as"), stringIDToTypeID("WebPFormat"), fmtDesc);
        desc.putPath(stringIDToTypeID("in"), targetFile);
        desc.putBoolean(stringIDToTypeID("copy"), true);
        desc.putBoolean(stringIDToTypeID("lowerCase"), true);
        desc.putEnumerated(stringIDToTypeID("saveStage"), stringIDToTypeID("saveStageType"), stringIDToTypeID("saveBegin"));
        executeAction(stringIDToTypeID("save"), desc, DialogModes.NO);
    }} else {{
        throw new Error("Unsupported export format: " + fmt);
    }}
    _result = targetFile.fsName;
    """
    return run_jsx(code)["result"]
