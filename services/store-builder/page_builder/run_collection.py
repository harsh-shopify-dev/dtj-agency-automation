"""Build a client's COLLECTION page (one template for every collection) from the client folder. Nothing is written to any store here.

    cd services/store-builder
    python -m page_builder.run_collection --client ../../.work/clients/<client>
        design only: <client>/collection-run/template.json and collection-report.json (header, products, trust when its facts exist)
    python -m page_builder.run_collection --client ../../.work/clients/<client> --sections header,products,faq
        the sections by name (header, products, trust, faq); products is always kept
    python -m page_builder.run_collection --client ... --store X.myshopify.com --theme 123 [--client-registry page_builder/clients/<store>.json]
        read-only on the store: checks the theme is a DRAFT Horizon theme, backs up its templates/collection.json and merges the page into it as
        it is now (our sections replace their old copies; the theme's own product grid is switched OFF, kept in the file; everything else
        stays). <client>/collection-run/approval.json then lets push_page write that one file, and only while it is unchanged.
    python -m page_builder.run_collection --learn-uuid --store X.myshopify.com --theme 123
        read-only: finds a DTJ Product List block placed in that theme (theme editor) and records the app's extension address, which Shopify
        only reveals through a placed block, in page_builder/registry.json (DTJ's own app) or the client registry (a client's copy).

The client folder holds brand.json, home-facts.json (the same facts as the home page) and, optionally, collection-page.json:
    {"store_points": [{"text": "Free shipping above Rs. 499", "source": "shipping policy page, 20 Oct 2026"}, ...]}   (3-6, STORE-WIDE only)
Writing the page is Tier 2: a collection page is NOT covered by Harsh's standing draft rule (product and home pages only), so a person
approves the exact page: python -m page_builder.push_page --out <client>/collection-run --approve <code> --approved-by <name>.
Exit code: 0 = built and clean, 2 = built but a problem needs a person's look, 1 = could not build.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from provision import templates
from provision.theme import ThemeError

from . import assemble_collection as ac
from . import catalog
from . import theme_target as tt
from .assemble import InputError

HERE = Path(__file__).resolve().parent
_REF = re.compile(r"shopify://apps/(?P<handle>[a-z0-9][a-z0-9-]*)/blocks/dtj-product-list/(?P<uuid>[0-9a-f-]{36})")


def learn_uuid(access, theme_id: str, workdir: Path, registry_path: Path = HERE / "registry.json", clients_dir: Path = HERE / "clients") -> dict:
    """Read-only: the DTJ Product List block placed in a theme -> its app handle and extension uuid (and the value the editor wrote for its
    collection setting, the dynamic source to copy). DTJ's own app goes into registry.json; a client's copy into that store's client registry."""
    pulled = access.pull(theme_id, ["templates/*.json", "sections/*.json"], workdir)
    found = None
    for f in sorted(pulled.rglob("*.json")):
        try:
            data = templates.load(f.read_text(encoding="utf-8"))[1]
        except (ValueError, json.JSONDecodeError):
            continue

        def walk(node):
            nonlocal found
            if isinstance(node, dict):
                m = _REF.fullmatch(str(node.get("type", "")))
                if m and not found:
                    found = {"handle": m["handle"], "uuid": m["uuid"], "file": str(f.relative_to(pulled)),
                             "collection_setting": (node.get("settings") or {}).get("collection")}
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)
        walk(data)
    if not found:
        raise ThemeError("no DTJ Product List block in this theme yet: in the theme editor add it once (Add section > Apps > DTJ Product List) "
                         "and save, then run this again")
    if found["handle"] == ac.LIST_APP:
        reg = json.loads(registry_path.read_text(encoding="utf-8"))
        reg["apps"][ac.LIST_APP]["uuid"] = found["uuid"]
        reg["apps"][ac.LIST_APP].pop("pending", None)
        registry_path.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        catalog.registry.cache_clear()
        found["recorded_in"] = str(registry_path)
    else:
        client = clients_dir / f"{tt.normalise_store(access.store).split('.')[0]}.json"
        data = json.loads(client.read_text(encoding="utf-8")) if client.exists() else {"store": access.store, "apps": {}}
        data["apps"][ac.LIST_APP] = {"handle": found["handle"], "uuid": found["uuid"]}
        client.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        found["recorded_in"] = str(client)
    return found


def _access(store: str, access):
    if access is not None:
        return access
    return tt.open_access(store)  # the Theme Access password, else the CLI's own (collaborator) login


