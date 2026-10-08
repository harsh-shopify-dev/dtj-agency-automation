"""Block builder: manifest + body + stylesheet -> the app block file Shopify serves.

    python tools/build_blocks.py            write generated files
    python tools/build_blocks.py --check    fail if a generated file differs from what the sources produce

Sources per block `<id>` (only manifests that have a `settings` list are built):
    manifests/<id>.json      settings (content + block-specific), standard_controls, standard_defaults, test sample
    src/<id>.liquid          body: builds the visible HTML only. It must NOT contain the licence gate or the schema.
    src/<id>.css             block styles (colours come from CSS variables, never hex)
    src/_<name>.css          optional shared fragments, listed in the manifest as css_includes
Output:
    extensions/dtj-blocks/blocks/dtj-<id>.liquid     prelude + body wrapped in the licence gate + generated {% schema %}
    extensions/dtj-blocks/assets/dtj-<id>.css        shared base styles + block styles

Every block gets the same standard controls, so no block ships with missing settings.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

TOOLS_HOME = Path(__file__).resolve().parents[1]  # the folder these shared tools live in (services/block-library)


def extension_dir(root: Path) -> Path:
    """The app's single theme extension folder (one extension per app), e.g. extensions/dtj-blocks."""
    found = [p for p in (root / "extensions").iterdir() if p.is_dir()] if (root / "extensions").is_dir() else []
    if len(found) != 1:
        raise SystemExit(f"{root}: expected exactly one folder under extensions/, found {[p.name for p in found]}")
    return found[0]


def use_root(root: Path) -> None:
    """Point the builder at an app folder. Default = the first app; the second app sets DTJ_APP_ROOT or passes --root."""
    global ROOT, BLOCKS, ASSETS
    ROOT = Path(root).resolve()
    BLOCKS = extension_dir(ROOT) / "blocks"
    ASSETS = extension_dir(ROOT) / "assets"


use_root(os.environ.get("DTJ_APP_ROOT") or TOOLS_HOME)

# ---- standard controls (single definition, used by every generated block) ----

def _range(id_, label, lo, hi, step, default, unit="px"):
    return {"type": "range", "id": id_, "label": label, "min": lo, "max": hi, "step": step, "unit": unit, "default": default}


def standard_controls(defaults: dict) -> dict:
    d = lambda key, fallback: defaults.get(key, fallback)  # noqa: E731
    return {
        "spacing": [
            _range("padding_top", "Top padding", 0, 100, 2, d("padding_top", 0)),
            _range("padding_bottom", "Bottom padding", 0, 100, 2, d("padding_bottom", 0)),
            _range("padding_left", "Left padding", 0, 100, 2, d("padding_left", 0)),
            _range("padding_right", "Right padding", 0, 100, 2, d("padding_right", 0)),
            _range("margin_top", "Top margin", -40, 100, 2, d("margin_top", 0)),
            _range("margin_bottom", "Bottom margin", -40, 100, 2, d("margin_bottom", 0)),
        ],
        # top and bottom padding only: the section already controls the sides, and every setting costs bytes (100 KB cap) and one of 75 slots
        "spacing_v": [
            _range("padding_top", "Top padding", 0, 100, 2, d("padding_top", 0)),
            _range("padding_bottom", "Bottom padding", 0, 100, 2, d("padding_bottom", 0)),
        ],
        # side space: keeps a full-width section off the screen edges (a phone needs ~16 px); uses the same left/right variables as `spacing`
        "gutter": [
            _range("side_padding", "Side space", 0, 64, 2, d("side_padding", 16)),
        ],
        "align": [
            {"type": "select", "id": "align", "label": "Alignment", "default": d("align", "start"),
             "options": [{"value": "start", "label": "Left"}, {"value": "center", "label": "Center"}, {"value": "end", "label": "Right"}]},
        ],
        "colors": [
            {"type": "color", "id": "text_color", "label": "Text color", "info": "Empty = follows the theme."},
            {"type": "color", "id": "background", "label": "Background color", "info": "Empty = the block's neutral default."},
        ],
        "shape": [_range("corner_radius", "Corner radius", 0, 40, 2, d("corner_radius", 0))],
        "text_size": [_range("text_size", "Text size", 10, 40, 1, d("text_size", 14))],
    }


# Liquid that turns the standard settings into CSS custom properties (only for the controls a block uses).
PRELUDE = {
    "spacing": ("--dtj-pad-top: {{ bs.padding_top | default: 0 }}px; --dtj-pad-bottom: {{ bs.padding_bottom | default: 0 }}px; "
                "--dtj-pad-left: {{ bs.padding_left | default: 0 }}px; --dtj-pad-right: {{ bs.padding_right | default: 0 }}px; "
                "--dtj-margin-top: {{ bs.margin_top | default: 0 }}px; --dtj-margin-bottom: {{ bs.margin_bottom | default: 0 }}px;"),
    "spacing_v": "--dtj-pad-top: {{ bs.padding_top | default: 0 }}px; --dtj-pad-bottom: {{ bs.padding_bottom | default: 0 }}px;",
    "gutter": "--dtj-pad-left: {{ bs.side_padding | default: 16 }}px; --dtj-pad-right: {{ bs.side_padding | default: 16 }}px;",
    "align": ("--dtj-align: {{ bs.align | default: 'start' }}; "
              "--dtj-justify: {% case bs.align %}{% when 'center' %}center{% when 'end' %}flex-end{% else %}flex-start{% endcase %};"),
    "colors": ("{% if bs.text_color != blank %}--dtj-text-color: {{ bs.text_color }};{% endif %} "
               "{% if bs.background != blank %}--dtj-background: {{ bs.background }};{% endif %}"),
    "shape": "--dtj-radius: {{ bs.corner_radius | default: 0 }}px;",
    "text_size": "--dtj-text-size: {{ bs.text_size | default: 14 }}px;",
}

