"""The collection page as shoppers see it, checked against the store's own data: run AFTER the page is written to the draft (read-only on
the store: it only opens the preview page in a clean headless Edge and reads the collection through the CLI without --allow-mutations).

    python .claude/skills/dtj-collection-page/scripts/check_collection_live.py --store X.myshopify.com --theme 123 --collection <handle> \
        --out .work/clients/<client>/collection-live      (the system Python with Playwright; --theme left out = the live theme)
    ... --collection <handle> --preview .work/clients/<client> --out ...   checks the LOCAL preview instead (Sort is not tried there)

  L1 no sideways scroll at 390 and 1280 px; L2 exactly one H1, the collection's title; L3 every product of the collection is on the page
  (up to 50), each once; L4 2 columns on a phone, the chosen columns on a laptop; L5 the first product picture inside the first screen
  (assemble_collection.COLLECTION_TARGETS); L6 every card: the rating and review count ONLY where the store has real reviews (a 0-review
  placeholder is never shown) and with the store's own numbers; L7 swatches only where the product has swatches; L8 badges only from whole
  tags (best-seller, new); L9 % OFF only from a real compare-at price, with the right number; L10 the button says Add to cart or Sold out
  as Shopify's availability says; L11 the count and Sort are there, and Sort really reorders (price, low to high); L12 no Liquid error.
Writes <out>/live-check.json and phone / desktop screenshots. Exit code 0 = every check passes, 2 = findings.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from store_read import expected_card, read_collection  # noqa: E402

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "services" / "store-builder"))
from page_builder.assemble_collection import COLLECTION_TARGETS  # noqa: E402

PHONE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
READ = r"""() => {
  const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden'; };
  const lists = [...document.querySelectorAll('.pl-list')].filter(vis);
  const cards = lists.flatMap(l => [...l.querySelectorAll('.pl-card')]).filter(vis);
  const first = cards[0]; const fr = first ? first.getBoundingClientRect() : null;
  const img = first ? first.querySelector('.pl-img') : null;
  return { width: innerWidth, page_width: document.documentElement.scrollWidth,
    h1: [...document.querySelectorAll('h1')].filter(vis).map(h => h.innerText.trim()),
    columns: fr ? cards.filter(c => Math.abs(c.getBoundingClientRect().top - fr.top) < 4).length : 0,
    first_image_top: img ? Math.round(img.getBoundingClientRect().top + scrollY) : null,
    count_text: ((document.querySelector('.pl-tools__count') || {}).innerText || '').trim(), sort: !!document.querySelector('.pl-tools__select'),
    liquid_error: /Liquid (syntax )?error/i.test(document.body.innerText),
    cards: cards.map(c => { const item = c.closest('.pl-item'); const q = s => c.querySelector(s);
      return { handle: c.dataset.handle, rating: q('.pl-rating__value') ? parseFloat(q('.pl-rating__value').innerText) : (q('.pl-rating') ? 'shown' : null),
        count_text: q('.pl-rating__count') ? q('.pl-rating__count').innerText : '', swatches: !!q('.pl-swatches'),
        badge: item && item.querySelector('.pl-badge') ? item.querySelector('.pl-badge').innerText.trim() : null,
        off: q('.pl-price__off') ? q('.pl-price__off').innerText.trim() : '', button: q('.pl-add') ? q('.pl-add').innerText.trim() : '',
        price: q('.pl-price__now') ? q('.pl-price__now').innerText.trim() : '' }; }) };
}"""


def money(text: str) -> float:
    digits = "".join(ch for ch in text if ch.isdigit() or ch == ".")
    return float(digits.strip(".") or 0)


def open_page(p, url: str, width: int):
    phone = width < 750
    b = p.chromium.launch(channel="msedge", headless=True)
    ctx = b.new_context(viewport={"width": width, "height": 844 if phone else 900}, is_mobile=phone, has_touch=phone,
                        user_agent=PHONE_UA if phone else None)
    page = ctx.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2500)
    for y in range(0, 6000, 700):
        page.evaluate(f"window.scrollTo(0,{y})")
        page.wait_for_timeout(150)
    page.evaluate("window.scrollTo(0,0)")
    page.wait_for_timeout(600)
    return b, page


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--store", required=True)
    ap.add_argument("--theme", help="the draft theme's id (left out = the live theme)")
    ap.add_argument("--collection", required=True)
    ap.add_argument("--columns", type=int, default=COLLECTION_TARGETS["desktop_columns"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--url", help="check this page instead (e.g. the local preview's page.html as a file:// address; Sort is then not tried)")
    ap.add_argument("--preview", help="a client folder: check its local preview (collection-preview/page.html) instead of the store's page")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    coll = read_collection(a.store, a.collection)
    want = {p["handle"]: expected_card(p) for p in coll["products"]["nodes"]}
    if a.preview:
        a.url = (Path(a.preview) / "collection-preview" / "page.html").resolve().as_uri()
    url = a.url or f"https://{a.store}/collections/{a.collection}" + (f"?preview_theme_id={a.theme}" if a.theme else "")
    findings, seen = [], {}

    def add(check, where, message):
        findings.append({"check": check, "where": where, "message": message})

    with sync_playwright() as p:
        for name, width in (("phone", 390), ("desktop", 1280)):
            b, page = open_page(p, url, width)
            try:
                page.screenshot(path=str(out / f"{name}-top.png"))
                page.screenshot(path=str(out / f"{name}.png"), full_page=True)
                m = page.evaluate(READ)
            finally:
                b.close()
            seen[name] = {k: v for k, v in m.items() if k != "cards"} | {"cards": len(m["cards"])}
            if m["page_width"] > width + 1:
                add("L1", name, f"the page is {m['page_width']} px wide on a {width} px screen (sideways scroll)")
            if m["h1"] != [coll["title"]]:
                add("L2", name, f"H1s on the page: {m['h1']}; expected exactly one, {coll['title']!r}")
            handles = [c["handle"] for c in m["cards"]]
            expected_n = min(50, coll["productsCount"]["count"])
            if len(handles) != expected_n or len(set(handles)) != len(handles):
                add("L3", name, f"{len(handles)} cards ({len(set(handles))} different) for {expected_n} products in the collection")
            cols = 2 if width < 750 else a.columns
            if m["columns"] != min(cols, len(handles)):
                add("L4", name, f"{m['columns']} cards in the first row, expected {min(cols, len(handles))}")
            limit = COLLECTION_TARGETS["phone_first_image_max" if width < 750 else "desktop_first_image_max"]
            if m["first_image_top"] is None or m["first_image_top"] > limit:
                add("L5", name, f"the first product picture starts at {m['first_image_top']} px; the target is {limit} px or less")
            for c in m["cards"]:
                w = want.get(c["handle"])
                if not w:
                    add("L3", name, f"{c['handle']}: on the page but not in the collection")
                    continue
                if w["rating"] is None and c["rating"] is not None:
                    add("L6", c["handle"], f"{name}: a rating is shown ({c['rating']}) but the store has no real reviews for it")
                elif w["rating"] is not None and c["rating"] != w["rating"]:
                    add("L6", c["handle"], f"{name}: rating {c['rating']} on the page, {w['rating']} in the store")
                elif w["count"] is not None and f"{w['count']} reviews" not in c["count_text"]:
                    add("L6", c["handle"], f"{name}: review count {c['count_text']!r}, the store says {w['count']}")
                if c["swatches"] != w["swatches"]:
                    add("L7", c["handle"], f"{name}: swatches {'shown' if c['swatches'] else 'missing'}, the product {'has' if w['swatches'] else 'has no'} swatches")
                if c["badge"] != w["badge"]:
                    add("L8", c["handle"], f"{name}: badge {c['badge']!r}, its tags say {w['badge']!r}")
                if (w["off"] and str(w["off"]) not in c["off"]) or (not w["off"] and c["off"]):
                    add("L9", c["handle"], f"{name}: offer text {c['off']!r}, the prices say {w['off']}% off")
                if c["button"] != w["button"]:
                    add("L10", c["handle"], f"{name}: button {c['button']!r}, Shopify's availability says {w['button']!r}")
            if not m["sort"] or not m["count_text"]:
                add("L11", name, "the product count or the Sort menu is missing")
            if m["liquid_error"]:
                add("L12", name, "the page shows a Liquid error")
        if not url.startswith("file:"):  # Sort really reorders: price, low to high, on a laptop (Shopify sorts; a local file cannot)
            sep = "&" if "?" in url else "?"
            b, page = open_page(p, url + f"{sep}sort_by=price-ascending", 1280)
            try:
                m = page.evaluate(READ)
            finally:
                b.close()
            prices = [money(c["price"]) for c in m["cards"]]
            seen["sorted_prices"] = prices
            if prices != sorted(prices):
                add("L11", "sort", f"?sort_by=price-ascending did not reorder the list: {prices}")
    result = {"url": url, "pass": not findings, "findings": findings, "measured": seen, "expected": want}
    (out / "live-check.json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    for f in findings:
        print(f"  {f['check']:4} {f['where']}: {f['message']}")
    print(f"live check {url}: " + ("PASS" if not findings else f"{len(findings)} finding(s)"))
    return 0 if not findings else 2


if __name__ == "__main__":
    sys.exit(main())
