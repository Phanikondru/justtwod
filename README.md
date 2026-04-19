# justtwod

> **Note:** Unofficial, independent project. Not affiliated with or endorsed by Adobe Inc.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-macOS-lightgrey.svg)]()
[![Tools](https://img.shields.io/badge/Tools-74-success.svg)]()
[![MCP](https://img.shields.io/badge/Protocol-MCP-purple.svg)](https://modelcontextprotocol.io/)

**Control Adobe Photoshop with natural language.** An MCP server that exposes
74 Photoshop operations — documents, layers, smart objects, text, shapes,
selections, masks, transforms, adjustments, filters, canvas, history, and a
flagship `build_product_mockup` tool — to any MCP-capable AI client.

> **🎨 74 Tools** | **🖼️ Smart-Object Mockups** | **🎯 Blender→PSD Pipeline** | **✂️ Clipping Masks** | **⏮️ Undo / Redo** | **🧩 ExtendScript Escape Hatch**

Companion to [`justthreed`](https://github.com/Phanikondru/justthreed).
Where `justthreed` is *just 3D* (Blender), `justtwod` is *just 2D* (Photoshop).
Together they form a 3D-to-deliverable pipeline: model and render in Blender,
composite and mock up in Photoshop, all driven by natural language.

## Features

- ✅ **74 curated tools** covering the whole compositing pipeline
- ✅ **Flagship `build_product_mockup`** — render folder → layered PSD with a smart-object placeholder
- ✅ **Deep smart-object support** — place, create, replace contents, edit contents, reset transforms
- ✅ **Full mask suite** — layer masks, clipping masks, apply / delete
- ✅ **History control** — undo, redo, inspect history stack with step counts
- ✅ **Selection primitives** — rect, ellipse, feather, expand, contract, invert, load from layer
- ✅ **Structured responses** — every tool returns `{ok, result | error}`, not loose strings
- ✅ **Photoshop auto-detection** — override with `JUSTTWOD_PHOTOSHOP_APP` if needed
- ✅ **ExtendScript escape hatch** — `execute_jsx` for anything not yet wrapped
- ✅ **JSON polyfill built in** — ExtendScript lacks native JSON; we inject one
- ✅ **Pairs with `justthreed`** via the `mockup_manifest.json` schema
- ✅ **Python + FastMCP** — `uv sync` and go

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

### Claude Code / Claude Desktop

Add to `~/.claude.json` (or `~/Library/Application Support/Claude/claude_desktop_config.json` for Claude Desktop):

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

### Cursor

Add to `.cursor/config.json` or your workspace settings:

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

### Environment variables

- `JUSTTWOD_PHOTOSHOP_APP` *(optional)* — path or app name override if auto-detection misses your install (e.g. `"Adobe Photoshop 2026"`).

## The 74 tools

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
| **History** | `undo`, `redo`, `get_history_states` |
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

## Example prompts

Paste these into Claude / Cursor once justtwod is configured:

<details>
<summary>🎨 Build a product mockup from Blender renders</summary>

```
Run build_product_mockup on ~/Desktop/phone_shoot/renders and save the PSD
to ~/Desktop/phone_mockup.psd. Use the mockup_manifest.json in that folder
if present.
```

</details>

<details>
<summary>🖼️ Drop a Figma export into an existing mockup</summary>

```
Open ~/Desktop/phone_mockup.psd. Replace the contents of the "Your Design"
smart object with ~/Desktop/figma-export.png. Save and export a 2x PNG
next to the PSD.
```

</details>

<details>
<summary>✂️ Mask a product photo to a shape</summary>

```
Open ~/Desktop/hero.jpg. Create a rounded-rectangle shape layer at
(200, 200) sized 1200x800 with a 48px corner radius. Use it as a clipping
mask on the photo layer. Flatten and save as hero-rounded.psd.
```

</details>

<details>
<summary>📝 Text poster design</summary>

```
Create a 1080x1350 RGB document at 300dpi. Fill the background layer
with #7828C8. Add centered "SUMMER" in 96pt white at (540, 300), and
"2026" at 128pt white at (540, 450). Apply a 2px Gaussian blur to the
background. Save as summer-poster.psd.
```

</details>

<details>
<summary>🎭 Layered composite with blend modes</summary>

```
Create a 1920x1080 RGB document. Place ~/Desktop/sky.jpg as a smart
object fitted to the canvas. Duplicate it, set the copy to Soft Light
at 60% opacity. Add a text layer "WANDER" in 200pt white, centered.
Group the text and top layer as "Overlay". Save as wander.psd.
```

</details>

<details>
<summary>⏮️ Undo an experiment</summary>

```
Apply a 30px Gaussian blur to the active layer.
Actually, that's too much — undo the last step and apply 8px instead.
Show me the history states afterwards.
```

</details>

<details>
<summary>🧩 Escape-hatch: arbitrary ExtendScript</summary>

```
Run execute_jsx with this code:
  app.activeDocument.suspendHistory("Batch rename", "for (var i = 0; i < app.activeDocument.layers.length; i++) { app.activeDocument.layers[i].name = 'Layer_' + (i+1); }");
```

</details>

## Quick-start prompt table

| Task | Prompt |
|---|---|
| **Product mockup** | "Build a mockup PSD from the renders in `~/Desktop/phone_shoot`." |
| **Swap design** | "Replace the smart object 'Your Design' with `~/Desktop/figma-export.png`." |
| **New document** | "Create a 1920x1080 RGB document at 72dpi named 'hero'." |
| **Rounded crop** | "Mask the top layer with a rounded-rectangle clipping mask at (100,100)–(900,600), 40px radius." |
| **Color grade** | "Apply levels with black point 15, white point 240, gamma 1.1 to the active layer." |
| **Text styling** | "Change the 'Title' text to Helvetica Neue 72pt, color white, center aligned." |
| **Undo** | "Undo the last 3 steps and show me the history stack." |
| **Export** | "Save a 2x PNG and a quality-10 JPEG next to the open PSD." |

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

## Troubleshooting

**"Could not find Adobe Photoshop"** — set `JUSTTWOD_PHOTOSHOP_APP` to the exact application name, e.g.:

```json
{ "env": { "JUSTTWOD_PHOTOSHOP_APP": "Adobe Photoshop 2026" } }
```

**`ping` hangs or times out** — make sure Photoshop is running and has at least one window open. macOS may prompt for Automation permission the first time (System Settings → Privacy & Security → Automation); allow it for your terminal / MCP client.

**Tool call fails with "No document is open"** — most tools require an active document. Start with `new_document` or `open_file` first.

**Something I want isn't wrapped yet** — use `execute_jsx(code)` to run raw ExtendScript, then [open an issue](https://github.com/Phanikondru/justtwod/issues) so we can add a proper tool.

## Status

v0.1 — scaffolding + 74 tools + one flagship composition. Production-usable
for the mockup workflow today. Next up: `justthreed` writes manifests,
justtwod consumes them; vector shapes; Windows support.

## Contributing

PRs welcome — especially for:
- Windows transport (COM automation counterpart to `osascript`)
- Action playback + custom-action recording tools
- Vector path shapes and pen-tool primitives
- Additional adjustment layers (curves, selective color, gradient map)

Open an issue first for anything larger than a one-file change.

## License

MIT

## Acknowledgments

- Built on [FastMCP](https://github.com/jlowin/fastmcp) and the [Model Context Protocol](https://modelcontextprotocol.io/)
