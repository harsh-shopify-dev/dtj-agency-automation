"""Local preview of a designed collection page BEFORE anything is written to a theme: the real DTJ Product List block (the generated file),
the store's REAL products of one collection (titles, pictures, prices, compare-at prices, tags, shade swatches and the reviews metafields,
read-only through the Shopify CLI: no --allow-mutations), the page's own settings from <client>/collection-run/template.json, and the title
band as the theme draws it. Writes <client>/collection-preview/page.html, phone-390.png, desktop-1280.png and preview.json (the numbers the
skill's targets are checked against). The theme's header, footer and fonts are NOT drawn: the real look is checked on the draft afterwards.

    cd "D:\\CODE CONTAINERR\\WEB DEV\\dtj-agency-automation"
    .work\\.venv\\Scripts\\python .claude\\skills\\dtj-collection-page\\scripts\\preview_collection.py --client .work\\clients\\<client> \\
        --store <store>.myshopify.com --collection <handle> [--theme-css <a pulled theme's assets/base.css>]
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
APP = REPO / "services" / "block-library-collection"
sys.path.insert(0, str(REPO / "services" / "store-builder"))
sys.path.insert(0, str(REPO / "services" / "block-library" / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_library as cl  # noqa: E402
from liquid import DictLoader, Environment  # noqa: E402
from page_builder import browser  # noqa: E402
from store_read import expected_card, read_collection, read_collections  # noqa: E402

PROBE = r"""<script>(function(){function run(){var W=innerWidth,cards=[...document.querySelectorAll('.pl-list--grid .pl-card, .pl-list--mobile-grid2 .pl-card')].filter(function(c){return c.getBoundingClientRect().width>0;});
var first=cards[0],img=first?first.querySelector('.pl-img'):null,r=first?first.getBoundingClientRect():null;
var row=cards.filter(function(c){return r&&Math.abs(c.getBoundingClientRect().top-r.top)<4;});var h1=document.querySelector('h1');
var out={width:W,page_width:document.documentElement.scrollWidth,cards:cards.length,columns:row.length,first_image_top:img?Math.round(img.getBoundingClientRect().top+scrollY):null,
 h1_px:h1?Math.round(parseFloat(getComputedStyle(h1).fontSize)):null,ratings:document.querySelectorAll('.pl-card .pl-rating').length,
 swatch_rows:document.querySelectorAll('.pl-card .pl-swatches').length,buttons:document.querySelectorAll('.pl-card .pl-add').length,
 sort:!!document.querySelector('.pl-tools__select'),count_text:(document.querySelector('.pl-tools__count')||{}).textContent||''};
var sink=parent&&parent.document&&parent.document.getElementById('pbm');var json='PBRESULT'+JSON.stringify(out)+'PBEND';
if(sink&&parent!==window)sink.textContent=json;else{var p=document.createElement('pre');p.id='pbm';p.textContent=json;document.body.appendChild(p);}}
window.addEventListener('load',function(){setTimeout(run,600);});})();</script>"""


class OV(dict):  # an option value prints as its name in Liquid, as Shopify's does
    def __str__(self):
        return self["name"]


def gid(value: str) -> int:
    return int(str(value).rsplit("/", 1)[-1])


def cents(value) -> int:
    return int(round(float(value or 0) * 100))


def to_liquid_product(p: dict) -> dict:
    images = [{"id": gid(i["id"]), "src": i["url"], "width": i["width"], "height": i["height"], "alt": i.get("altText") or ""} for i in p["images"]["nodes"]]
    variants = [{"id": gid(v["id"]), "title": v["title"], "price": cents(v["price"]), "compare_at_price": cents(v["compareAtPrice"]),
                 "available": v["availableForSale"], "featured_media": {"id": gid(v["image"]["id"]) if v.get("image") else ""}} for v in p["variants"]["nodes"]]
    first = next((v for v in variants if v["available"]), variants[0])
    options = []
    for k, o in enumerate(p["options"]):
        vals = []
        for j, ov in enumerate(o["optionValues"]):
            var = next((v for v in variants if ov["name"] in v["title"].split(" / ")), first)
            sw = ov.get("swatch") or None
            swatch = None
            if sw and sw.get("color"):
                h = sw["color"].lstrip("#")
                swatch = {"color": {"rgb": f"{int(h[0:2], 16)} {int(h[2:4], 16)} {int(h[4:6], 16)}"}}
            elif sw and sw.get("image"):
                swatch = {"image": sw["image"]["image"]["url"]}
            vals.append(OV(name=ov["name"], id=1000 * k + j, selected=var is first and j == 0, available=var["available"], variant=var, swatch=swatch))
        options.append({"name": o["name"], "position": k + 1, "values": vals})
    meta = {"reviews": {}}
    if p.get("rating"):
        v = json.loads(p["rating"]["value"])
        meta["reviews"]["rating"] = {"value": {"rating": v.get("value"), "scale_max": v.get("scale_max")}}
    if p.get("count"):
        meta["reviews"]["rating_count"] = p["count"]["value"]
    return {"id": gid(p["id"]), "handle": p["handle"], "title": p["title"], "url": "/products/" + p["handle"], "tags": p["tags"], "images": images,
            "variants": variants, "selected_or_first_available_variant": first, "available": any(v["available"] for v in variants),
            "options_with_values": options, "metafields": meta}


def brightness(hexcolor) -> int:
    h = str(hexcolor).lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return round((299 * r + 587 * g + 114 * b) / 1000)


def render_block(settings: dict, coll: dict) -> str:
    manifest = json.loads((APP / "manifests" / "product-list.json").read_text(encoding="utf-8"))
    text = (APP / manifest["block_file"]).read_text(encoding="utf-8")
    defaults = {s["id"]: s.get("default", "") for s in cl.extract_schema(text)["settings"] if "id" in s}
    snippets = {p.stem: p.read_text(encoding="utf-8") for p in (APP / "extensions" / "dtj-collection" / "snippets").glob("*.liquid")}
    env = Environment(loader=DictLoader(snippets))
    env.add_filter("image_url", lambda value, **kw: value["src"] if isinstance(value, dict) else str(value))
    env.add_filter("money", lambda value: "Rs. {:,.2f}".format(float(value or 0) / 100))
    env.add_filter("color_brightness", brightness)
    page_coll = {"title": coll["title"], "url": f"/collections/{coll['handle']}", "products_count": coll["productsCount"]["count"],
                 "sort_by": "manual", "default_sort_by": "manual", "products": [to_liquid_product(p) for p in coll["products"]["nodes"]],
                 "sort_options": [{"value": v, "name": n} for v, n in (("manual", "Featured"), ("best-selling", "Best selling"),
                                  ("price-ascending", "Price, low to high"), ("price-descending", "Price, high to low"), ("created-descending", "Date, new to old"))]}
    s = {k: v for k, v in settings.items() if k != "collection"}  # the page's own collection, as on a real collection page
    template = env.from_string(cl.strip_schema(text), globals={"request": {"design_mode": False, "page_type": "collection"}, "collection": page_coll,
                                                                "routes": {"cart_add_url": "/cart/add", "cart_url": "/cart"}})
    out = template.render(app={"metafields": {"dtj": {"licence": {"value": "active"}}}}, block={"id": "pl1", "settings": {**defaults, **s}, "shopify_attributes": ""})
    return re.sub(r"<!--.*?-->", "", out, flags=re.S)


COMMERCE = REPO / "services" / "block-library-commerce"


def render_nav(settings: dict, colls: dict) -> tuple[str, str]:
    """The links row with the REAL DTJ Commerce circle-menu block and the store's own collections (pictures, names, addresses)."""
    text = (COMMERCE / "extensions" / "dtj-commerce" / "blocks" / "dtj-circle-menu.liquid").read_text(encoding="utf-8")
    defaults = {s["id"]: s.get("default", "") for s in cl.extract_schema(text)["settings"] if "id" in s}
    snippets = {p.stem: p.read_text(encoding="utf-8") for p in (COMMERCE / "extensions" / "dtj-commerce" / "snippets").glob("*.liquid")}
    env = Environment(loader=DictLoader(snippets))
    env.add_filter("image_url", lambda value, **kw: value["src"] if isinstance(value, dict) else str(value))
    s = dict(settings)
    s["collections"] = [{"title": c["title"], "url": f"/collections/{c['handle']}",
                         "image": ({"src": c["image"]["url"], "width": c["image"]["width"], "height": c["image"]["height"]} if c.get("image") else None)}
                        for c in (colls.get(h) for h in settings.get("collections", [])) if c]
    out = env.from_string(cl.strip_schema(text), globals={"request": {"design_mode": False}}).render(
        app={"metafields": {"dtj": {"licence": {"value": "active"}}}}, block={"id": "nav1", "settings": {**defaults, **s}, "shopify_attributes": ""})
    css = (COMMERCE / "extensions" / "dtj-commerce" / "assets" / "dtj-circle-menu.css").read_text(encoding="utf-8")
    return re.sub(r"<!--.*?-->", "", out, flags=re.S), css


