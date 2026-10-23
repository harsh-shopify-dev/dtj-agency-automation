"""Read a product the way the store shows it publicly and fetch its pictures for the page builder (factory P2, a new page).

    cd services/store-builder
    python -m page_builder.fetch_product --store X.myshopify.com --handle <product handle> --client ../../.work/clients/<folder>

Writes <client>/store-product.json (title, price and compare-at price in rupees, options, variants, availability, vendor, type,
tags, the description as plain text, and every picture and video with its store file name, alt text and size) and downloads each
picture into <client>/media/<store file name>. In facts.json a picture is named by that store file name (facts.media[].file): the
page links it as shopify://shop_images/<name>, the name the store's Content > Files shows for product pictures, and run_client
--media uses the downloaded copies for the screenshot review. Videos are listed, not downloaded: facts.ugc[].video needs the name
shown in Content > Files, which can differ from the link (ask Harsh for it).
Reads only public pages; never writes to the store. Exit 0 = done, 1 = the product could not be read.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable
from urllib.parse import unquote, urlparse

from .theme_target import normalise_store

Getter = Callable[[str], tuple[int, str, bytes]]


def _get(url: str) -> tuple[int, str, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "dtj-page-builder/1", "Accept": "application/json, image/*"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.geturl(), r.read()


def file_name(src: str) -> str:
    """The store file name of a picture link (//store/cdn/shop/files/NAME.webp?v=1 or https://cdn.shopify.com/.../files/NAME.webp)."""
    return unquote(Path(urlparse(src if not src.startswith("//") else "https:" + src).path).name)


def as_text(description_html: str) -> str:
    text = re.sub(r"<(br|/p|/li|/h\d)\s*/?>", "\n", description_html or "", flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return "\n".join(line.strip() for line in re.sub(r"[ \t]+", " ", text).splitlines() if line.strip())


def _admin_call(body: dict) -> dict:
    """The install service's POST /copy, signed with this computer's control key (n8n/store-factory/store_job.py _catcher)."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "n8n" / "store-factory"))
    from store_job import _catcher  # noqa: PLC0415
    return _catcher(body)


def from_admin(store: str, handle: str, call: Callable[[dict], dict] = _admin_call) -> dict:
    """The product through DTJ Store Builder (read only), when the storefront is behind its password page (23 Oct 2026: a dev store
    never drops it, and the first page run on the VPS stopped there). Same shape as the public read."""
    p = call({"op": "product", "shop": normalise_store(store), "handle": handle})["product"]
    money = lambda v: round(float(v), 2) if v not in (None, "") else None  # noqa: E731 - the store's own currency, as the .js read
    variants = (p.get("variants") or {}).get("nodes") or []
    media = []
    for m in (p.get("media") or {}).get("nodes") or []:
        img = (m.get("image") or (m.get("preview") or {}).get("image") or {})
        kind = "video" if m.get("mediaContentType") in ("VIDEO", "EXTERNAL_VIDEO") else "image"
        item = {"type": kind, "file": file_name(img.get("url") or ""), "url": img.get("url") or "", "alt": m.get("alt") or "",
                "width": img.get("width"), "height": img.get("height")}
        if kind == "video":
            item["sources"] = [s.get("url") for s in m.get("sources") or [] if s.get("url")]
        media.append(item)
    first = variants[0] if variants else {}
    return {
        "store": normalise_store(store), "handle": p.get("handle", handle), "title": p.get("title"),
        "price_rupees": money(first.get("price")), "compare_at_price_rupees": money(first.get("compareAtPrice")),
        "available": any(v.get("availableForSale") for v in variants), "vendor": p.get("vendor"), "type": p.get("productType"),
        "tags": p.get("tags") or [], "options": [o.get("name") for o in p.get("options") or []],
        "variants": [{"title": v.get("title"), "price_rupees": money(v.get("price")), "available": v.get("availableForSale")}
                     for v in variants],
        "description_text": as_text(p.get("descriptionHtml", "")), "media": media,
        "source": f"https://{normalise_store(store)}/products/{handle} (the store's own data through DTJ Store Builder: its storefront "
                  "is behind its password page)",
    }


def read_product(store: str, handle: str, get: Getter = _get, admin: Callable[[dict], dict] | None = None) -> dict:
    try:
        status, final_url, body = get(f"https://{normalise_store(store)}/products/{handle}.js")
    except urllib.error.HTTPError as exc:  # a password page answers with a redirect loop to /password
        if exc.code in (301, 302, 303, 307, 308) or "password" in str(exc).lower():
            return from_admin(store, handle, admin or _admin_call)
        raise
    if "/password" in final_url:
        return from_admin(store, handle, admin or _admin_call)
    if status != 200:
        raise ValueError(f"the store did not show /products/{handle} (HTTP {status})")
    p = json.loads(body.decode("utf-8", "replace"))
    rupees = lambda v: round(v / 100, 2) if isinstance(v, (int, float)) else None  # noqa: E731 - the .js prices are in paise
    media = []
    for m in p.get("media") or [{"media_type": "image", "src": s} for s in p.get("images", [])]:
        src = m.get("src") or (m.get("preview_image") or {}).get("src") or ""
        item = {"type": m.get("media_type", "image"), "file": file_name(src), "url": "https:" + src if src.startswith("//") else src,
                "alt": m.get("alt") or "", "width": m.get("width") or (m.get("preview_image") or {}).get("width"),
                "height": m.get("height") or (m.get("preview_image") or {}).get("height")}
        if item["type"] == "video":
            item["sources"] = [s.get("url") for s in m.get("sources", []) if s.get("url")]
        media.append(item)
    return {
        "store": normalise_store(store), "handle": p.get("handle", handle), "title": p.get("title"),
        "price_rupees": rupees(p.get("price")), "compare_at_price_rupees": rupees(p.get("compare_at_price")),
        "available": p.get("available"), "vendor": p.get("vendor"), "type": p.get("type"), "tags": p.get("tags", []),
        "options": [o.get("name") if isinstance(o, dict) else o for o in p.get("options", [])],
        "variants": [{"title": v.get("title"), "price_rupees": rupees(v.get("price")), "available": v.get("available")}
                     for v in p.get("variants", [])],
        "description_text": as_text(p.get("description", "")), "media": media,
        "source": f"https://{normalise_store(store)}/products/{handle} (public product data)",
    }


def main(argv: list[str] | None = None, *, get: Getter = _get, admin: Callable[[dict], dict] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--store", required=True, help="the store's .myshopify.com address")
    ap.add_argument("--handle", required=True, help="the product handle (the part after /products/ in its link)")
    ap.add_argument("--client", required=True, help="the client folder (created if missing)")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    client = Path(args.client)
    try:
        product = read_product(args.store, args.handle, get, admin)
    except (OSError, ValueError) as exc:
        print(f"could not read the product: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - behind a password and DTJ Store Builder could not read it (not installed, not deployed)
        print(f"could not read the product: the store is behind its password page and DTJ Store Builder could not read it either "
              f"({str(exc)[:300]})", file=sys.stderr)
        return 1
    media_dir = client / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    for item in product["media"]:
        if item["type"] != "image" or not item["file"]:
            continue
        try:
            status, _, body = get(item["url"])
            if status == 200 and body:
                (media_dir / item["file"]).write_bytes(body)
                item["downloaded"] = True
        except OSError as exc:
            item["downloaded"] = False
            item["error"] = str(exc)
    (client / "store-product.json").write_text(json.dumps(product, indent=1, ensure_ascii=False), encoding="utf-8")
    pics = [m for m in product["media"] if m["type"] == "image"]
    print(f"{product['title']} | Rs {product['price_rupees']} (compare-at {product['compare_at_price_rupees']}) | "
          f"available {product['available']} | {len(pics)} pictures, {len(product['media']) - len(pics)} other media")
    for m in product["media"]:
        print(f"  {m['type']:6s} {m['file']}  alt: {m['alt'][:60]!r}" + ("" if m.get("downloaded", m["type"] != "image") else "  NOT DOWNLOADED"))
    print(f"written: {client / 'store-product.json'} and {media_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
