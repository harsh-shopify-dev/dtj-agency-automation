"""Local page preview: turns a built page (the template JSON from assemble.build_pdp) into ONE self-contained HTML page, using the REAL
generated DTJ block files, their CSS/JS and the theme's stylesheet, so a browser can measure and screenshot the page BEFORE anything is
pushed to a store (see review.py).

What is real here: every DTJ block (the same Liquid Shopify runs, rendered by python-liquid), its CSS and JS, the page's block settings
(colours, bands, padding, radius, text) and the theme's base.css when the review copy exists (.work/master-packs/assets/base.css).
What is NOT real, and is marked on the page (data-pb-theme) and in the returned notes: the theme's own parts of the product section
(gallery, title, variant picker, buy buttons, description) are grey stand-ins; pictures are labelled placeholders unless a local media
folder holds the file; live data (price, stock, products in pickers) uses each block's own preview sample. The final check is still the
real store preview after a person approves the push.
"""
from __future__ import annotations

import base64
import html as htmllib
import json
import re
from functools import lru_cache
from pathlib import Path

from .catalog import _SCHEMA, IMAGE_PREFIX, SERVICES, registry

REPO = SERVICES.parent
THEME_CSS = REPO / ".work" / "master-packs" / "assets" / "base.css"
_REF = re.compile(r"^shopify://apps/(?P<app>[^/]+)/blocks/dtj-(?P<block>[^/]+)/")
PLACEHOLDER_COLOURS = ["#C9D3DB", "#D8CFC4", "#C4D6C9", "#D6C9D8"]


def _ext(app: str) -> Path:
    return SERVICES / Path(registry()[app]["folder"]).parent  # .../extensions/<ext>


def _app_root(app: str) -> Path:
    return SERVICES / Path(registry()[app]["folder"]).parts[0]  # .../services/block-library[-sections[-2]]


@lru_cache(maxsize=None)
def _block_source(app: str, block: str) -> tuple[str, dict]:
    text = (_ext(app) / "blocks" / f"dtj-{block}.liquid").read_text(encoding="utf-8")
    return _SCHEMA.sub("", text), json.loads(_SCHEMA.search(text).group(1))


@lru_cache(maxsize=None)
def _snippets(app: str) -> dict:
    return {p.stem: p.read_text(encoding="utf-8") for p in (_ext(app) / "snippets").glob("*.liquid")}


