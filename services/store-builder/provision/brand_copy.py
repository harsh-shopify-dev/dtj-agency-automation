"""Copy a brand's public Shopify store into another Shopify store (Harsh, 21 Oct 2026: "it has to create the shopify store of it";
his choices: products with pictures and prices, collections, the policy pages; products ACTIVE when the store is behind a password;
one Approve tap per import).

    python -m provision.brand_copy plan --brand https://brand.com --store target.myshopify.com --out <dir>
        read only: the brand's public catalog, collections and policies, and the target's products, collections, policies and
        currency -> <dir>/plan.json and a short summary
    python -m provision.brand_copy apply --out <dir> --approved-by "<name> (Telegram Approve)"
        create what plan.json lists in the target store

What it never does: change or delete anything the target has. A product or collection whose handle is on the target already is left
alone (listed as skipped); a policy is written only where the target's own is empty; nothing is ever deleted (gql's allowlist).
Products go in ACTIVE only when the target's storefront is behind a password (a dev store), else as DRAFT. Prices are the brand's
numbers as its site shows them (never converted or guessed; a product without a price is left out). Every change is one allowlisted
mutation through `shopify store execute` (the CLI's own sign-in for that store; no token in our files) and one action-log row; a
rerun continues where it stopped (<dir>/applied.json). The store's sign-in needs the scopes in SCOPES once:
    shopify store auth -s <store> --scopes <SCOPES>      (a browser page a person approves)
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable
from urllib.parse import unquote, urlparse

from .actionlog import ActionLog
from .cli_gql import make_cli_transport
from .gql import GraphQLClient, GraphQLError, raise_on_user_errors
from .run import CircuitBreaker

API_VERSION = "2026-10"  # the CLI takes 2026-01 to 2027-01 (21 Oct 2026); the inputs below were read from this version's schema
SCOPES = "read_products,write_products,read_publications,write_publications,read_legal_policies,write_legal_policies"
UA = "Mozilla/5.0 (dtj-brand-copy/1; read-only)"
MAX_PAGES = 10            # 2,500 products
MAX_COLLECTIONS = 40      # a catalogue with hundreds of collections (Gymreapers: 250) keeps its first 40 with products
SKIP_COLLECTIONS = {"all", "frontpage"}
POLICIES = {"refund-policy": "REFUND_POLICY", "shipping-policy": "SHIPPING_POLICY", "privacy-policy": "PRIVACY_POLICY",
            "terms-of-service": "TERMS_OF_SERVICE"}
_SCRIPT = re.compile(r"<script\b[\s\S]*?</script>|<style\b[\s\S]*?</style>", re.I)

TARGET = "query Target { shop { name currencyCode myshopifyDomain } publications(first: 20) { nodes { id name } } }"
TARGET_POLICIES = "query TargetPolicies { shop { shopPolicies { type body } } }"  # needs read_legal_policies: read apart
PRODUCT_HANDLES = ("query ProductHandles($after: String) { products(first: 250, after: $after) { nodes { handle } "
                   "pageInfo { hasNextPage endCursor } } }")
COLLECTION_HANDLES = ("query CollectionHandles($after: String) { collections(first: 250, after: $after) { nodes { handle } "
                      "pageInfo { hasNextPage endCursor } } }")
SET_PRODUCT = ("mutation CopyProduct($input: ProductSetInput!) { productSet(input: $input, synchronous: true) { product { id handle } "
               "userErrors { field message code } } }")
CREATE_COLLECTION = ("mutation CopyCollection($collection: CollectionCreateInput!) { collectionCreate(collection: $collection) { "
                     "collection { id handle } userErrors { field message } } }")
PUBLISH = ("mutation Publish($id: ID!, $input: [PublicationInput!]!) { publishablePublish(id: $id, input: $input) { "
           "userErrors { field message } } }")
SET_POLICY = ("mutation SetPolicy($shopPolicy: ShopPolicyInput!) { shopPolicyUpdate(shopPolicy: $shopPolicy) { shopPolicy { type } "
              "userErrors { field message } } }")

Getter = Callable[[str], "tuple[int, str, bytes]"]  # url -> (status, final url, body)


def http_get(url: str) -> tuple[int, str, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.geturl(), r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, url, b""
    except (urllib.error.URLError, OSError):
        return 0, url, b""


def base_url(link: str) -> str:
    link = link.strip()
    if not re.match(r"https?://", link, re.I):
        link = "https://" + link
    host = urlparse(link).netloc.lower()
    if "." not in host:
        raise ValueError(f"{link!r} is not a website address")
    return f"https://{host}"


def _json(get: Getter, url: str) -> dict | None:
    status, _, body = get(url)
    if status != 200:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


def file_name(src: str) -> str:
    """The name the store gives a picture: the last part of its address, without the ?v= version."""
    return unquote(Path(urlparse(src if "//" in src else "https:" + src).path).name)


def clean_html(text: str) -> str:
    return _SCRIPT.sub("", text or "").strip()


# ---------------------------------------------------------------------------------------------------------- a brand that is not on Shopify
# Harsh, 22 Oct 2026 (Senso: a WordPress trade site with product pages and no prices): its products come from its own product pages
# (found through its sitemap), and a product without a price goes in as a hidden draft at 0.00 with the tag dtj-price-needed ("Create
# them as drafts, prices later"); a price is never guessed.
MAX_SITE_PRODUCTS = 150  # Senso has 114 product pages
PRICE_TAG = "dtj-price-needed"
SITE_POLICIES = {
    "PRIVACY_POLICY": ("privacy-policy", "privacy"),
    "TERMS_OF_SERVICE": ("terms-conditions", "terms-and-conditions", "terms-of-service", "terms-of-use"),
    "REFUND_POLICY": ("refund-policy", "return-policy", "refund-and-returns-policy", "returns", "cancellation-refund-policy"),
    "SHIPPING_POLICY": ("shipping-policy", "shipping-delivery-policy", "shipping-and-delivery", "shipping"),
}
_NOT_PRODUCT_PICTURE = re.compile(r"logo|icon|favicon|shape|sprite|placeholder|loader|arrow|badge|payment|flag", re.I)
_RELATED = re.compile(r"Related Products|You may also like|Similar Products|Customers also bought", re.I)
_FEATURES = re.compile(r"feature|benefit|specification|highlight|ingredient|key points|why ", re.I)


def _text(fragment: str) -> str:
    # \ufffd: a character the site's own page could not encode reads as a plain dash rather than a box
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment or "")).replace("\ufffd", "-")).strip()


def _blocks(fragment: str) -> list[str]:
    """The text of a page part, one entry per block (div, p, heading, list item, line break): for pages whose text is not in <p>
    (Senso's policy pages put it straight into <div>s under <h5> headings)."""
    flat = re.sub(r"\s+", " ", clean_html(fragment))  # the page's own line breaks are not blocks
    marked = re.sub(r"<(?:/?(?:div|p|li|ul|ol|section|h[1-6]|table|tr)|br)\b[^>]*>", "\n", flat, flags=re.I)
    return [x for x in (_text(line) for line in marked.split("\n")) if x]


def _meta(page: str, prop: str) -> str | None:
    m = re.search(rf'<meta[^>]+(?:property|name)="{prop}"[^>]+content="([^"]*)"', page, re.I)
    return html.unescape(m.group(1)).strip() if m else None


def _ld_product(page: str) -> dict:
    """schema.org Product from the page's JSON-LD, when it has one (most shops do; Senso's is broken)."""
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>([\s\S]*?)</script>', page, re.I):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        items = data.get("@graph", [data]) if isinstance(data, dict) else data if isinstance(data, list) else []
        for it in items:
            kind = it.get("@type") if isinstance(it, dict) else None
            if kind == "Product" or (isinstance(kind, list) and "Product" in kind):
                return it
    return {}


def site_product_urls(base: str, get: Getter) -> list[str]:
    """Product pages from the site's sitemaps: /product/<x>, /products/<x>, /my-product/<x> and the like."""
    host = urlparse(base).netloc.replace("www.", "")
    queue, seen, pages = [f"{base}/sitemap.xml", f"{base}/sitemap_index.xml", f"{base}/wp-sitemap.xml", f"{base}/product-sitemap.xml"], set(), []
    while queue and len(seen) < 15:
        sm = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        status, _, body = get(sm)
        if status != 200:
            continue
        text = body.decode("utf-8", "replace")
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", text)
        if "<sitemapindex" in text:
            queue += sorted(locs, key=lambda u: "product" not in u)  # the product sitemaps first
        else:
            pages += locs
    found = []
    for u in pages:
        pu = urlparse(u)
        parts = [x for x in pu.path.split("/") if x]
        if pu.netloc.replace("www.", "") == host and len(parts) >= 2 and re.search(r"product", parts[-2], re.I) and u not in found:
            found.append(u)
    return found[:MAX_SITE_PRODUCTS]


def site_product(url: str, page: str, brand_name: str) -> dict | None:
    """One product page as /products.json would show it (one variant), or None when the page names no product."""
    ld = _ld_product(page)
    h1 = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", page, re.I)
    name = str(ld.get("name") or (_text(h1.group(1)) if h1 else "") or _meta(page, "og:title") or "").strip()
    if not name:
        return None
    cut = _RELATED.search(page)
    main = page[:cut.start()] if cut else page
    summary = _text(str(ld.get("description") or "")) or _meta(page, "description") or _meta(page, "og:description") or ""
    features: list[str] = []
    for head in re.finditer(r"<h[2-4][^>]*>([\s\S]*?)</h[2-4]>", main, re.I):
        if _FEATURES.search(_text(head.group(1))):
            section = main[head.end():]
            nxt = re.search(r"<h2[^>]*>", section, re.I)
            section = section[:nxt.start()] if nxt else section
            features = [x for x in (_text(f) for f in re.findall(r"<(?:li|p)[^>]*>([\s\S]*?)</(?:li|p)>", section, re.I)) if 2 < len(x) < 200][:12]
            break
    body = (f"<p>{html.escape(summary)}</p>" if summary else "") + (
        "<ul>" + "".join(f"<li>{html.escape(f)}</li>" for f in features) + "</ul>" if features else "")
    srcs = []
    ld_img = ld.get("image")
    for s in (ld_img if isinstance(ld_img, list) else [ld_img] if ld_img else []):
        srcs.append(s.get("url") if isinstance(s, dict) else s)
    srcs.append(_meta(page, "og:image"))
    found = re.findall(r'<img[^>]+src="([^"]+)"', main, re.I)
    counts = {u: found.count(u) for u in found}
    srcs += [u for u in found if counts[u] < 3]  # a picture repeated three times is an icon (Senso: the feature ticks)
    images, seen = [], set()
    for s in srcs:
        s = html.unescape(str(s or "")).strip()
        if s.startswith("//"):
            s = "https:" + s
        if not s.startswith("https://") or s in seen or _NOT_PRODUCT_PICTURE.search(file_name(s)) or not re.search(r"\.(jpe?g|png|webp)(\?|$)", s, re.I):
            continue
        seen.add(s)
        images.append({"src": s, "alt": name})
    offer = ld.get("offers") or {}
    offer = offer[0] if isinstance(offer, list) and offer else offer
    price = str(offer.get("price") or "") if isinstance(offer, dict) else ""
    price = price if re.fullmatch(r"\d{1,9}(\.\d{1,4})?", price) else ""
    slug = [x for x in urlparse(url).path.split("/") if x][-1].lower()
    handle = slug if re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug) else re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:200]
    return {"handle": handle, "title": name, "body_html": body, "vendor": brand_name, "product_type": "",
            "tags": [] if price else [PRICE_TAG], "options": [{"name": "Title", "position": 1, "values": ["Default Title"]}],
            "variants": [{"option1": "Default Title", "price": price or "0.00", "sku": str(ld.get("sku") or "")}],
            "images": images[:8], "source": url, "price_needed": not price}