def main(argv: list[str] | None = None, *, access=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--client", help="the client folder (brand.json, home-facts.json, optional collection-page.json)")
    ap.add_argument("--sections", help=f"the sections by name: {', '.join(ac.OPTIONS)} (default: {','.join(ac.DEFAULT)})")
    ap.add_argument("--store", help="the store's ORIGINAL .myshopify.com address (read-only check and merge)")
    ap.add_argument("--theme", help="the DRAFT theme's id")
    ap.add_argument("--client-registry", help="a client's own app copies; without it the page uses DTJ's original apps")
    ap.add_argument("--learn-uuid", action="store_true", help="read the DTJ Product List block placed in the theme and record its address")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if bool(args.store) != bool(args.theme):
        ap.error("--store and --theme go together")

    if args.learn_uuid:
        if not args.store:
            ap.error("--learn-uuid needs --store and --theme")
        try:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            found = learn_uuid(_access(args.store, access), args.theme, Path(args.client or ".") / f"learn-{stamp}" if args.client
                               else Path.cwd() / f".learn-{stamp}")
        except ThemeError as exc:
            print(f"could not learn the address: {exc}", file=sys.stderr)
            return 1
        print(f"DTJ Product List found in {found['file']}: app {found['handle']}, extension {found['uuid']}")
        print(f"its collection setting as the editor wrote it: {found['collection_setting']!r}")
        print(f"recorded in {found['recorded_in']}")
        return 0

    if not args.client:
        ap.error("--client is needed")
    client = Path(args.client)
    out = client / "collection-run"
    try:
        brand = json.loads((client / "brand.json").read_text(encoding="utf-8"))
        facts = json.loads((client / "home-facts.json").read_text(encoding="utf-8"))
        page_file = client / "collection-page.json"
        page = json.loads(page_file.read_text(encoding="utf-8")) if page_file.exists() else {}
        chosen = tuple(s.strip().lower() for s in args.sections.split(",") if s.strip()) if args.sections else ac.DEFAULT
        if "products" not in chosen:
            chosen = chosen + ("products",)
        result = ac.build_collection(brand, facts, page, chosen=chosen)
        template = result.template
        if args.client_registry:
            template = catalog.to_client(template, catalog.load_client_registry(args.client_registry))
    except (InputError, ValueError, KeyError, OSError) as e:
        print(f"could not build the collection page: {e}", file=sys.stderr)
        return 1
    rep = result.report

    base_sha, changes, check = None, [], None
    if args.store:
        try:
            acc = _access(args.store, access)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            check = tt.check_target(acc, args.theme, out / f"backup-{stamp}", ac.COLLECTION_FILE)
            if check["base_theme"] != "Horizon":
                raise ThemeError(f"the collection builder makes Horizon pages only; theme {args.theme} is built on {check['base_theme']}")
            current = templates.load(Path(check["backup"]).read_text(encoding="utf-8"))[1] if check["backup"] else {"sections": {}, "order": []}
            base_sha = check["current_product_template_sha256"]
            final, changes = ac.merge(current, template)
        except ThemeError as exc:
            print(f"could not check the theme: {exc}", file=sys.stderr)
            return 1
    else:  # design only: the page on its own, for a look
        final, changes = template, [{"section": s, "change": "added"} for s in template["order"]]

    out.mkdir(parents=True, exist_ok=True)
    (out / "templates").mkdir(exist_ok=True)
    body = tt.template_bytes(final)
    (out / "template.json").write_bytes(body)
    (out / "templates" / "collection.json").write_bytes(body)
    digest = tt.sha256(body)
    ready = not rep["problems"]
    rep["changes"] = changes
    approval = {
        "client": brand.get("brand_name", ""), "store": tt.normalise_store(args.store) if args.store else "", "theme_id": str(args.theme or ""),
        "file": ac.COLLECTION_FILE, "template_sha256": digest, "approve_code": digest[:12], "pushable": bool(args.store) and not rep["pending_address"], "base_sha256": base_sha,
        "sections": rep["chosen"], "changes": changes, "samples": len(rep["samples"]), "demo": False, "ready": ready,  # demo = TEST pictures from the facts: this page shows none (the store's own products)
        "review": "pass" if ready else f"{len(rep['problems'])} build problems",
        "standing_rule": False,  # a collection page is not covered by Harsh's standing draft rule: a person approves this exact file
        "theme": {k: check[k] for k in ("theme_name", "role", "base_theme", "base_version")} if check else None,
    }
    (out / "collection-report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "approval.json").write_text(json.dumps(approval, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"collection page: {', '.join(rep['chosen'])} | category {rep['category']}")
    for o in rep["sections_omitted"]:
        print(f"  not built {o['section']}: {o['reason']}")
    for c in changes:
        print(f"  {c['change']:12} {c['section']}" + (f" ({c['why']})" if c.get("why") else ""))
    for p in rep["problems"]:
        print(f"  PROBLEM {p}")
    print(f"build problems: {len(rep['problems'])}" + (f" | approve code {digest[:12]} (Tier 2: a person approves this page)" if args.store else " | design only"))
    return 0 if ready else 2


if __name__ == "__main__":
    sys.exit(main())