def _manifest(app: str, block: str) -> dict:
    path = _app_root(app) / "manifests" / f"{block}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def placeholder(label: str, n: int = 0, ratio: float = 1.0) -> dict:
    """A labelled stand-in picture object (Shopify's image object has src/width/height/aspect_ratio/alt)."""
    h = 600
    w = round(h * ratio)
    text = htmllib.escape(label[:40])
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"><rect width="{w}" height="{h}" fill="{PLACEHOLDER_COLOURS[n % 4]}"/>'
           f'<text x="50%" y="50%" text-anchor="middle" font-family="sans-serif" font-size="28" fill="#4a5560">{text}</text></svg>')
    return {"src": "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode(), "width": w, "height": h, "aspect_ratio": ratio, "alt": ""}


def _picture(value: str, media_dir: Path | None, n: int) -> dict:
    name = value[len(IMAGE_PREFIX):]
    people = Path(__file__).resolve().parent / "assets" / "sample-people" / name  # DTJ's sample people photos
    path = media_dir / name if media_dir and (media_dir / name).is_file() else (people if people.is_file() else None)
    if path:
        w, h = 1000, 1000
        try:  # real proportions when Pillow is installed; a square otherwise
            from PIL import Image
            with Image.open(path) as im:
                w, h = im.size
        except Exception:  # noqa: BLE001 - a picture we cannot measure is shown square, nothing else depends on it
            pass
        return {"src": path.resolve().as_uri(), "width": w, "height": h, "aspect_ratio": round(w / h, 4), "alt": ""}
    return placeholder(f"picture: {name}", n)


def _stand_in_product(handle: str, n: int) -> dict:
    variant = {"id": 1000 + n, "available": True, "price": 0, "compare_at_price": None}
    return {"handle": handle, "title": f"[{handle}]", "url": "#", "featured_media": placeholder(handle, n),
            "selected_or_first_available_variant": variant, "variants": [variant], "price": 0}


def block_settings(app: str, block: str, values: dict, media_dir: Path | None = None) -> dict:
    """Every declared setting gets a value like on Shopify: the page's value, else the default, else blank ("")."""
    _, schema = _block_source(app, block)
    out, n = {}, 0
    for s in schema.get("settings", []):
        if "id" not in s:
            continue
        key, kind = s["id"], s["type"]
        value = values.get(key, s.get("default", ""))
        if kind == "image_picker" and isinstance(value, str) and value.startswith(IMAGE_PREFIX):
            n += 1
            value = _picture(value, media_dir, n)
        elif kind == "product_list" and isinstance(value, list):
            value = [_stand_in_product(h, i) for i, h in enumerate(value)]
        out[key] = value
    return out


def _money(value, cents: bool) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return f"Rs. {value}"
    return f"Rs. {v / 100:,.2f}" if cents else f"Rs. {v:,.2f}"


def render_block(app: str, block: str, values: dict, *, key: str, section_id: str, product: dict | None = None,
                 media_dir: Path | None = None) -> str:
    from liquid import DictLoader, Environment  # python-liquid (requirements: python-liquid)

    source, _ = _block_source(app, block)
    env = Environment(loader=DictLoader(_snippets(app)))
    cents = block == "price"  # the price block reads Shopify money values (cents); preview samples elsewhere are plain numbers
    env.add_filter("image_url", lambda v, **kw: v["src"] if isinstance(v, dict) else (v or ""))
    env.add_filter("json", lambda v: json.dumps(v, ensure_ascii=False, default=str))
    env.add_filter("money", lambda v: _money(v, cents))
    env.add_filter("money_without_trailing_zeros", lambda v: _money(v, cents).replace(".00", ""))
    env.add_filter("video_tag", lambda v, **kw: f'<video id="{kw.get("id", "")}" class="{kw.get("class", "")}" muted playsinline></video>')
    template = env.from_string(source, globals={"request": {"design_mode": False}})
    sample = _manifest(app, block).get("test", {}).get("product")
    ctx = {
        "app": {"metafields": {"dtj": {"licence": {"value": "active"}}}},
        "block": {"settings": block_settings(app, block, values, media_dir), "id": key, "shopify_attributes": ""},
        "section": {"id": section_id, "settings": {}},
        "shop": {"money_format": "Rs. {{amount}}"},
        "product": {**(product or {}), **(sample or {})},
    }
    return re.sub(r"<!--.*?-->", "", template.render(**ctx), flags=re.S)


def _assets(app: str, block: str) -> tuple[str, str]:
    _, schema = _block_source(app, block)
    assets = _ext(app) / "assets"
    css = (assets / schema["stylesheet"]).read_text(encoding="utf-8") if schema.get("stylesheet") else ""
    js = (assets / schema["javascript"]).read_text(encoding="utf-8") if schema.get("javascript") else ""
    return css, js


def _stand_in(kind: str, label: str, height: int) -> str:
    return (f'<div data-pb-theme="{kind}" style="min-height:{height}px;display:flex;align-items:center;justify-content:center;'
            f'background:repeating-linear-gradient(45deg,#ececec 0 10px,#e2e2e2 10px 20px);color:#555;font:600 13px/1.3 sans-serif;'
            f'border-radius:6px;margin:6px 0">{htmllib.escape(label)}</div>')


def page_html(result, *, media_dir: Path | None = None, width_hint: str = "") -> tuple[str, dict]:
    """(html, notes). notes lists what is real and what is a stand-in, for the report."""
    model, template = result.model, result.template
    roles = model.direction.roles
    used: dict[tuple[str, str], None] = {}
    notes = {"theme_css": THEME_CSS.is_file(), "stand_ins": [], "placeholder_pictures": 0, "sections": []}
    product = {"title": model.facts["product"]["title"], "handle": model.facts["product"].get("handle", ""), "url": "#"}

    def dtj(entry: dict, key: str, section_id: str) -> str:
        m = _REF.match(entry["type"])
        app, block = m["app"], m["block"]
        used[(app, block)] = None
        body = render_block(app, block, entry.get("settings", {}), key=key, section_id=section_id, product=product, media_dir=media_dir)
        notes["placeholder_pictures"] += body.count("data:image/svg+xml;base64")
        return f'<div class="shopify-block shopify-app-block" data-pb-block="{key}" data-pb-dtj="{app}/{block}">{body}</div>'

    # ---- the product section: the theme's own parts are stand-ins, the DTJ buy-box blocks are real
    from .assemble import product_column
    details = product_column(template)  # Horizon's product-details or Dawn's main-product
    col = []
    for key in details["block_order"]:
        entry = details["blocks"][key]
        t = entry["type"]
        if t.startswith("shopify://apps/"):
            col.append(dtj(entry, key, "main"))
        elif t == "group":
            for sub in entry.get("block_order", []):
                sub_entry = entry["blocks"][sub]
                if sub_entry["type"].startswith("shopify://apps/"):
                    col.append(dtj(sub_entry, sub, "main"))
                else:
                    notes["stand_ins"].append(f"theme {sub_entry['type']}")
                    col.append(f'<h1 data-pb-theme="title" style="margin:8px 0;font-size:28px;line-height:1.15">{htmllib.escape(product["title"])}</h1>'
                               if sub_entry["type"] == "text" else _stand_in(sub_entry["type"], f"theme: {sub_entry['type']}", 24))
        elif t == "title":  # Dawn's title block
            notes["stand_ins"].append("theme title")
            col.append(f'<h1 data-pb-theme="title" style="margin:8px 0;font-size:28px;line-height:1.15">{htmllib.escape(product["title"])}</h1>')
        else:
            notes["stand_ins"].append(f"theme {t}")
            height = {"buy-buttons": 96, "buy_buttons": 96, "variant-picker": 56, "variant_picker": 56, "_divider": 2, "text": 60,
                      "description": 120}.get(t, 40)
            col.append(_stand_in(t, f"theme: {t}", height))
    notes["stand_ins"].insert(0, "theme product gallery")
    main = (f'<section class="pb-main" data-pb-section="main"><div class="pb-gallery">{_stand_in("gallery", "theme: product gallery", 320)}</div>'
            f'<div class="pb-details">{"".join(col)}</div></section>')

    # ---- the DTJ sections below the product section, in template order
    parts = [main]
    for sid in template["order"]:
        if sid == "main":
            continue
        sec = template["sections"][sid]
        if not sec.get("block_order"):  # one of the theme's own sections (Dawn's related products): a labelled stand-in
            notes["stand_ins"].append(f"theme {sec.get('type')}")
            parts.append(f'<section class="pb-section" data-pb-theme="{sec.get("type")}">{_stand_in(sec.get("type", "section"), "theme: " + str(sec.get("type")), 120)}</section>')
            continue
        inner = "".join(dtj(sec["blocks"][k], k, sid) for k in sec["block_order"])
        role = model.roles.get(sid, "")
        notes["sections"].append({"id": sid, "role": role})
        parts.append(f'<section class="pb-section" data-pb-section="{sid}" data-pb-role="{role}">'
                     f'<div class="layout-panel-flex layout-panel-flex--column section-content-wrapper mobile-column" '
                     f'style="--horizontal-alignment:center;--vertical-alignment:flex-start;--gap:0px;--flex-wrap:nowrap;--flex-direction:column">'
                     f'{inner}</div></section>')

    css_parts, js_parts = [], []
    for app, block in used:
        css, js = _assets(app, block)
        css_parts.append(css)
        if js:
            js_parts.append(js)
    theme_css = THEME_CSS.read_text(encoding="utf-8") if notes["theme_css"] else ""
    page_css = (
        f"html{{color-scheme:light}}body{{margin:0;background:{roles['bg']};color:{roles['text']};"
        "font:15px/1.5 Inter,'Segoe UI',system-ui,sans-serif}*{transition:none!important;animation-duration:0s!important}"
        # Horizon's product columns are capped tracks (a subgrid of minmax(0, ...) columns), so wide content cannot stretch them:
        # the stand-in must do the same or the review reports overflow the real theme would not have (found 9 Oct 2026)
        "img,video{max-width:100%}.pb-main{display:grid;grid-template-columns:minmax(0,1fr);gap:16px;padding:16px}"
        "@media (min-width:750px){.pb-main{grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:40px;padding:32px 40px;max-width:1200px;margin:0 auto}}"
        ".pb-section>.layout-panel-flex{width:100%}.pb-section .shopify-app-block{width:100%}"
    )
    doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>Preview {htmllib.escape(model.brand["brand_name"])} {width_hint}</title>'
           f'<style>{theme_css}</style><style>{page_css}</style><style>{"".join(css_parts)}</style></head>'
           f'<body>{"".join(parts)}<script>{";".join(js_parts)}</script></body></html>')
    return doc, notes