def site_policies(base: str, get: Getter) -> dict:
    out = {}
    for ptype, slugs in SITE_POLICIES.items():
        for slug in slugs:
            status, _, body = get(f"{base}/{slug}/")
            if status != 200:
                continue
            page = body.decode("utf-8", "replace")
            m = (re.search(r"<main[^>]*>([\s\S]*?)</main>", page, re.I) or re.search(r"<article[^>]*>([\s\S]*?)</article>", page, re.I)
                 or re.search(r'class="[^"]*entry-content[^"]*"[^>]*>([\s\S]*?)</div>\s*</div>', page, re.I)
                 or re.search(r"</header>([\s\S]*?)<footer", page, re.I))  # a theme without main / article (Senso): the page body
            if not m:
                continue
            blocks = [x for x in (_text(b) for b in re.findall(r"<(?:p|li|h[2-4])[^>]*>([\s\S]*?)</(?:p|li|h[2-4])>", clean_html(m.group(1)), re.I)) if x]
            if len(" ".join(blocks)) <= 200:
                blocks = _blocks(m.group(1))
            text = "".join(f"<p>{html.escape(b)}</p>" for b in blocks)
            if len(" ".join(blocks)) > 200:
                out[ptype] = {"body": text, "source": f"{base}/{slug}/"}
                break
    return out


