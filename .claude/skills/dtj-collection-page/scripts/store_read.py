"""Read-only: one collection of a store with everything a product card shows (pictures, prices, compare-at prices, availability, tags, shade
swatches, the reviews metafields), through `shopify store execute` WITHOUT --allow-mutations (the CLI refuses anything but a query).
Used by preview_collection.py (the local preview) and check_collection_live.py (the truth the draft page is checked against)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "services" / "store-builder"))
from provision.theme import cli_exe  # noqa: E402

QUERY = """query($h: String!) { collectionByHandle(handle: $h) { title handle descriptionHtml productsCount { count }
  products(first: 50) { nodes { id handle title tags
    images(first: 30) { nodes { id url width height altText } }
    variants(first: 100) { nodes { id title price compareAtPrice availableForSale image { id } } }
    options { name optionValues { name swatch { color image { image { url } } } } }
    rating: metafield(namespace: "reviews", key: "rating") { value }
    count: metafield(namespace: "reviews", key: "rating_count") { value }
  } } } }"""


def read_collection(store: str, handle: str) -> dict:
    tmp = Path(tempfile.mkdtemp())
    (tmp / "q.graphql").write_text(QUERY, encoding="utf-8")
    (tmp / "v.json").write_text(json.dumps({"h": handle}), encoding="utf-8")
    out = tmp / "out.json"
    r = subprocess.run([cli_exe("shopify"), "store", "execute", "-s", store, "--no-input", "-j", "--query-file", str(tmp / "q.graphql"),
                        "--variable-file", str(tmp / "v.json"), "--output-file", str(out)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=180, stdin=subprocess.DEVNULL, cwd=tempfile.gettempdir())
    if r.returncode != 0 or not out.exists():
        sys.exit(f"could not read the collection (read-only CLI query; sign the CLI in with `shopify store auth -s {store} --scopes read_products` "
                 f"if it asks): {(r.stdout + r.stderr)[-800:]}")
    data = json.loads(out.read_text(encoding="utf-8"))
    coll = data.get("data", data)["collectionByHandle"]
    if not coll:
        sys.exit(f"no collection {handle!r} on {store}")
    return coll


def expected_card(p: dict) -> dict:
    """What the DTJ Product List card must show for this product (its default settings on a collection page)."""
    variants = p["variants"]["nodes"]
    first = next((v for v in variants if v["availableForSale"]), variants[0])
    price, compare = float(first["price"] or 0), float(first["compareAtPrice"] or 0)
    rating = json.loads(p["rating"]["value"]) if p.get("rating") else None
    count = int(p["count"]["value"]) if p.get("count") and str(p["count"]["value"]).strip() != "" else None
    shows_rating = bool(rating) and (count is None or count >= 1)  # pf_hide_no_reviews: a placeholder rating with 0 reviews is never shown
    tags = [t.strip().lower() for t in p["tags"]]
    badge = "Best Seller" if "best-seller" in tags else ("New Launches" if "new" in tags else None)
    off = round((compare - price) * 100 / compare) if compare > price > 0 else 0
    return {"handle": p["handle"], "rating": round(float(rating["value"]), 1) if shows_rating else None, "count": count if shows_rating else None,
            "swatches": any(v.get("swatch") for o in p["options"] for v in o["optionValues"]), "badge": badge,
            "off": off, "button": "Add to cart" if first["availableForSale"] else "Sold out"}


COLLS = """query($q: String!) { collections(first: 20, query: $q) { nodes { handle title image { url width height } } } }"""


def read_collections(store: str, handles: list[str]) -> dict:
    """Read-only: the collections a links row shows (handle -> title, address, picture), in the order asked."""
    if not handles:
        return {}
    tmp = Path(tempfile.mkdtemp())
    (tmp / "q.graphql").write_text(COLLS, encoding="utf-8")
    (tmp / "v.json").write_text(json.dumps({"q": " OR ".join(f"handle:{h}" for h in handles)}), encoding="utf-8")
    out = tmp / "out.json"
    r = subprocess.run([cli_exe("shopify"), "store", "execute", "-s", store, "--no-input", "-j", "--query-file", str(tmp / "q.graphql"),
                        "--variable-file", str(tmp / "v.json"), "--output-file", str(out)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=180, stdin=subprocess.DEVNULL, cwd=tempfile.gettempdir())
    if r.returncode != 0 or not out.exists():
        sys.exit(f"could not read the collections (read-only CLI query): {(r.stdout + r.stderr)[-600:]}")
    data = json.loads(out.read_text(encoding="utf-8"))
    nodes = {c["handle"]: c for c in data.get("data", data)["collections"]["nodes"]}
    return {h: nodes[h] for h in handles if h in nodes}
