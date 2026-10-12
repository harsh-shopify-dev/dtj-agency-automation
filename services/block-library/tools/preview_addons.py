"""DEV TOOL (not part of the released app): renders the block with sample data in a phone-width page and screenshots it with headless Edge/Chrome,
so the look can be checked without opening Shopify. Needs the venv (python-liquid): .work/.venv/Scripts/python
usage (from services/block-library): python tools/preview_addons.py OUT.png [tick=1,2] [setting=value ...]
Sample content is made up for the preview only."""
import base64
import subprocess
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools"))
import test_generated_blocks as tg  # noqa: E402

import os  # noqa: E402

W = int(os.environ.get("PREVIEW_WIDTH", "390"))
H = int(os.environ.get("PREVIEW_HEIGHT", "640"))
out = Path(sys.argv[1]).resolve()
tick = [int(x) for x in (sys.argv[2].split("=")[1].split(",") if len(sys.argv) > 2 and sys.argv[2].startswith("tick=") else ["1"])]

COLOURS = ["#e8c14a", "#b5506b", "#4a7fb5"]


def swatch(n):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect width="200" height="200" fill="{COLOURS[n % 3]}"/><circle cx="100" cy="80" r="40" fill="#fff" opacity=".5"/></svg>'
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def prod(n, title, price, compare=None):
    media = swatch(n)
    return {"title": title, "url": f"/products/{n}", "featured_media": media,
            "variants": [{"id": n * 10, "price": price}],
            "selected_or_first_available_variant": {"id": n * 10, "price": price, "compare_at_price": compare, "available": True, "featured_media": media}}


extra = dict(a.split("=",1) for a in sys.argv[3:])
products = [prod(1, "Super Senior - Ultimate Brain WorkBook", 69900, 99900), prod(2, "girl suit", 59900), prod(3, "FROM PEN TO PUBLISHED", 29900, 100000), prod(4, "Planner Journal", 39900), prod(5, "Brain WorkBook (Hindi)", 69900, 99900)]
m = next(x for x in tg.generated() if x["id"] == "addons")
page = {"selected_or_first_available_variant": {"id": 5, "price": 99900}, "variants": [{"id": 5, "price": 99900}]}

from liquid import DictLoader, Environment  # noqa: E402
import re  # noqa: E402

env = Environment(loader=DictLoader({p.stem: p.read_text(encoding="utf-8") for p in tg.SNIPPETS.glob("*.liquid")}))
env.add_filter("image_url", lambda value, **kw: value)
env.add_filter("json", lambda v: json.dumps(v, default=str))
env.add_filter("money", lambda v: f"Rs. {int(v) / 100:,.2f}")
template = env.from_string(tg.cl.strip_schema(tg.block_text(m)), globals={"request": {"design_mode": False}})
settings = {**tg.defaults(m), "products": products, "heading": "Complete your routine", "subheading": "Add to this order in one tap", "recommended_slot": "2", "recommended_label": "Best", "show_total": True, **extra}
html = template.render(app={"metafields": {"dtj": {"licence": {"value": "active"}}}}, block={"settings": settings, "shopify_attributes": ""}, product=page)
html = re.sub(r"<!--.*?-->", "", html, flags=re.S)

css = (ROOT / "extensions/dtj-blocks/assets/dtj-addons.css").read_text(encoding="utf-8")
js = (ROOT / "extensions/dtj-blocks/assets/dtj-addons.js").read_text(encoding="utf-8")
clicks = "".join(f"document.querySelectorAll('[data-card]')[{i - 1}]?.click();" for i in tick)
doc = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>html{{color-scheme:light}}body{{margin:0;padding:16px;width:{W - 32}px;background:#fff;color:#121212;font:14px/1.4 Inter,"Segoe UI",system-ui,sans-serif}}
.shopify-block{{display:block}}img{{max-width:100%}}*{{transition:none!important;animation:none!important}}</style><style>{css}</style></head>
<body>{html}<script>{js}</script><script>window.addEventListener('load',()=>setTimeout(()=>{{{clicks}}},50));</script></body></html>"""
import html as htmllib  # noqa: E402

html_path = out.with_suffix(".html")
html_path.write_text(doc, encoding="utf-8")  # the plain page (used by preview_measure.py)
# Headless Edge never goes below ~496px wide, so a phone is simulated with an iframe of the true width.
frame_path = out.with_name(out.stem + "-frame.html")
frame_path.write_text(f'<!doctype html><body style="margin:0;background:#fff"><iframe srcdoc="{htmllib.escape(doc, quote=True)}" '
                      f'style="width:{W}px;height:{H}px;border:0;display:block"></iframe></body>', encoding="utf-8")
edge = next(p for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe") if Path(p).is_file())
subprocess.run([edge, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2", f"--window-size={max(W, 500)},{H}",
                f"--screenshot={out}", "--virtual-time-budget=2000", frame_path.as_uri()], check=True, capture_output=True, timeout=90)
print("wrote", out)