BASE_CSS = """/* GENERATED by tools/build_blocks.py: shared base. Do not edit. */
.dtj-b {
  box-sizing: border-box;
  /* never wider than the container, whatever a merchant types: a long unbroken word must wrap, not stretch the page (6 Oct 2026) */
  min-width: 0;
  max-width: 100%;
  margin: var(--dtj-margin-top, 0) 0 var(--dtj-margin-bottom, 0);
  padding: var(--dtj-pad-top, 0) var(--dtj-pad-right, 0) var(--dtj-pad-bottom, 0) var(--dtj-pad-left, 0);
  text-align: var(--dtj-align, start);
  font-size: var(--dtj-text-size, inherit);
}

/* A long unbroken word must wrap, not stretch the page. It is set on EVERY element inside the block, not just the block: themes set
   `overflow-wrap: break-word` straight on p and h1-h6 (Horizon does), which beats an inherited value, and `break-word` (unlike `anywhere`)
   does not shrink the minimum width, so one long word made the whole block wider than the screen (6 Oct 2026). */
.dtj-b,
.dtj-b * {
  overflow-wrap: anywhere;
}

/* Horizon wraps every app block in <div class="shopify-block">, and inside its flex column that wrapper is only as wide as its content wants
   to be: a slider row or a marquee strip made it far wider than the screen. Make the wrapper fill the space instead. */
.shopify-block:has(> .dtj-b) {
  width: 100%;
  max-width: 100%;
  min-width: 0;
}
"""

GATE = ("{%- render 'dtj-licence', value: app.metafields.dtj.licence.value, content: dtj_content, "
        "design_mode: request.design_mode, attributes: block.shopify_attributes -%}")


def build_one(manifest: dict, body: str, css: str, shared_css: str = "") -> tuple[str, str]:
    controls = manifest.get("standard_controls", [])
    available = standard_controls(manifest.get("standard_defaults", {}))
    unknown = [c for c in controls if c not in available]
    if unknown:
        raise ValueError(f"{manifest['id']}: unknown standard controls {unknown}")
    if "{% schema" in body or "render 'dtj-licence'" in body:
        raise ValueError(f"{manifest['id']}: the body must not contain the schema or the licence gate; the builder adds them")

    settings = list(manifest["settings"])
    standard = [setting for c in controls for setting in available[c]]
    ids = [x["id"] for x in settings + standard if "id" in x]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{manifest['id']}: duplicate setting ids between the block and the standard controls")
    if standard:
        settings = settings + [{"type": "header", "content": "Style and spacing"}] + standard

    prelude = " ".join(PRELUDE[c] for c in controls)
    schema = {"name": manifest["title"], "target": "section", "stylesheet": f"dtj-{manifest['id']}.css", "settings": settings}
    if manifest.get("script"):
        schema["javascript"] = f"dtj-{manifest['id']}.js"  # served from the extension's assets, loaded once when the block is on the page
    block = (
        f"{{%- comment -%}} GENERATED by tools/build_blocks.py from manifests/{manifest['id']}.json and src/{manifest['id']}.liquid. "
        "Do not edit this file. {%- endcomment -%}\n"
        # `bs` is the block's settings under a short name: Shopify counts every byte of Liquid (100 KB cap per app) and the long
        # prefix was repeated hundreds of times (about 5 KB per app)
        "{%- assign bs = block.settings -%}\n"
        f"{{%- capture dtj_std_style -%}}{prelude}{{%- endcapture -%}}\n"
        "{%- capture dtj_content -%}\n" + body.strip("\n") + "\n{%- endcapture -%}\n\n"
        # compact JSON: Shopify counts every byte of Liquid (100 KB cap per app), and pretty-printing cost about 18 KB
        + GATE + "\n\n{% schema %}\n" + json.dumps(schema, separators=(",", ":"), ensure_ascii=False) + "\n{% endschema %}\n"
    )
    shared = (shared_css.strip("\n") + "\n\n") if shared_css else ""
    return block, BASE_CSS + "\n" + shared + css.strip("\n") + "\n"


def targets() -> list[tuple[Path, str]]:
    """(path, expected text) for every generated file."""
    result = []
    for manifest_path in sorted((ROOT / "manifests").glob("*.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if "settings" not in manifest:
            continue
        shared = "\n\n".join((ROOT / "src" / f"_{name}.css").read_text(encoding="utf-8") for name in manifest.get("css_includes", []))
        block, css = build_one(manifest, (ROOT / "src" / f"{manifest['id']}.liquid").read_text(encoding="utf-8"),
                               (ROOT / "src" / f"{manifest['id']}.css").read_text(encoding="utf-8"), shared)
        result += [(BLOCKS / f"dtj-{manifest['id']}.liquid", block), (ASSETS / f"dtj-{manifest['id']}.css", css)]
        if manifest.get("script"):
            script = (ROOT / "src" / f"{manifest['id']}.js").read_text(encoding="utf-8")
            result.append((ASSETS / f"dtj-{manifest['id']}.js", script))
    return result


def main(argv: list[str]) -> int:
    if "--root" in argv:
        use_root(Path(argv[argv.index("--root") + 1]))
    check = "--check" in argv
    stale = []
    for path, text in targets():
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if current != text:
            stale.append(path.name)
            if not check:
                path.write_text(text, encoding="utf-8", newline="\n")
    if check and stale:
        print("STALE (run tools/build_blocks.py):", ", ".join(stale))
        return 1
    print(("up to date" if check else f"wrote {len(stale)} changed file(s)") + f" ({len(targets())} generated)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
