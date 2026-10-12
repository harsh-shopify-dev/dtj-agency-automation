"""DEV TOOL (not part of the released app). Needs the venv (python-liquid): .work/.venv/Scripts/python
Render a master-theme PACK SECTION (the original design) with its own default settings, so it can be compared with our app block.
usage: python render_pack_section.py SECTION_FILE OUT.png [width] [height]
Approximations: python-liquid, stubbed shopify filters, theme CSS variables guessed (font, colours). Layout and card design are the section's own.
"""
import base64
import html as htmllib
import json
import re
import subprocess
import sys
from pathlib import Path

from liquid import DictLoader, Environment

PACK = Path(__file__).resolve().parents[3] / ".work" / "master-packs"
src_path, out = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
W = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
H = int(sys.argv[4]) if len(sys.argv) > 4 else 700

text = src_path.read_text(encoding="utf-8")
m = re.search(r"\{%-?\s*schema\s*-?%\}(.*?)\{%-?\s*endschema\s*-?%\}", text, re.S)
schema = json.loads(m.group(1))
text = text.replace(m.group(0), "")
text = re.sub(r"alt:\s*block\.settings\.image_alt\s*\|\s*default:\s*block\.settings\.stat_number,", "alt: block.settings.stat_number,", text)
for tag in ("style", "stylesheet", "javascript"):
    text = re.sub(r"\{%-?\s*" + tag + r"\s*-?%\}", "<style>" if tag != "javascript" else "<script>", text)
    text = re.sub(r"\{%-?\s*end" + tag + r"\s*-?%\}", "</style>" if tag != "javascript" else "</script>", text)

COLORS = ["#e8c14a", "#b5506b", "#4a7fb5", "#5fa37a"]


def swatch(n):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect width="200" height="200" fill="{COLORS[n % 4]}"/><circle cx="100" cy="80" r="40" fill="#fff" opacity=".5"/></svg>'
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


class Img(dict):
    """A stand-in image object: truthy, has width/height, and prints as its URL."""
    def __str__(self):
        return self["src"]


def default_for(setting, n=1):
    t = setting.get("type")
    if t in ("header", "paragraph"):
        return None
    if t == "image_picker":
        return Img(src=swatch(n), width=200, height=200, alt="", aspect_ratio=1.0)
    if t == "font_picker":
        return {"family": "Helvetica, Arial, sans-serif", "style": "normal", "weight": 400, "fallback_families": "sans-serif", "baseline_ratio": 1}
    if "default" in setting:
        return setting["default"]
    return ""


def settings_of(items, n=1):
    return {s["id"]: default_for(s, n) for s in items if "id" in s}


section_settings = settings_of(schema.get("settings", []))
block_defs = {b["type"]: b for b in schema.get("blocks", [])}
preset = (schema.get("presets") or [{}])[0].get("blocks") or [{"type": t} for t in list(block_defs)[:1] * 4]
blocks = []
for n, pb in enumerate(preset, 1):
    bd = block_defs.get(pb["type"], {"settings": []})
    st = settings_of(bd.get("settings", []), n)
    st.update(pb.get("settings", {}))
    blocks.append({"type": pb["type"], "id": f"b{n}", "settings": st, "shopify_attributes": ""})
# a few sample slides if the preset has none
if not blocks and block_defs:
    t = next(iter(block_defs))
    for n in range(1, 5):
        blocks.append({"type": t, "id": f"b{n}", "settings": settings_of(block_defs[t]["settings"], n), "shopify_attributes": ""})

env = Environment(loader=DictLoader({}))
env.add_filter("image_url", lambda v, **kw: str(v))
env.add_filter("image_tag", lambda v, **kw: f'<img src="{v}" alt="{kw.get("alt", "")}" class="{kw.get("class", "")}" width="{kw.get("width", 100)}" height="{kw.get("height", 100)}">')
env.add_filter("asset_url", lambda v: "")
env.add_filter("font_face", lambda v, **kw: "")
env.add_filter("font_url", lambda v, *a: "")
env.add_filter("font_modify", lambda v, *a: v)
env.add_filter("json", lambda v: json.dumps(v, default=str))
env.add_filter("money", lambda v: f"Rs. {v}")
env.add_filter("t", lambda v, **kw: str(v).split(".")[-1])
env.add_filter("color_modify", lambda v, *a: v)
env.add_filter("color_to_rgb", lambda v: v)
env.add_filter("brightness_difference", lambda v, *a: 40)
env.add_filter("stylesheet_tag", lambda v: "")
env.add_filter("script_tag", lambda v: "")
env.add_filter("placeholder_svg_tag", lambda v, *a: f'<svg class="ph"></svg>')

import os
section_settings.update(json.loads(os.environ.get("PACK_SET", "{}")))
if os.environ.get("PACK_BLOCKS"):
    bt = next(iter(block_defs))
    blocks = []
    for n, extra in enumerate(json.loads(os.environ["PACK_BLOCKS"]), 1):
        st = settings_of(block_defs[bt]["settings"], n)
        st.update({k: (Img(src=swatch(n), width=200, height=250, alt="", aspect_ratio=0.8) if v == "IMG" else v) for k, v in extra.items()})
        blocks.append({"type": bt, "id": f"b{n}", "settings": st, "shopify_attributes": ""})
section = {"id": "pack1", "settings": section_settings, "blocks": blocks, "index": 1, "location": "template", "shopify_attributes": ""}
try:
    body = env.from_string(text, globals={"request": {"design_mode": False}}).render(section=section, settings={}, shop={"money_format": "Rs. {{amount}}"}, product={})
except Exception as exc:  # noqa: BLE001
    print("RENDER ERROR:", repr(exc)[:400])
    raise
js_path = PACK / "assets" / (src_path.stem + ".js")
body = re.sub(r"<script[^>]*src=\"\"[^>]*></script>", "<script>" + (js_path.read_text(encoding="utf-8") if js_path.exists() else "") + "</script>", body)

page = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>html{{color-scheme:light}}body{{margin:0;background:#fff;color:#121212;font:14px/1.4 Inter,"Segoe UI",system-ui,sans-serif;
--font-heading--family:Inter,"Segoe UI",system-ui,sans-serif;--font-body--family:Inter,"Segoe UI",system-ui,sans-serif;--font-paragraph--family:Inter,"Segoe UI",system-ui,sans-serif}}
*{{transition:none!important}}</style></head><body>{body}</body></html>"""
html_path = out.with_suffix(".html")
html_path.write_text(page, encoding="utf-8")
frame = out.with_name(out.stem + "-frame.html")
frame.write_text(f'<!doctype html><body style="margin:0;background:#fff"><iframe srcdoc="{htmllib.escape(page, quote=True)}" style="width:{W}px;height:{H}px;border:0;display:block"></iframe></body>', encoding="utf-8")
edge = next(p for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe") if Path(p).is_file())
subprocess.run([edge, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1", f"--window-size={max(W, 500)},{H}",
                f"--screenshot={out}", "--virtual-time-budget=3000", frame.as_uri()], check=True, capture_output=True, timeout=120)
print("wrote", out, "| blocks:", len(blocks), "| html bytes:", len(body))
