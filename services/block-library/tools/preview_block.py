"""DEV TOOL (not part of the released app): renders the block with sample data in a phone-width page and screenshots it with headless Edge/Chrome,
so the look can be checked without opening Shopify. Needs the venv (python-liquid): .work/.venv/Scripts/python
usage (from services/block-library): python tools/preview_block.py testimonials|shade-picker|<any block id> OUT.png [setting=value ...]
Sample content is made up for the preview only."""
import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools"))
import test_generated_blocks as tg  # noqa: E402
from liquid import DictLoader, Environment  # noqa: E402

block, out = sys.argv[1], Path(sys.argv[2]).resolve()
extra = dict(a.split("=", 1) for a in sys.argv[3:])
COLOURS = ["#e8c14a", "#b5506b", "#4a7fb5", "#5fa37a"]


def swatch(n, text=""):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect width="200" height="200" fill="{COLOURS[n % 4]}"/><circle cx="100" cy="80" r="40" fill="#fff" opacity=".5"/></svg>'
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


m = next(x for x in tg.generated() if x["id"] == block)
settings = dict(tg.defaults(m))
product = None
if block == "testimonials":
    settings.update({
        "quote_1": "I have been using this for three weeks and my routine feels easier. The finish is lovely and it arrived quickly.",
        "name_1": "Priya", "location_1": "Surat", "rating_1": "5", "badge_1": "Repeat customer", "image_1": swatch(1),
        "quote_2": "Good quality, simple to use.", "name_2": "Rahul", "location_2": "Pune", "rating_2": "4",
        "show_progress": True})
elif block == "shade-picker":
    settings["products"] = [
        {"handle": "a", "title": "Rose", "url": "/products/a", "featured_media": swatch(1), "selected_or_first_available_variant": {"available": True}},
        {"handle": "b", "title": "Sand", "url": "/products/b", "featured_media": swatch(0), "selected_or_first_available_variant": {"available": True}},
        {"handle": "c", "title": "Sky", "url": "/products/c", "featured_media": swatch(2), "selected_or_first_available_variant": {"available": False}},
        {"handle": "d", "title": "Mint", "url": "/products/d", "featured_media": swatch(3), "selected_or_first_available_variant": {"available": True}}]
    product = {"handle": "b"}
else:
    settings.update(m["test"]["sample"])  # any other block: its own test sample
    product = m["test"].get("product")
def picture(n, ratio):
    """A placeholder picture object with a chosen shape (width / height), like Shopify's image object."""
    h = 200
    w = round(h * ratio)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"><rect width="{w}" height="{h}" fill="{COLOURS[n % 4]}"/><circle cx="{w // 2}" cy="{h // 2}" r="{min(w, h) // 4}" fill="#fff" opacity=".5"/></svg>'
    return {"src": "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode(), "aspect_ratio": ratio, "alt": "", "width": w, "height": h}


def resolve(key, value):
    if value == "SWATCH":
        return swatch(1)
    if isinstance(value, str) and value.startswith("SWATCH:"):  # "SWATCH:0.6" = a tall picture, "SWATCH:1.8" = a wide one
        return picture(int(key.rsplit("_", 1)[-1]) if key.rsplit("_", 1)[-1].isdigit() else 1, float(value.split(":")[1]))
    return value


settings.update({k: resolve(k, v) for k, v in extra.items()})
if os.environ.get("PREVIEW_AUTO_IMAGES", "1") != "0":  # numbered items get a placeholder picture unless one was given (set PREVIEW_AUTO_IMAGES=0 to skip)
    for n in range(1, 13):
        if any(settings.get(f"{p}_{n}") for p in ("name", "text", "number", "description")):
            for picture in (f"image_{n}", f"photo_{n}"):
                if picture in settings and not settings[picture]:
                    settings[picture] = swatch(n)

env = Environment(loader=DictLoader({p.stem: p.read_text(encoding="utf-8") for p in tg.SNIPPETS.glob("*.liquid")}))
env.add_filter("image_url", lambda value, **kw: value["src"] if isinstance(value, dict) else value)  # a picture object or a plain URL
env.add_filter("json", lambda v: json.dumps(v, default=str))
env.add_filter("money", lambda v: f"Rs. {int(v) / 100:,.2f}" if block == "price" else f"Rs. {v}")
env.add_filter("money_without_trailing_zeros", lambda v: f"Rs. {int(v) / 100:,.0f}" if block == "price" else f"Rs. {v}")
template = env.from_string(tg.cl.strip_schema(tg.block_text(m)), globals={"request": {"design_mode": False}})
ctx = {"app": {"metafields": {"dtj": {"licence": {"value": "active"}}}}, "block": {"settings": settings, "shopify_attributes": ""}}
if product:
    ctx["product"] = product
html = re.sub(r"<!--.*?-->", "", template.render(**ctx), flags=re.S)
assets = tg.cl.ext_of(tg.ROOT) / "assets"  # works for either app (set DTJ_APP_ROOT for the second one)
import os  # noqa: E402

W = int(os.environ.get("PREVIEW_WIDTH", "390"))
H = int(os.environ.get("PREVIEW_HEIGHT", "420"))
css = (assets / f"dtj-{block}.css").read_text(encoding="utf-8")
js_path = assets / f"dtj-{block}.js"
js = js_path.read_text(encoding="utf-8") if js_path.exists() else ""
# PREVIEW_THEME=1: render inside the real Horizon wrapper (flex column, app block wrapper) with the theme's own stylesheet loaded
THEME = os.environ.get("PREVIEW_THEME", "0") == "1"
theme_css = ""
if THEME:
    theme_css = (Path(__file__).resolve().parents[3] / ".work" / "master-packs" / "assets" / "base.css").read_text(encoding="utf-8")
    html = ('<div class="layout-panel-flex layout-panel-flex--column section-content-wrapper mobile-column" '
            'style="--horizontal-alignment:center;--vertical-alignment:flex-start;--gap:20px;--flex-wrap:nowrap;--flex-direction:column">'
            '<div class="shopify-block shopify-app-block">' + html + '</div></div>')
doc = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>{theme_css}</style><style>html{{color-scheme:light}}body{{margin:0;padding:16px;width:{W - 32}px;background:#fff;color:#121212;font:14px/1.4 Inter,"Segoe UI",system-ui,sans-serif}}
img{{max-width:100%}}*{{transition:none!important;animation:none!important}}</style><style>{css}</style></head>
<body>{html}<script>{js}</script></body></html>"""
import html as htmllib  # noqa: E402

hp = out.with_suffix(".html")
hp.write_text(doc, encoding="utf-8")  # the plain page (used by preview_measure.py)
# Headless Edge never goes below ~496px wide, so a phone is simulated with an iframe of the true width:
# media queries inside an iframe are evaluated against the iframe's own width.
frame = out.with_name(out.stem + "-frame.html")
frame.write_text(f'<!doctype html><body style="margin:0;background:#fff"><iframe srcdoc="{htmllib.escape(doc, quote=True)}" '
                 f'style="width:{W}px;height:{H}px;border:0;display:block"></iframe></body>', encoding="utf-8")
edge = next(p for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe") if Path(p).is_file())
subprocess.run([edge, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2", f"--window-size={max(W, 500)},{H}",
                f"--screenshot={out}", "--virtual-time-budget=2000", frame.as_uri()], check=True, capture_output=True, timeout=90)
print("wrote", out)
