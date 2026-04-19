# `mockup_manifest.json` schema

The manifest is the contract between `justthreed` (Blender → renders) and
`justtwod` (renders → PSD). Writing it is optional — justtwod will measure
the screen bbox from the mask PNG and estimate the corner radius if no
manifest is provided — but a manifest is faster, more accurate, and opens
the door to multi-region mockups (laptop screen + keyboard, bottle label +
cap, etc.).

## v1 schema

```json
{
  "version": 1,
  "product": "iphone17_pro",
  "canvas": {
    "width": 3840,
    "height": 2160,
    "resolution": 72
  },
  "passes": {
    "body": "phone_body_0001.tif",
    "shadow": "phone_shadow_0001.png",
    "reflections": "phone_reflections_0001.png",
    "screen_mask": "screen_mask_0001.png"
  },
  "editable_regions": [
    {
      "name": "Screen",
      "bounds": {
        "left": 1619,
        "top": 433,
        "right": 2221,
        "bottom": 1727,
        "width": 602,
        "height": 1294
      },
      "corner_radius": 75,
      "perspective": null,
      "cutouts": [
        {
          "name": "DynamicIsland",
          "bounds": {
            "left": 1798,
            "top": 471,
            "right": 2042,
            "bottom": 555,
            "width": 244,
            "height": 84
          },
          "corner_radius": 42,
          "perspective": null
        }
      ]
    }
  ]
}
```

## Fields

- **`version`** — schema version. Currently `1`. Breaking changes bump this.
- **`product`** — short identifier (used for layer naming in the PSD).
- **`canvas`** — render canvas size. Should match every pass.
- **`passes`** — paths relative to the manifest's own folder. `body` and
  `shadow` are required; `reflections` and `screen_mask` are optional.
  `screen_mask` is only needed when the consumer wants to fall back to
  pixel-derived geometry instead of the vector geometry in `editable_regions`.
- **`editable_regions`** — array of interactive areas the user can swap a
  design into. Phones have one (Screen). Laptops have two (Screen + Keyboard).
  Bottles have one (Label). Each entry:
    - **`name`** — layer name used for the smart-object placeholder in the PSD.
    - **`bounds`** — pixel rectangle in canvas coordinates (top-left origin).
    - **`corner_radius`** — pixels, or `null` for a sharp rectangle.
    - **`perspective`** — future: 4-point warp for off-axis surfaces. `null` in v1.
    - **`cutouts`** — optional array of nested regions (same shape) that the
      consumer should subtract from this region's mask. Use for dynamic islands,
      camera notches, speaker grilles, etc. Each cutout uses the same field set
      as a top-level region.

## Future fields (not yet implemented)

- **`lighting`** — separate `key`, `fill`, `rim` passes for relighting in Photoshop.
- **`id_mask`** — per-material IDs for targeted color grading.
- **`exr`** — the 32-bit float pass for advanced re-grading workflows.

## How justthreed writes it

Call the `export_mockup_manifest` tool. It projects each editable region
object's bounding box through the active camera and writes pixel-space
geometry. Two ways to declare regions:

1. **Auto-discovery** — set custom property `editable_region = True` on the
   screen object, and `editable_region_cutout = True` on cutout children
   (e.g. the dynamic island). Optionally set `corner_radius_px` on either.
2. **Explicit** — pass a `regions` argument listing object names + cutouts.

If no manifest is present, justtwod falls back to measuring the `screen_mask`
PNG — slower, less accurate, and requires the (otherwise unnecessary) mask
render pass.