def read_site(link: str, get: Getter = http_get, pause: Callable[[], None] = lambda: time.sleep(0.25)) -> dict:
    """A brand whose website is not a Shopify store: its product pages, read one by one, and its policy pages."""
    base = base_url(link)
    status, _, body = get(base + "/")
    home = body.decode("utf-8", "replace") if status == 200 else ""
    title = re.search(r"<title[^>]*>([\s\S]*?)</title>", home, re.I)
    name = _meta(home, "og:site_name") or (_text(title.group(1)).split("|")[-1].split(" - ")[-1].strip() if title else "") or urlparse(base).netloc
    products, unreadable = [], []
    for url in site_product_urls(base, get):
        st, _, pb = get(url)
        pause()
        item = site_product(url, pb.decode("utf-8", "replace"), name) if st == 200 else None
        if item and item["handle"] not in {x["handle"] for x in products}:
            products.append(item)
        elif not item:
            unreadable.append(url)
    if not products:
        raise ValueError(f"{base} shows no product pages to read (no Shopify catalogue, and no /product/... pages in its sitemap)")
    if len(products) >= 5:  # a picture on 4+ different products is a site badge or banner, not a product photo (Senso: wc-2.png,
        shared = {i["src"] for p in products for i in p["images"]}  # 100-natural.png, Easily-soluble.png)
        common = {s for s in shared if sum(any(i["src"] == s for i in p["images"]) for p in products) >= 4}
        for p in products:
            own = [i for i in p["images"] if i["src"] not in common]
            p["images"] = own or p["images"][:1]
    return {"base": base, "name": name, "platform": "website", "products": products, "collections": [], "more_collections": 0,
            "policies": site_policies(base, get), "unreadable_pages": unreadable}


