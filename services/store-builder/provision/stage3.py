"""Stage 3: create DRAFT products with images on the target store. Tier 2: needs a named approver.

    python -m provision.stage3 --brand brand.json --products products.json --images ./images --out ./out --approved-by NAME

Without --approved-by (or with the kill switch off, DRY_RUN on, or shadow mode) it refuses and touches nothing.
Existing handles are never modified: same handle and price = skipped, same handle but different price = reported.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import secrets
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from . import config, products
from .actionlog import ActionLog
from .cli_gql import make_cli_transport
from .gql import AuthError, GraphQLClient, GraphQLError, raise_on_user_errors
from .run import CircuitBreaker, InputError, validate

LIST_EXISTING = "query Existing($after: String) { products(first: 100, after: $after) { nodes { handle variants(first: 1) { nodes { price } } } pageInfo { hasNextPage endCursor } } }"


class UploadError(Exception):
    pass


def multipart(fields: list[tuple[str, str]], file_name: str, data: bytes, content_type: str) -> tuple[bytes, str]:
    boundary = "----dtj" + secrets.token_hex(12)
    parts = []
    for name, value in fields:
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
                 f"Content-Type: {content_type}\r\n\r\n".encode() + data + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def http_post(url: str, body: bytes, content_type: str) -> int:
    req = urllib.request.Request(url, data=body, headers={"Content-Type": content_type}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


def upload_staged(target: dict, path: Path, post: Callable[[str, bytes, str], int] = http_post) -> None:
    if urlparse(target["url"]).scheme != "https":
        raise UploadError("staged upload target is not https; refusing")
    fields = [(p["name"], p["value"]) for p in target.get("parameters", [])]  # parameters first, file last
    body, ctype = multipart(fields, path.name, path.read_bytes(), mimetypes.guess_type(path.name)[0] or "application/octet-stream")
    status = post(target["url"], body, ctype)
    if not 200 <= status < 300:
        raise UploadError(f"upload of {path.name} failed with HTTP {status}")


def existing_products(client: GraphQLClient) -> dict[str, str]:
    found: dict[str, str] = {}
    after = None
    while True:
        data = client.execute(LIST_EXISTING, {"after": after})["data"]["products"]
        for node in data["nodes"]:
            nodes = node["variants"]["nodes"]
            found[node["handle"]] = nodes[0]["price"] if nodes else ""
        if not data["pageInfo"]["hasNextPage"]:
            return found
        after = data["pageInfo"]["endCursor"]


def create_products(client: GraphQLClient, cfg: config.Config, sheet: dict, image_dir: Path, log: ActionLog,
                    approved_by: str | None, post=http_post) -> dict:
    decision = cfg.decide(2, approved_by)
    target = cfg.store_domain or "unknown store"
    report: dict = {"created": [], "skipped": [], "differs": [], "failed": [], "stopped": None}
    if not decision.allowed:
        log.record(tier=2, mode=cfg.mode, target=target, action="create draft products", reason="stage 3",
                   result="blocked", error=decision.reason)
        report["stopped"] = decision.reason
        return report
    approval = {"approved_by": approved_by, "approved_at": datetime.now(timezone.utc).isoformat()}
    breaker = CircuitBreaker()
    try:
        existing = existing_products(client)
    except GraphQLError as exc:  # includes AuthError: stop cleanly, change nothing
        log.record(tier=2, mode=cfg.mode, target=target, action="create draft products", reason="stage 3: could not read existing products",
                   result="failed", error=str(exc)[:500], **approval)
        report["stopped"] = f"auth problem: {exc}" if isinstance(exc, AuthError) else f"could not read the store: {exc}"
        return report

    for item in sheet["products"]:
        handle = item["handle"]
        if handle in existing:
            same = existing[handle] == item["price"]
            (report["skipped"] if same else report["differs"]).append(handle)
            log.record(tier=2, mode=cfg.mode, target=f"{target} product {handle}", action="create draft product",
                       reason="handle already exists; left untouched", result="blocked",
                       error=None if same else f"existing price {existing[handle]} differs from sheet {item['price']}")
            continue
        phase = "stage"
        try:
            files = [i["file"] for i in item.get("images", [])]
            urls: dict[str, str] = {}
            if files:
                payload = raise_on_user_errors(client.execute(products.STAGED_UPLOADS, products.staged_upload_variables(image_dir, files)),
                                               "stagedUploadsCreate")
                phase = "upload"
                for name, tgt in zip(files, payload["stagedTargets"]):
                    upload_staged(tgt, image_dir / name, post)
                    urls[name] = tgt["resourceUrl"]
            phase = "create"
            made = raise_on_user_errors(client.execute(products.CREATE_PRODUCT, products.product_variables(item, urls)),
                                        "productCreate")["product"]
            phase = "variant"
            raise_on_user_errors(client.execute(products.SET_VARIANT, products.variant_variables(
                made["id"], made["variants"]["nodes"][0]["id"], item)), "productVariantsBulkUpdate")
            for p in ("stage", "upload", "create", "variant"):
                breaker.ok(p)
            report["created"].append({"handle": handle, "id": made["id"], "images": len(urls)})
            log.record(tier=2, mode=cfg.mode, target=f"{target} product {handle}", action="create draft product",
                       reason="stage 3 of Shopify provisioning", result="success", before=None,
                       after={"id": made["id"], "status": made["status"], "images": len(urls), "price": item["price"]},
                       **approval)
        except AuthError as exc:  # halt everything and tell the human
            log.record(tier=2, mode=cfg.mode, target=f"{target} product {handle}", action="create draft product",
                       reason="stage 3", result="failed", error=str(exc), **approval)
            report["stopped"] = f"auth problem: {exc}"
            return report
        except (GraphQLError, UploadError, OSError, KeyError, IndexError, ValueError) as exc:
            log.record(tier=2, mode=cfg.mode, target=f"{target} product {handle}", action="create draft product",
                       reason=f"stage 3, failed in step '{phase}'", result="failed", error=str(exc)[:500], **approval)
            report["failed"].append({"handle": handle, "step": phase, "error": str(exc)[:300]})
            if breaker.failed(phase):
                report["stopped"] = f"3 failures in a row in step '{phase}': stopped (circuit breaker)"
                return report
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    for flag in ("--brand", "--products", "--images", "--out"):
        ap.add_argument(flag, required=True)
    ap.add_argument("--approved-by")
    args = ap.parse_args(argv)

    cfg = config.load()
    brand = json.loads(Path(args.brand).read_text(encoding="utf-8"))
    sheet = json.loads(Path(args.products).read_text(encoding="utf-8"))
    try:
        validate(brand, "brand-config.schema.json")
        validate(sheet, "product-sheet.schema.json")
    except InputError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    if brand["store_domain"] != cfg.store_domain:
        print("BLOCKED: SHOPIFY_DOMAIN does not match the brand config store_domain", file=sys.stderr)
        return 2
    if not cfg.api_version:
        print("BLOCKED: SHOPIFY_API_VERSION is not pinned", file=sys.stderr)
        return 2
    client = GraphQLClient(cfg.store_domain, cfg.api_version, lambda: "", dry_run=cfg.dry_run,
                           transport=make_cli_transport(cfg.store_domain, cfg.api_version))
    log = ActionLog(Path(args.out) / "action-log.jsonl", brand["client_id"])
    report = create_products(client, cfg, sheet, Path(args.images), log, args.approved_by)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not report["failed"] and not report["stopped"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
