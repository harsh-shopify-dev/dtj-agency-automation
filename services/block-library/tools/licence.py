"""Read or flip the DTJ licence flag (app-data metafield dtj.licence, stored on the app INSTALLATION) on one store.

    python tools/licence.py --shop NAME.myshopify.com --status
    python tools/licence.py --shop NAME.myshopify.com --set inactive --approved-by Harsh

How it gets in: the app's own client credentials grant. This only works for stores in the SAME Shopify organization as
the app. A client's store outside our org needs a hosted service that catches the install (authorization code grant)
and keeps that client's token (see docs/block-library-design.md).
Secrets: the client secret is read from the environment variable DTJ_BLOCKS_CLIENT_SECRET. It is never printed or logged.
Changing the flag is a tier 2 action: it needs --approved-by, and every change appends a row to the log.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_ENV = "DTJ_BLOCKS_CLIENT_SECRET"
API_VERSION = "2026-07"
STATUSES = ("active", "inactive")
_SHOP = re.compile(r"^[a-z0-9][a-z0-9-]*\.myshopify\.com$")
_SENSITIVE = re.compile(r"secret|token|authorization", re.I)

READ = 'query { shop { id } currentAppInstallation { id app { handle } licence: metafield(namespace: "dtj", key: "licence") { value } } }'
WRITE = """mutation SetLicence($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { id namespace key value }
    userErrors { field message code }
  }
}"""
ALLOWED_MUTATIONS = {"metafieldsSet"}  # nothing else can be sent from this tool


class LicenceError(Exception):
    pass


def client_id(toml_path: Path = ROOT / "shopify.app.toml") -> str:
    match = re.search(r'^client_id\s*=\s*"([0-9a-f]+)"', toml_path.read_text(encoding="utf-8"), re.M)
    if not match:
        raise LicenceError("client_id not found in shopify.app.toml (run `shopify app config link`)")
    return match.group(1)


def post_json(url: str, payload: dict, headers: dict | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read() or b"{}")
        except ValueError:
            return exc.code, {}


def get_token(shop: str, cid: str, secret: str, post=post_json) -> str:
    status, body = post(f"https://{shop}/admin/oauth/access_token",
                        {"client_id": cid, "client_secret": secret, "grant_type": "client_credentials"})
    token = body.get("access_token")
    if status != 200 or not token:
        reason = str(body.get("error_description") or body.get("error") or f"HTTP {status}")
        if "shop_not_permitted" in str(body.get("error")) or "cannot be performed" in reason or "not permitted" in reason:
            reason += " (the app and the store must be in the same Shopify organization, and the app must be installed)"
        raise LicenceError(f"could not get a token: {reason}")
    return token


def graphql(shop: str, token: str, query: str, variables: dict | None = None, post=post_json) -> dict:
    if query.lstrip().startswith("mutation"):
        fields = re.findall(r"^\s{2}(\w+)\(", query, re.M)
        if not fields or any(f not in ALLOWED_MUTATIONS for f in fields) or "delete" in query.lower():
            raise LicenceError("only metafieldsSet can be sent from this tool")
    status, body = post(f"https://{shop}/admin/api/{API_VERSION}/graphql.json",
                        {"query": query, "variables": variables or {}}, {"X-Shopify-Access-Token": token})
    if status in (401, 403):
        raise LicenceError(f"HTTP {status}: the token was refused")
    if status != 200 or body.get("errors"):
        raise LicenceError(f"GraphQL failed: HTTP {status} {json.dumps(body.get('errors'))[:300]}")
    return body["data"]


def read_status(shop: str, token: str, post=post_json) -> dict:
    data = graphql(shop, token, READ, post=post)
    install = data["currentAppInstallation"]
    return {"install_id": install["id"], "licence": (install["licence"] or {}).get("value"), "app": install["app"]["handle"]}


def set_status(shop: str, token: str, value: str, post=post_json) -> dict:
    if value not in STATUSES:
        raise LicenceError(f"status must be one of {STATUSES}")
    current = read_status(shop, token, post)
    # app-data metafield: owner is the app installation, plain namespace (Shopify isolates it per app and per store)
    data = graphql(shop, token, WRITE, {"metafields": [{"ownerId": current["install_id"], "namespace": "dtj", "key": "licence",
                                                          "type": "single_line_text_field", "value": value}]}, post=post)
    errors = data["metafieldsSet"]["userErrors"]
    if errors:
        raise LicenceError("; ".join(f"{e.get('field')}: {e['message']}" for e in errors))
    return {"before": current["licence"], "after": value}


def log_row(path: Path, shop: str, change: dict, approved_by: str, result: str, error: str | None = None) -> dict:
    row = {"ts": datetime.now(timezone.utc).isoformat(), "automation": "block-library", "tier": 2, "target": f"{shop} dtj.licence",
           "action": "set licence flag", "before": change.get("before"), "after": change.get("after"), "approved_by": approved_by,
           "result": result, "error": error}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    return row


def main(argv: list[str] | None = None, env=os.environ, post=post_json) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--shop", required=True)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--status", action="store_true", help="read the current flag (read only)")
    group.add_argument("--set", choices=STATUSES)
    ap.add_argument("--approved-by")
    ap.add_argument("--log", default=str(ROOT.parents[1] / ".work" / "out" / "licence-log.jsonl"))
    args = ap.parse_args(argv)
    if not _SHOP.match(args.shop):
        print("BLOCKED: --shop must look like name.myshopify.com", file=sys.stderr)
        return 2
    if args.set and not args.approved_by:
        print("BLOCKED: changing the flag needs --approved-by NAME (tier 2)", file=sys.stderr)
        return 2
    secret = env.get(SECRET_ENV)
    if not secret:
        print(f"BLOCKED: {SECRET_ENV} is not set in the environment", file=sys.stderr)
        return 2
    try:
        token = get_token(args.shop, client_id(), secret, post)
        if args.status:
            print(json.dumps(read_status(args.shop, token, post)))
            return 0
        try:
            change = set_status(args.shop, token, args.set, post)
        except LicenceError as exc:
            log_row(Path(args.log), args.shop, {"after": args.set}, args.approved_by, "failed", str(exc))
            raise
        log_row(Path(args.log), args.shop, change, args.approved_by, "success")
        print(json.dumps(change))
        return 0
    except LicenceError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
