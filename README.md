# justtwod

**Control Adobe Photoshop with natural language.** An MCP server that exposes
71 Photoshop operations — documents, layers, smart objects, text, shapes,
selections, masks, transforms, adjustments, filters, canvas, and a flagship
`build_product_mockup` tool — to any MCP-capable AI client.

Companion to [`justthreed`](https://github.com/Phanikondru/justthreed).
Where `justthreed` is *just 3D* (Blender), `justtwod` is *just 2D* (Photoshop).
Together they form a 3D-to-deliverable pipeline: model and render in Blender,
composite and mock up in Photoshop, all driven by natural language.

## Why

Designers spend hours repeating the same Photoshop steps: open renders, stack
passes with the right blend modes, set up a smart object at the screen region
with the right corner radius, add a background, export. `justtwod` lets an AI
do it in one sentence:

> "Build a mockup PSD from the renders in `~/Desktop/phone_shoot`, save it to
> `~/Desktop/phone_mockup.psd`."

The user gets a clean, layered PSD with a "Your Design" smart-object
placeholder. They double-click, drop in a Figma export, save → finished
marketing asset.

## Requirements

- macOS (Windows support planned)
- Adobe Photoshop 2022 or newer (auto-detected; override with `JUSTTWOD_PHOTOSHOP_APP`)
- Python 3.11+

## Install

```bash
git clone https://github.com/Phanikondru/justtwod.git
cd justtwod/mcp_server
uv sync
```

Smoke-test that the server reaches Photoshop:

```bash
uv run justtwod-ping
# [justtwod] Using Adobe Photoshop 2026
# [justtwod] pong from Adobe Photoshop 27.5.0
# OK
```

## Configure your MCP client

Add to `~/.claude.json` (or the equivalent for your client):

```json
{
  "mcpServers": {
    "justtwod": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/justtwod/mcp_server", "justtwod"]
    }
  }
}
```

## The 71 tools

| Category | Tools |
|---|---|
| **Core** | `ping`, `execute_jsx` |
| **Documents** | `new_document`, `open_file`, `save`, `save_as`, `close_document`, `export_as` |
| **Inspection** | `get_document_info`, `list_documents`, `list_layers`, `get_layer_info` |
| **Layers** | `create_layer`, `duplicate_layer`, `delete_layer`, `rename_layer`, `group_layers`, `set_layer_blend_mode`, `set_layer_opacity`, `set_layer_visibility`, `reorder_layer` |
| **Smart Objects** | `place_as_smart_object`, `create_smart_object`, `replace_contents`, `edit_contents`, `reset_smart_object_transforms` |
| **Text** | `create_text_layer`, `create_paragraph_text`, `set_text_content`, `set_font`, `set_text_size`, `set_text_color`, `set_text_alignment` |
| **Shapes** | `create_rectangle`, `create_rounded_rectangle`, `create_ellipse`, `fill_layer_with_color` |
| **Selection** | `select_all`, `deselect`, `select_rectangle`, `select_ellipse`, `invert_selection`, `feather_selection`, `expand_selection`, `contract_selection`, `load_selection_from_layer` |
| **Masks** | `add_layer_mask`, `apply_mask`, `delete_mask`, `create_clipping_mask`, `release_clipping_mask` |
| **Transforms** | `move_layer`, `move_layer_to`, `scale_layer`, `rotate_layer`, `flip_layer` |
| **Adjustments** | `apply_levels`, `apply_brightness_contrast`, `apply_hue_saturation`, `apply_color_balance` |
| **Filters** | `gaussian_blur`, `motion_blur`, `sharpen`, `add_noise` |
| **Canvas** | `resize_canvas`, `crop`, `rotate_canvas`, `trim_transparent`, `flatten_image`, `merge_visible` |
| **Compositions** | `build_product_mockup` |

Every tool is documented via its docstring, which the MCP client surfaces to
the AI as part of the tool schema. Anything not yet covered by a curated tool
is reachable via `execute_jsx(code)` — the escape hatch that runs arbitrary
ExtendScript.

## The flagship: `build_product_mockup`

This is what justtwod was originally built for. Takes a folder of Blender
render passes and produces a clean, layered PSD with a smart-object
placeholder sized to the product's editable region.

```
renders/
├── phone_body_0001.tif       # required — the hero pass
├── phone_shadow_0001.png     # required — contact shadow (Multiply blend)
├── phone_reflections_0001.png # optional — specular highlights (Screen @ 40%)
├── screen_mask_0001.png      # required — white mask for the editable region
└── mockup_manifest.json      # optional — explicit canvas size + region bounds
```

Natural-language call:

> "Run `build_product_mockup` on `~/Desktop/phone_shoot/renders`, save to
> `~/Desktop/phone_mockup.psd`."

Result: a PSD with layers stacked top-to-bottom as
`Screen Mask (hidden)` → `Your Design (smart object)` → `Reflections` →
`Phone Body` → `Shadow`. The "Your Design" layer is a smart object sized and
rounded to match the phone's screen — double-click it, drop in your Figma
export, save, done.

See [MANIFEST.md](MANIFEST.md) for the `mockup_manifest.json` schema that
`justthreed` will produce automatically to skip on-the-fly mask measurement.

## Architecture

```
AI client ── MCP ──▶ justtwod server (Python)
                         │
                         ▼
                    osascript + ExtendScript (.jsx)
                         │
                         ▼
                    Adobe Photoshop
```

- MCP tools live in `mcp_server/src/justtwod/tools/`, one module per category
- All tools register onto a shared FastMCP instance in `_app.py`
- The transport in `transport.py` wraps JSX with a JSON polyfill (ExtendScript
  lacks native JSON), sends it to Photoshop via `osascript`, and parses a
  structured `{ok, result | error}` envelope from the return value
- A future UXP-plugin transport will replace `osascript` for faster,
  bidirectional round-trips

## Status

v0.1 — scaffolding + 71 tools + one flagship composition. Production-usable
for the mockup workflow today. Next up: `justthreed` writes manifests,
justtwod consumes them; vector shapes; Windows support.

## License

MIT
