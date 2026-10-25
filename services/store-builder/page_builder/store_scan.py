"""Read a brand's Shopify store from its public pages, from the one link a person sends the bot (Harsh, 21 Oct 2026: "i just share
the brand store link and it starts designing the store and it asks the specific questions it needs"). Read only, no login.

    python -m page_builder.store_scan https://brand.com            prints the scan as JSON

What the store job needs before it asks its questions: the store's ORIGINAL .myshopify.com address (Shopify.shop in the page; a
renamed store keeps it), its name, its live theme (name and id), how many products and collections it has, and its products in the
store's own best-selling order (its /collections/all page sorted by best-selling; the product list's order when that page is hidden).
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from typing import Callable
from urllib.parse import urlparse

from .brand_intake import Getter, _get, _json, _safe_get, read_home

SHOP = re.compile(r'Shopify\.shop\s*=\s*"([a-z0-9][a-z0-9-]*\.myshopify\.com)"')
THEME = re.compile(r"Shopify\.theme\s*=\s*(\{.*?\});")
PRODUCT_LINK = re.compile(r'href="(?:https?://[^"/]+)?(?:/[a-z]{2}(?:-[a-z]{2})?)?/(?:collections/[^"/]+/)?products/([a-z0-9][a-z0-9-]*)[?"#]', re.I)
MAX_PAGES = 10  # 2,500 products: enough to count; a bigger catalogue says "2500+"
PAGE_SIZE = 250


class NotShopify(Exception):
    """The link is not a Shopify store's public page (or the store is password-protected)."""


def base_url(link: str) -> str:
    link = link.strip()
    if not re.match(r"https?://", link, re.I):
        link = "https://" + link
    u = urlparse(link)
    if not u.netloc or "." not in u.netloc:
        raise NotShopify(f"{link!r} is not a website address")
    return f"https://{u.netloc.lower()}"


def products(base: str, get: Getter) -> tuple[list[dict], bool]:
    """Every product as {handle, title, type}; True when the catalogue goes past MAX_PAGES pages."""
    found: list[dict] = []
    for page in range(1, MAX_PAGES + 1):
        data = _json(get, f"{base}/products.json?limit={PAGE_SIZE}&page={page}")
        items = (data or {}).get("products") or []
        found += [{"handle": p.get("handle"), "title": html.unescape(str(p.get("title") or "")), "type": p.get("product_type") or ""}
                  for p in items if p.get("handle")]
        if len(items) < PAGE_SIZE:
            return found, False
    return found, True


def best_sellers(base: str, get: Getter, known: list[str]) -> tuple[list[str], str]:
    """The handles in the store's best-selling order, and where that order came from."""
    status, body = _safe_get(get, f"{base}/collections/all?sort_by=best-selling")
    order: list[str] = []
    if status == 200:
        for handle in PRODUCT_LINK.findall(body.decode("utf-8", "replace")):
            handle = handle.lower()
            if handle in known and handle not in order:
                order.append(handle)
    if order:
        return order + [h for h in known if h not in order], "the store's best-selling order (/collections/all?sort_by=best-selling)"
    return list(known), "the store's product list order (its best-selling page did not answer)"


def store_domain(link: str) -> str | None:
    """The .myshopify.com address a link names by itself: admin.shopify.com/store/<handle> or <handle>.myshopify.com."""
    m = (re.search(r"admin\.shopify\.com/store/([a-z0-9][a-z0-9-]*)", link, re.I)
         or re.search(r"(?:^|//)([a-z0-9][a-z0-9-]*)\.myshopify\.com", link.strip(), re.I))
    return f"{m.group(1).lower()}.myshopify.com" if m else None


def scan(link: str, get: Getter = _get, private: Callable[[str, str], dict] | None = None) -> dict:
    """private(domain, link): how to read a store whose public pages show nothing (an admin link, or a store behind its password
    page, as every dev store is): the caller reads it with DTJ's own access instead (store_job.py). Without it, such a link is
    refused with what to send instead."""
    domain = store_domain(link)
    if domain and "admin.shopify.com" in link.lower():
        if private:
            return private(domain, link)
        raise NotShopify(f"{link} is the store's admin: its public address is https://{domain}")
    base = base_url(link)
    status, body = _safe_get(get, base + "/")
    if status != 200:
        if domain and private:
            return private(domain, link)
        raise NotShopify(f"{base} did not answer ({status or 'no response'})")
    page = body.decode("utf-8", "replace")
    shop = SHOP.search(page)
    if not shop:
        if "/password" in page[:20000] and "shopify" in page.lower():
            if domain and private:
                return private(domain, link)  # a dev store: read with DTJ's own access, not the public page
            raise NotShopify(f"{base} is a Shopify store behind a password page: send its <name>.myshopify.com address")
        raise NotShopify(f"{base} does not look like a Shopify store (no Shopify.shop in its page)")
    home = read_home(base, page)
    theme = {}
    m = THEME.search(page)
    if m:
        try:
            t = json.loads(m.group(1))
            theme = {"name": t.get("name"), "id": str(t.get("id") or ""), "schema_name": t.get("schema_name"),
                     "schema_version": t.get("schema_version")}
        except ValueError:
            theme = {}
    items, more = products(base, get)
    order, order_source = best_sellers(base, get, [p["handle"] for p in items])
    titles = {p["handle"]: p["title"] for p in items}
    collections = _json(get, f"{base}/collections.json?limit=250") or {}
    return {
        "link": link.strip(), "base": base, "myshopify_domain": shop.group(1), "name": home.get("name") or shop.group(1).split(".")[0],
        "currency": home.get("currency"), "live_theme": theme,
        "product_count": len(items), "more_products": more,
        "best_sellers": [{"handle": h, "title": titles.get(h, h), "url": f"{base}/products/{h}"} for h in order],
        "best_sellers_from": order_source,
        "collection_count": len(collections.get("collections") or []),
    }


def product_choices(count: int) -> list[tuple[str, str]]:
    """The product-page options to offer for a store of `count` products (Harsh, 21 Oct 2026: "lets say if a brand has less products
    then it creates all so i guess these decision should be taken there"): (button label, value) pairs."""
    if count <= 0:
        return [("No product pages", "none")]
    options: list[tuple[str, str]] = []
    if count <= 12:
        options.append((f"All {count} products" if count > 1 else "The 1 product", f"all:{count}"))
    for n in (3, 5, 10):
        if n < count and len(options) < 3:
            options.append((f"Top {n} best sellers", f"top:{n}"))
    options.append(("I'll pick them", "pick"))
    return options


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("link")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        print(json.dumps(scan(a.link), indent=1, ensure_ascii=False))
    except NotShopify as exc:
        print(f"not read: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