# ---------------------------------------------------------------------------------------------------------- reading the brand
def read_brand(link: str, get: Getter = http_get, pause: Callable[[], None] = lambda: time.sleep(0.25)) -> dict:
    base = base_url(link)
    products: list[dict] = []
    for page in range(1, MAX_PAGES + 1):
        items = (_json(get, f"{base}/products.json?limit=250&page={page}") or {}).get("products") or []
        products += items
        pause()
        if len(items) < 250:
            break
    if not products:
        return read_site(link, get, pause)  # not a Shopify catalogue: the brand's own product pages instead
    known = {p.get("handle") for p in products}
    collections, more = [], 0
    for c in (_json(get, f"{base}/collections.json?limit=250") or {}).get("collections") or []:
        if c.get("handle") in SKIP_COLLECTIONS:
            continue
        if len(collections) >= MAX_COLLECTIONS:
            more += 1
            continue
        handles: list[str] = []
        for page in range(1, 5):
            items = (_json(get, f"{base}/collections/{c['handle']}/products.json?limit=250&page={page}") or {}).get("products") or []
            handles += [p["handle"] for p in items if p.get("handle") in known]
            pause()
            if len(items) < 250:
                break
        if handles:
            collections.append({"handle": c["handle"], "title": html.unescape(c.get("title") or c["handle"]),
                                "description_html": clean_html(c.get("body_html") or ""), "products": handles})
    policies = {}
    for name, ptype in POLICIES.items():
        status, final, body = get(f"{base}/policies/{name}")
        page = body.decode("utf-8", "replace") if status == 200 else ""
        m = re.search(r'<div class="shopify-policy__body">\s*<div class="rte">([\s\S]*?)</div>\s*</div>', page)
        text = clean_html(m.group(1)) if m else ""
        if text and len(re.sub(r"<[^>]+>", "", text).strip()) > 40:
            policies[ptype] = {"body": text, "source": f"{base}/policies/{name}"}
        pause()
    return {"base": base, "products": products, "collections": collections, "more_collections": more, "policies": policies}


