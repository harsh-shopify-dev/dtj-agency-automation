"""Copy a Shopify storefront's PUBLIC catalog (products.json) and images to local files.

    python -m provision.import_catalog sagarchudesara.com --out .work/import/sagarchudesara

Reads only what any visitor can read. Polite: one request at a time with a pause, identifies itself,
caps image size, skips anything that is not an image. Writes raw JSON, images and a product sheet
that matches schemas/product-sheet.schema.json. Output goes under .work/ (git-ignored): this is a
private test copy and must not be published or committed.
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

UA = "DTJ-catalog-copy/1.0 (agency test copy; read-only)"
HANDLE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_PAGES = 10

Getter = Callable[[str], "tuple[bytes, str]"]  # url -> (body, content-type)


def http_get(url: str) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read(MAX_IMAGE_BYTES + 1)
        return body, resp.headers.get("Content-Type", "")


def fetch_products(domain: str, get: Getter = http_get, sleep=time.sleep) -> list[dict]:
    out: list[dict] = []
    for page in range(1, MAX_PAGES + 1):
        body, _ = get(f"https://{domain}/products.json?limit=250&page={page}")
        batch = json.loads(body).get("products", [])
        if not batch:
            break
        out += batch
        sleep(0.5)
    return out


def safe_handle(product: dict) -> str:
    """Keep the original handle when it is plain ASCII; otherwise a neutral id-based one (rename later)."""
    handle = product.get("handle", "")
    return handle if HANDLE.match(handle) else f"imported-{product['id']}"


def image_name(handle: str, n: int, url: str) -> str | None:
    ext = Path(urlparse(url).path).suffix.lower()
    short = handle[:60].rstrip("-")
    return f"{short}-{n}{ext}" if ext in EXTS else None


_SCRIPT = re.compile(r"<script\b[\s\S]*?</script>", re.I)


def build_sheet(products: list[dict], files: dict[str, dict[str, str]]) -> dict:
    """files: {source image url: local file name} per product id, keyed as {str(product id): {url: name}}."""
    items = []
    for p in products:
        variant = (p.get("variants") or [{}])[0]
        if not variant.get("price"):
            continue  # no price, no product: never guess one
        handle = safe_handle(p)
        item = {"handle": handle, "title": p["title"], "price": variant["price"]}
        if p.get("body_html"):
            item["description_html"] = _SCRIPT.sub("", p["body_html"])
        for src, dst in (("vendor", "vendor"), ("product_type", "product_type")):
            if p.get(src):
                item[dst] = p[src]
        tags = p.get("tags")
        tags = [t.strip() for t in tags.split(",")] if isinstance(tags, str) else (tags or [])
        if tags:
            item["tags"] = [t for t in tags if t]
        cap = variant.get("compare_at_price")
        if cap and float(cap) > float(variant["price"]):
            item["compare_at_price"] = cap
        if variant.get("sku"):
            item["sku"] = variant["sku"]
        images = []
        for img in p.get("images", []):
            name = files.get(str(p["id"]), {}).get(img["src"])
            if name:
                images.append({"file": name, "alt": img.get("alt") or p["title"]})  # alt falls back to the title
        if images:
            item["images"] = images
        items.append(item)
    return {"products": items}


def run(domain: str, out_dir: Path, get: Getter = http_get, sleep=time.sleep) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    image_dir = out_dir / "images"
    image_dir.mkdir(exist_ok=True)
    products = fetch_products(domain, get, sleep)
    (out_dir / "products.raw.json").write_text(json.dumps(products, indent=2, ensure_ascii=False), encoding="utf-8")

    files: dict[str, dict[str, str]] = {}
    skipped: list[str] = []
    for p in products:
        handle = safe_handle(p)
        for n, img in enumerate(p.get("images", []), start=1):
            name = image_name(handle, n, img["src"])
            if not name:
                skipped.append(f"{img['src']} (unsupported type)")
                continue
            try:
                body, ctype = get(img["src"])
            except Exception as exc:  # network trouble on one image must not stop the rest
                skipped.append(f"{img['src']} ({exc})")
                continue
            if not ctype.startswith("image/") or len(body) > MAX_IMAGE_BYTES or not body:
                skipped.append(f"{img['src']} (not an image or too large)")
                continue
            (image_dir / name).write_bytes(body)
            files.setdefault(str(p["id"]), {})[img["src"]] = name
            sleep(0.3)

    sheet = build_sheet(products, files)
    (out_dir / "product-sheet.json").write_text(json.dumps(sheet, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "SOURCE.md").write_text(
        f"Source: https://{domain} public catalog (/products.json), copied {time.strftime('%Y-%m-%d')}.\n"
        "Private test copy for the DTJ dev store. Do not publish, commit or reuse for anyone else.\n"
        "Only public, published products are included. Videos and unpublished products are not.\n", encoding="utf-8")
    return {"products": len(sheet["products"]), "images": sum(len(v) for v in files.values()),
            "skipped_images": skipped, "renamed_handles": [safe_handle(p) for p in products if safe_handle(p) != p.get("handle")]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("domain")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    print(json.dumps(run(args.domain, Path(args.out)), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
