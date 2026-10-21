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
        raise ValueError(f"{base} shows no public products (/products.json): it is not a Shopify store, or it hides its catalogue")
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
    status = "ACTIVE" if target["password"] else "DRAFT"
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
    if status == "DRAFT":
        notes.append(f"{target['store']} is open to the public (no password page), so the products go in as DRAFT")
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
                       approver=approved_by, error=str(exc)[:300])
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
                       result="success", approver=approved_by, after={"id": cid})
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
                       result="success", approver=approved_by, after={"id": pid, "status": plan["status"]})
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
                       result="success", approver=approved_by, evidence={"source": pol["source"]})
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