# ---------------------------------------------------------------------------------------------------------- the plan
def product_input(p: dict, status: str) -> dict | None:
    """productSet's input for one public product (as /products.json shows it), or None when it has no price."""
    variants = p.get("variants") or []
    if not variants or not all(v.get("price") not in (None, "") for v in variants):
        return None  # no price, no product: never guess one
    options = [o for o in p.get("options") or [] if o.get("name")] or [{"name": "Title", "values": ["Default Title"]}]
    out_variants = []
    for v in variants:
        values = [{"optionName": o["name"], "name": str(v.get(f"option{i}") or "Default Title")} for i, o in enumerate(options, 1)
                  if i <= 3]
        one = {"optionValues": values, "price": str(v["price"]), "inventoryItem": {"tracked": False}}
        cap = v.get("compare_at_price")
        if cap and float(cap) > float(v["price"]):
            one["compareAtPrice"] = str(cap)
        if v.get("sku"):
            one["sku"] = v["sku"]
        out_variants.append(one)
    used = {o["name"]: [] for o in options}
    for v in out_variants:
        for ov in v["optionValues"]:
            if ov["name"] not in used[ov["optionName"]]:
                used[ov["optionName"]].append(ov["name"])
    tags = p.get("tags") or []
    tags = [t.strip() for t in tags.split(",")] if isinstance(tags, str) else tags
    inp = {
        "title": html.unescape(p.get("title") or p["handle"]), "handle": p["handle"], "status": status,
        "descriptionHtml": clean_html(p.get("body_html") or ""),
        "productOptions": [{"name": name, "position": i, "values": [{"name": x} for x in values]}
                           for i, (name, values) in enumerate(used.items(), 1)],
        "variants": out_variants,
        "files": [{"originalSource": ("https:" + img["src"]) if str(img["src"]).startswith("//") else img["src"],
                   "contentType": "IMAGE", "alt": html.unescape(img.get("alt") or p.get("title") or "")[:500], "filename": file_name(img["src"])}
                  for img in p.get("images") or [] if img.get("src")],
    }
    for src, dst in (("vendor", "vendor"), ("product_type", "productType")):
        if p.get(src):
            inp[dst] = p[src]
    if [t for t in tags if t]:
        inp["tags"] = [t for t in tags if t]
    return inp


def read_target(client, get: Getter = http_get) -> dict:
    data = client.execute(TARGET)["data"]
    shop = data["shop"]
    try:
        policies = client.execute(TARGET_POLICIES)["data"]["shop"]["shopPolicies"]
        empty = sorted(p["type"] for p in policies if not (p.get("body") or "").strip())
    except GraphQLError:
        empty = None  # this store's sign-in cannot read policies yet: none are copied, and the plan says why
    online = next((p["id"] for p in data["publications"]["nodes"] if p.get("name") == "Online Store"), None)

    def handles(query: str, field: str) -> set[str]:
        found, after = set(), None
        for _ in range(40):
            page = client.execute(query, {"after": after})["data"][field]
            found |= {n["handle"] for n in page["nodes"]}
            if not page["pageInfo"]["hasNextPage"]:
                break
            after = page["pageInfo"]["endCursor"]
        return found

    status, final, _ = get(f"https://{shop['myshopifyDomain']}/")
    return {"store": shop["myshopifyDomain"], "name": shop["name"], "currency": shop["currencyCode"],
            "password": "/password" in (final or ""), "storefront_status": status, "online_store": online,
            "empty_policies": empty,
            "products": sorted(handles(PRODUCT_HANDLES, "products")), "collections": sorted(handles(COLLECTION_HANDLES, "collections"))}


