"""Adjustment and filter tools: levels, hue/saturation, color balance,
brightness/contrast, gaussian blur, motion blur, sharpen, noise.

All adjustments are destructive — they bake into the active layer's pixels.
For non-destructive edits, convert the layer to a smart object first.
"""
from __future__ import annotations

from typing import Literal

from .._app import mcp
from ..transport import run_jsx
from ._jsx_helpers import FIND_LAYER_BY_NAME, REQUIRE_ACTIVE_DOC, js_string

NoiseDistribution = Literal["uniform", "gaussian"]

_NOISE_DIST = {
    "uniform":  "NoiseDistribution.UNIFORM",
    "gaussian": "NoiseDistribution.GAUSSIAN",
}


@mcp.tool()
def apply_levels(
    name: str,
    input_black: int = 0,
    input_white: int = 255,
    gamma: float = 1.0,
    output_black: int = 0,
    output_white: int = 255,
) -> str:
    """Adjust levels on the named layer (destructive).

    Typical usage: increase contrast by bringing `input_black` up (e.g. 20)
    and `input_white` down (e.g. 235). `gamma` > 1 brightens midtones, < 1
    darkens them.
    """
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    doc.activeLayer = l;
    l.adjustLevels({input_black}, {input_white}, {gamma}, {output_black}, {output_white});
    _result = l.name;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def apply_brightness_contrast(name: str, brightness: int = 0, contrast: int = 0) -> str:
    """Adjust brightness and contrast on the named layer. Each value is -150..150."""
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    doc.activeLayer = l;
    l.adjustBrightnessContrast({brightness}, {contrast});
    _result = l.name;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def apply_hue_saturation(
    name: str,
    hue: int = 0,
    saturation: int = 0,
    lightness: int = 0,
    colorize: bool = False,
) -> str:
    """Adjust hue / saturation / lightness on the named layer.

    - `hue`: -180..180
    - `saturation`, `lightness`: -100..100
    - `colorize`: if true, applies the hue uniformly across all colors
    """
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    doc.activeLayer = l;
    // Use Action Manager (adjustHueSaturation is not a method on ArtLayer in modern PS).
    var desc = new ActionDescriptor();
    desc.putBoolean(charIDToTypeID("Clrz"), {"true" if colorize else "false"});
    var adjList = new ActionList();
    var adjDesc = new ActionDescriptor();
    adjDesc.putInteger(charIDToTypeID("H   "), {hue});
    adjDesc.putInteger(charIDToTypeID("Strt"), {saturation});
    adjDesc.putInteger(charIDToTypeID("Lght"), {lightness});
    adjList.putObject(charIDToTypeID("Hst2"), adjDesc);
    desc.putList(charIDToTypeID("Adjs"), adjList);
    executeAction(charIDToTypeID("HStr"), desc, DialogModes.NO);
    _result = l.name;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def apply_color_balance(
    name: str,
    shadows: list[int] | None = None,
    midtones: list[int] | None = None,
    highlights: list[int] | None = None,
    preserve_luminosity: bool = True,
) -> str:
    """Color balance on the named layer. Each tuple is [cyan-red, magenta-green, yellow-blue]
    in the range -100..100. Defaults are [0,0,0] (no change).
    """
    def _triple(t: list[int] | None) -> list[int]:
        if t is None:
            return [0, 0, 0]
        if len(t) != 3:
            raise ValueError(f"Expected 3 values, got {len(t)}")
        return [max(-100, min(100, int(v))) for v in t]
    s = _triple(shadows)
    m = _triple(midtones)
    h = _triple(highlights)
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    doc.activeLayer = l;
    l.adjustColorBalance(
        [{s[0]}, {s[1]}, {s[2]}],
        [{m[0]}, {m[1]}, {m[2]}],
        [{h[0]}, {h[1]}, {h[2]}],
        {"true" if preserve_luminosity else "false"}
    );
    _result = l.name;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def gaussian_blur(name: str, radius: float) -> str:
    """Apply gaussian blur to the named layer. `radius` is in pixels (0.1..1000)."""
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    doc.activeLayer = l;
    l.applyGaussianBlur({radius});
    _result = l.name;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def motion_blur(name: str, angle: float = 0, distance: float = 10) -> str:
    """Apply motion blur. `angle` in degrees (-360..360), `distance` in pixels (1..2000)."""
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    doc.activeLayer = l;
    l.applyMotionBlur({angle}, {distance});
    _result = l.name;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def sharpen(name: str, amount: float = 50, radius: float = 1.0, threshold: int = 0) -> str:
    """Apply Unsharp Mask to the named layer.

    - `amount`: 1..500 (percent) — strength of the sharpening
    - `radius`: 0.1..1000 (pixels) — halo size
    - `threshold`: 0..255 — minimum edge contrast to sharpen
    """
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    doc.activeLayer = l;
    l.applyUnSharpMask({amount}, {radius}, {threshold});
    _result = l.name;
    """
    return run_jsx(code)["result"]


@mcp.tool()
def add_noise(
    name: str,
    amount: float = 12.5,
    distribution: NoiseDistribution = "gaussian",
    monochromatic: bool = True,
) -> str:
    """Add noise to the named layer.

    - `amount`: 0.1..400 (percent)
    - `distribution`: "uniform" (even) or "gaussian" (natural film grain)
    - `monochromatic`: if true, noise is grayscale; otherwise colored
    """
    code = REQUIRE_ACTIVE_DOC + FIND_LAYER_BY_NAME + f"""
    var l = requireLayer({js_string(name)});
    doc.activeLayer = l;
    l.applyAddNoise({amount}, {_NOISE_DIST[distribution]}, {"true" if monochromatic else "false"});
    _result = l.name;
    """
    return run_jsx(code)["result"]
