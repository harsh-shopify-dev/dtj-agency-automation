"""DEV TOOL: does a block stay inside its container when a theme puts it in an awkward layout and a merchant types a very long unbroken word?

    cd services/block-library
    DTJ_APP_ROOT=<app folder> ../../.work/.venv/Scripts/python tools/preview_overflow.py [block-id ...]

Each block is rendered with long text in every text setting, inside a 358px box, in three parents themes really use
(a grid with an `auto` column, a flex row, a flex column), in headless Edge/Chrome. It prints how many px the widest part of the block
sticks out past the box (0 = fine). Added 6 Oct 2026 after a Testimonials Slider made the whole page wider than the phone screen.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(HERE / "tools"))
import test_generated_blocks as tg  # noqa: E402
from liquid import DictLoader, Environment  # noqa: E402

BOX = 358
# Horizon puts every app block inside <div class="shopify-block shopify-app-block"> (the flex item), and that sits in a flex column that
# centres or left-aligns it (sections/section.liquid -> .layout-panel-flex). The first three wraps are generic stress layouts; the last two
# copy the theme's real structure, which is what broke the Testimonials Slider on 6 Oct 2026.
APP = '<div class="shopify-block shopify-app-block">{}</div>'
WRAPS = {
    "grid-auto": f'<div style="display:grid;grid-template-columns:auto;width:{BOX}px">{{}}</div>',
    "flex-row": f'<div style="display:flex;width:{BOX}px">{{}}</div>',
    "flex-col": f'<div style="display:flex;flex-direction:column;align-items:flex-start;width:{BOX}px">{{}}</div>',
    "horizon-center": f'<div style="display:flex;flex-direction:column;align-items:center;width:{BOX}px">' + APP + '</div>',
    "horizon-start": f'<div style="display:flex;flex-direction:column;align-items:flex-start;width:{BOX}px">' + APP + '</div>',
    # the theme's own classes and variables, with the theme's own stylesheet loaded (see THEME_CSS)
    "theme-center": f'<div class="layout-panel-flex layout-panel-flex--column section-content-wrapper mobile-column" style="--horizontal-alignment:center;--vertical-alignment:flex-start;--gap:20px;--flex-wrap:nowrap;--flex-direction:column;width:{BOX}px">' + APP + '</div>',
    "theme-start": f'<div class="layout-panel-flex layout-panel-flex--column section-content-wrapper mobile-column" style="--horizontal-alignment:flex-start;--vertical-alignment:flex-start;--gap:20px;--flex-wrap:nowrap;--flex-direction:column;width:{BOX}px">' + APP + '</div>',
    # Dawn (Shopify's free reference theme) renders an app block straight into a plain container: sections/apps.liquid -> .page-width,
    # sections/main-product.liquid -> .product__info-container. Its stylesheets are fetched into .work/dawn (see docs/HANDOFF.md).
    "dawn-apps": f'<div class="page-width" style="width:{BOX}px">' + APP + '</div>',
    "dawn-product": f'<div class="grid grid--1-col product" style="width:{BOX}px"><div class="grid__item product__info-wrapper"><div class="product__info-container">' + APP + '</div></div></div>',
}
WORK = HERE.parent.parent / ".work"
THEME_FILES = {  # wrap-name prefix -> the real stylesheets to load (git-ignored review copies)
    "theme": [WORK / "master-packs" / "assets" / "base.css"],
    "dawn": [WORK / "dawn" / "base.css", WORK / "dawn" / "section-main-product.css"],
}
LONG = "W" * 70
ASSETS = tg.cl.ext_of(tg.ROOT) / "assets"


def render_block(manifest):
    settings = dict(tg.defaults(manifest))
    settings.update(manifest["test"]["sample"])
    for key, value in list(settings.items()):  # stress every text setting with a very long word (not selects, colours, ranges)
        spec = next((s for s in manifest["settings"] if s.get("id") == key), {})
        if spec.get("type") in ("text", "textarea", "inline_richtext"):
            settings[key] = f"{value}{LONG}" if value else value
    env = Environment(loader=DictLoader({p.stem: p.read_text(encoding="utf-8") for p in tg.SNIPPETS.glob("*.liquid")}))
    env.add_filter("image_url", lambda v, **kw: str(v))
    env.add_filter("json", lambda v: json.dumps(v, default=str))
    env.add_filter("money", lambda v: f"Rs. {v}")
    template = env.from_string(tg.cl.strip_schema(tg.block_text(manifest)), globals={"request": {"design_mode": False}})
    html = template.render(app={"metafields": {"dtj": {"licence": {"value": "active"}}}}, block={"settings": settings, "shopify_attributes": ""})
    return re.sub(r"<!--.*?-->", "", html, flags=re.S)


def measure(manifest, wrap_html, wrap_name):
    css = (ASSETS / f"dtj-{manifest['id']}.css").read_text(encoding="utf-8")
    if os.environ.get("OVERFLOW_STRIP_FIX") == "1":  # control run: remove the two shared width fixes to see which layouts really need them
        css = re.sub(r"\.dtj-b,\s*\.dtj-b \*\s*\{[^}]*\}", "", css)
        css = re.sub(r"\.shopify-block:has\(> \.dtj-b\)\s*\{[^}]*\}", "", css)
    js_path = ASSETS / f"dtj-{manifest['id']}.js"
    js = js_path.read_text(encoding="utf-8") if js_path.exists() else ""
    # parts inside a sideways-scrolling row (overflow-x auto/scroll/hidden) are meant to extend: only the row itself counts
    probe = ("<script>addEventListener('load',()=>setTimeout(()=>{const box=document.getElementById('box').getBoundingClientRect();let max=0;"
             "const clipped=e=>{for(let p=e.parentElement;p&&p.id!=='box';p=p.parentElement){if(getComputedStyle(p).overflowX!=='visible')return true;}return false;};"
             "document.querySelectorAll('#box *').forEach(e=>{if(clipped(e))return;const r=e.getBoundingClientRect();if(r.width&&r.right>max)max=r.right;});"
             "const own=document.getElementById('box').firstElementChild.getBoundingClientRect();"
             "document.getElementById('o').textContent='RESULT'+JSON.stringify({box:box.right,widest:max,block:own.width,page:document.documentElement.scrollWidth})+'END';},400));</script>")
    body = wrap_html.format(render_block(manifest)).replace("<div ", '<div id="box" ', 1)
    theme = "".join(f.read_text(encoding="utf-8") for prefix, files in THEME_FILES.items() if wrap_name.startswith(prefix) for f in files if f.is_file())
    doc = (f'<!doctype html><meta charset="utf-8"><style>{theme}</style><style>html{{color-scheme:light}}body{{margin:0;font:14px/1.4 sans-serif}}{css}</style>'
           f'<body>{body}<pre id="o"></pre><script>{js}</script>{probe}</body>')
    path = HERE.parent.parent / ".work" / "previews" / f"overflow-{manifest['id']}-{wrap_name}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")
    edge = next(p for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe") if Path(p).is_file())
    result = subprocess.run([edge, "--headless=new", "--disable-gpu", "--window-size=700,600", "--virtual-time-budget=3000", "--dump-dom", path.as_uri()],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    found = re.search(r"RESULT(.*?)END", result.stdout, re.S)
    if not found:
        return None
    data = json.loads(found.group(1))
    over = round(data["widest"] - data["box"], 1)
    return (over if over >= 1 else 0), data  # under 1px is sub-pixel rounding, not overflow


def main(argv):
    wanted = set(argv)
    problems = 0
    for path in sorted((tg.ROOT / "manifests").glob("*.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if "settings" not in manifest or (wanted and manifest["id"] not in wanted):
            continue
        cells = []
        for name, wrap in WRAPS.items():
            got = measure(manifest, wrap, name)
            if got is None:
                cells.append(f"{name}: no result")
                problems += 1
            else:
                over, _data = got
                cells.append(f"{name}: {'OK' if over == 0 else f'STICKS OUT {over}px'}")
                problems += over > 0
        print(f"{manifest['id']:22} " + " | ".join(cells))
    print("\nall blocks stay inside their container" if not problems else f"\n{problems} wrap(s) overflow")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