def make_plan(brand: dict, target: dict, brand_currency: str | None = None) -> dict:
    needs_price = [p["handle"] for p in brand["products"] if p.get("price_needed")]
    status = "ACTIVE" if target["password"] and not needs_price else "DRAFT"
    have_p, have_c = set(target["products"]), set(target["collections"])
    products, skipped, no_price = [], [], []
    for p in brand["products"]:
        if p.get("handle") in have_p:
            skipped.append(p["handle"])
            continue
        inp = product_input(p, status)
        if inp is None:
            no_price.append(p.get("handle"))
            continue
        products.append(inp)
    planned = {p["handle"] for p in products}
    collections = [dict(c, products=[h for h in c["products"] if h in planned]) for c in brand["collections"] if c["handle"] not in have_c]
    empty = target["empty_policies"] or []
    policies = [{"type": t, **v} for t, v in brand["policies"].items() if t in empty]
    notes = []
    if target["empty_policies"] is None and brand["policies"]:
        notes.append(f"the policy pages are left out: this store's sign-in cannot read policies yet (shopify store auth -s "
                     f"{target['store']} --scopes {SCOPES}, then plan again)")
    if brand_currency and target["currency"] and brand_currency != target["currency"]:
        notes.append(f"prices are the brand's numbers in {brand_currency}; {target['store']} sells in {target['currency']} (not converted)")
    if needs_price:
        notes.append(f"the brand's website shows no price for {len(needs_price)} products: everything goes in as hidden drafts, those at "
                     f"0.00 with the tag {PRICE_TAG}; set each price in Shopify admin before they show")
    if not target["password"]:
        notes.append(f"{target['store']} is open to the public (no password page), so the products go in as DRAFT")
    if brand.get("unreadable_pages"):
        notes.append(f"{len(brand['unreadable_pages'])} product pages could not be read and are left out")
    if brand.get("more_collections"):
        notes.append(f"{brand['more_collections']} more collections left out (the first {MAX_COLLECTIONS} with products are copied)")
    if not target["online_store"] and status == "ACTIVE":
        notes.append("no Online Store channel found: products are created but not shown on the storefront")
    return {"brand": brand["base"], "target": {k: target[k] for k in ("store", "name", "currency", "password", "online_store")},
            "status": status, "products": products, "collections": collections, "policies": policies,
            "skipped": {"products_on_target": skipped, "no_price": no_price,
                        "collections_on_target": [c["handle"] for c in brand["collections"] if c["handle"] in have_c],
                        "policies_not_empty": [t for t in brand["policies"] if target["empty_policies"] is not None and t not in empty]},
            "notes": notes}


def summary(plan: dict) -> str:
    return (f"{len(plan['products'])} products ({sum(len(p['files']) for p in plan['products'])} pictures, "
            f"{sum(len(p['variants']) for p in plan['products'])} variants), {len(plan['collections'])} collections, "
            f"{len(plan['policies'])} policy pages, as {plan['status']}")