def header_html(head: dict, coll: dict) -> str:
    st = head["settings"]
    t, d = head["blocks"]["title"]["settings"], head["blocks"]["description"]["settings"]
    desc = coll.get("descriptionHtml") or ""
    return (f'<div class="pv-head" style="background:{st["background_color"]};--pt:{st["padding-block-start"]}px;--pb:{st["padding-block-end"]}px;'
            f'color:{t["text_color"]}"><div class="pv-head__in" style="gap:{st["gap"]}px">'
            f'<h1 class="pv-h1">{htmllib.escape(coll["title"])}</h1>' + (f'<div class="pv-desc">{desc}</div>' if desc else "") + "</div></div>")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--client", required=True)
    ap.add_argument("--store", required=True)
    ap.add_argument("--collection", required=True, help="the handle of a collection to show (one with ratings and shades shows the most)")
    ap.add_argument("--theme-css", help="a pulled theme's assets/base.css, for the theme's resets (optional)")
    args = ap.parse_args()
    client = Path(args.client)
    tpl = json.loads((client / "collection-run" / "template.json").read_text(encoding="utf-8"))
    head = tpl["sections"].get("dtj_collection_header")
    prod = tpl["sections"]["dtj_collection_products"]
    block = next(iter(prod["blocks"].values()))
    wrap = prod["settings"]
    coll = read_collection(args.store, args.collection)
    block_html = render_block(block["settings"], coll)
    nav_html, nav_css = "", ""
    if "collection_nav" in tpl["sections"]:
        nav_settings = next(iter(tpl["sections"]["collection_nav"]["blocks"].values()))["settings"]
        nav_html, nav_css = render_nav(nav_settings, read_collections(args.store, nav_settings.get("collections", [])))
        nav_html = f'<div class="shopify-block shopify-app-block">{nav_html}</div>'
    css = (APP / "extensions" / "dtj-collection" / "assets" / "dtj-product-list.css").read_text(encoding="utf-8")
    js = (APP / "extensions" / "dtj-collection" / "assets" / "dtj-product-list.js").read_text(encoding="utf-8")
    base = Path(args.theme_css).read_text(encoding="utf-8") if args.theme_css else ""
    page_css = """body{margin:0;font-family:Inter,system-ui,sans-serif;color:#0f171f;background:#fff}
.pv-head{padding:calc(var(--pt)) 16px calc(var(--pb))}.pv-head__in{display:flex;flex-direction:column;align-items:center;text-align:center;max-width:1200px;margin:0 auto}
.pv-h1{margin:0;font-size:32px;line-height:1.15;font-weight:700}.pv-desc{max-width:42ch;font-size:14px;line-height:1.5}.pv-desc p{margin:0}
.pv-prod{padding:calc(var(--pt)) 0 calc(var(--pb))}
@media (width<750px){.pv-head{padding:max(20px,calc(.7*var(--pt))) 16px max(20px,calc(.7*var(--pb)))}.pv-prod{padding:max(20px,calc(.7*var(--pt))) 0 max(20px,calc(.7*var(--pb)))}.pv-h1{font-size:24px}}
.pv-bar{height:64px;background:#0f171f;color:#fff;display:flex;align-items:center;padding:0 16px;font:600 14px system-ui}"""
    doc = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           '<script type="importmap">{"imports":{"@shopify/events":"https://cdn.shopify.com/storefront/standard-events.js"}}</script>'
           f'<style>{base}</style><style>{page_css}</style><style>{css}</style><style>{nav_css}</style></head><body>'
           '<div class="pv-bar">(the theme\'s header: not drawn in the preview)</div>'
           + (header_html(head, coll) if head else "") + nav_html
           + f'<div class="pv-prod" style="--pt:{wrap["padding-block-start"]}px;--pb:{wrap["padding-block-end"]}px;background:{wrap.get("background_color") or "#fff"}">'
           f'<div class="shopify-block shopify-app-block">{block_html}</div></div><script>{js}</script></body></html>')
    out = client / "collection-preview"
    out.mkdir(parents=True, exist_ok=True)
    (out / "page.html").write_text(doc, encoding="utf-8")
    eb = browser.EdgeBrowser(work=out / "_frames")
    numbers = {}
    for name, width in (("phone", 390), ("desktop", 1280)):
        m = eb.measure(doc, width, probe=PROBE, height=1600)
        numbers[name] = m
        eb.screenshot(doc, width, 1500 if width == 390 else 1200, out / f"{name}-{width}.png")
    numbers["collection"] = {"handle": coll["handle"], "title": coll["title"], "products": coll["productsCount"]["count"],
                             "with_rating": sum(1 for p in coll["products"]["nodes"] if p.get("rating")),
                             "with_reviews": sum(1 for p in coll["products"]["nodes"] if p.get("count") and int(p["count"]["value"] or 0) > 0),
                             "with_swatches": sum(1 for p in coll["products"]["nodes"] if any(v.get("swatch") for o in p["options"] for v in o["optionValues"]))}
    # what each card will show, from the store's own data (step C2): the person sees why a card shows less, before anything is written
    numbers["cards"] = [expected_card(p) for p in coll["products"]["nodes"]]
    (out / "preview.json").write_text(json.dumps(numbers, indent=1), encoding="utf-8")
    for key in ("phone", "desktop"):
        m = numbers[key]
        print(f"{key:7} {m['width']} px: {m['cards']} cards, {m['columns']} columns, first picture at {m['first_image_top']} px, "
              f"{m['ratings']} with stars, {m['swatch_rows']} with swatches, count {m['count_text']!r}, sort {'yes' if m['sort'] else 'NO'}")
    print(f"\nwhat each card shows ({coll['title']}, {coll['productsCount']['count']} products; from the store's own data):")
    for c in numbers["cards"]:
        stars = f"{c['rating']} | {c['count']} reviews" if c["rating"] is not None else "no stars (no reviews)"
        print(f"  {c['handle'][:38]:38} {stars:24} {'swatches' if c['swatches'] else 'no swatches':12} {(c['badge'] or 'no badge'):13} "
              f"{(str(c['off']) + '% OFF') if c['off'] else 'no offer':9} {c['button']}")
    print(f"\npreview: {out / 'page.html'} | screenshots: {out / 'phone-390.png'}, {out / 'desktop-1280.png'}")


if __name__ == "__main__":
    main()