# ---------------------------------------------------------------------------------------------------------- applying it
def apply(plan: dict, client, state_path: Path, log: ActionLog, approved_by: str, out=print) -> dict:
    """Creates the plan in the target; returns what was done. Resumes from state_path; stops after 3 failures of one step in a row."""
    if not approved_by.strip():
        raise ValueError("an import needs the name of who approved it")
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    for key in ("collections", "products", "policies", "failed"):
        state.setdefault(key, {} if key != "policies" else [])
    save = lambda: state_path.write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8")  # noqa: E731
    breaker = CircuitBreaker()
    publish_to = [{"publicationId": plan["target"]["online_store"]}] if plan["target"].get("online_store") and plan["status"] == "ACTIVE" else []
    target = plan["target"]["store"]

    def step(kind: str, key: str, fn) -> str | None:
        try:
            got = fn()
            breaker.ok(kind)
            state["failed"].pop(f"{kind}:{key}", None)
            return got
        except GraphQLError as exc:
            state["failed"][f"{kind}:{key}"] = str(exc)[:300]
            save()
            log.record(tier=2, mode="approve", target=target, action=f"copy {kind} {key}", reason="brand copy", result="failed",
                       approved_by=approved_by, error=str(exc)[:300])
            if breaker.failed(kind):
                raise SystemExit(f"stopped: 3 {kind} copies failed in a row (last: {exc}). Done so far is kept in {state_path}")
            return None

    for c in plan["collections"]:
        if c["handle"] in state["collections"]:
            continue

        def make(c=c):
            body = client.execute(CREATE_COLLECTION, {"collection": {"title": c["title"], "handle": c["handle"],
                                                                     "descriptionHtml": c["description_html"]}})
            cid = raise_on_user_errors(body, "collectionCreate")["collection"]["id"]
            if publish_to:
                raise_on_user_errors(client.execute(PUBLISH, {"id": cid, "input": publish_to}), "publishablePublish")
            return cid
        cid = step("collection", c["handle"], make)
        if cid:
            state["collections"][c["handle"]] = cid
            save()
            log.record(tier=2, mode="approve", target=target, action=f"copy collection {c['handle']}", reason="brand copy",
                       result="success", approved_by=approved_by, after={"id": cid})
    member = {}
    for c in plan["collections"]:
        for h in c["products"]:
            if c["handle"] in state["collections"]:
                member.setdefault(h, []).append(state["collections"][c["handle"]])
    for i, p in enumerate(plan["products"], 1):
        if p["handle"] in state["products"]:
            continue

        def make(p=p):
            inp = dict(p, collections=member.get(p["handle"], []))
            pid = raise_on_user_errors(client.execute(SET_PRODUCT, {"input": inp}), "productSet")["product"]["id"]
            if publish_to:
                raise_on_user_errors(client.execute(PUBLISH, {"id": pid, "input": publish_to}), "publishablePublish")
            return pid
        pid = step("product", p["handle"], make)
        if pid:
            state["products"][p["handle"]] = pid
            save()
            log.record(tier=2, mode="approve", target=target, action=f"copy product {p['handle']}", reason="brand copy",
                       result="success", approved_by=approved_by, after={"id": pid, "status": plan["status"]})
            out(f"  product {i} of {len(plan['products'])}: {p['handle']}")
    for pol in plan["policies"]:
        if pol["type"] in state["policies"]:
            continue
        done = step("policy", pol["type"], lambda pol=pol: raise_on_user_errors(
            client.execute(SET_POLICY, {"shopPolicy": {"type": pol["type"], "body": pol["body"]}}), "shopPolicyUpdate"))
        if done is not None:
            state["policies"].append(pol["type"])
            save()
            log.record(tier=2, mode="approve", target=target, action=f"copy policy {pol['type']}", reason="brand copy (the target's was empty)",
                       result="success", approved_by=approved_by, evidence={"source": pol["source"]})
    return {"products": len(state["products"]), "collections": len(state["collections"]), "policies": len(state["policies"]),
            "failed": state["failed"], "planned": {"products": len(plan["products"]), "collections": len(plan["collections"]),
                                                   "policies": len(plan["policies"])}}


def cli_client(store: str) -> GraphQLClient:
    return GraphQLClient(store, API_VERSION, lambda: "", dry_run=False, transport=make_cli_transport(store, API_VERSION))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("plan")
    pl.add_argument("--brand", required=True)
    pl.add_argument("--store", required=True)
    pl.add_argument("--out", required=True)
    pl.add_argument("--brand-currency", default="")
    ap_ = sub.add_parser("apply")
    ap_.add_argument("--out", required=True)
    ap_.add_argument("--approved-by", required=True)
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        if a.cmd == "plan":
            brand = read_brand(a.brand)
            target = read_target(cli_client(a.store))
            plan = make_plan(brand, target, a.brand_currency or None)
            (out / "plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
            print(json.dumps({"summary": summary(plan), "notes": plan["notes"], "skipped": {k: len(v) for k, v in plan["skipped"].items()}},
                             ensure_ascii=False))
            return 0
        plan = json.loads((out / "plan.json").read_text(encoding="utf-8"))
        log = ActionLog(out / "action-log.jsonl", plan["target"]["store"], automation="brand-copy")
        done = apply(plan, cli_client(plan["target"]["store"]), out / "applied.json", log, a.approved_by)
        print(json.dumps(done, ensure_ascii=False))
        return 0 if not done["failed"] else 1
    except (ValueError, GraphQLError) as exc:
        print(f"stopped: {exc}", file=sys.stderr)
        if "ACCESS_DENIED" in str(exc) or "scope" in str(exc).lower():
            print(f"the store's sign-in needs these permissions once: shopify store auth -s <store> --scopes {SCOPES}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
