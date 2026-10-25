"""Connect one client store: write the per-client app files for its app copies (all seven since 21 Oct 2026; --parts to choose) and register
them with the catcher.

    python services/install-catcher/tools/add_client.py --shop royal-dosa.myshopify.com --label "Royal Dosa" \
        --worker https://dtj-install-catcher.<subdomain>.workers.dev \
        --blocks-id <client id> --sections-id <client id> --sections2-id <client id> [--name <short name>]

--shop must be the store's ORIGINAL .myshopify.com address: the one in its admin address (admin.shopify.com/store/<handle>).
Shopify keeps sending that address after a store is renamed (seen 9 Oct 2026: a store renamed to test-store-harsh-dtj still
installed as qaxv3r-8g.myshopify.com), and the catcher refuses any other. --name (default: that handle) names the files, the
app addresses and the secret variables, so a renamed store can keep a readable name.

Writes (our current apps and their shopify.app.toml files are never touched):
  services/block-library/shopify.app.<client>.toml            DTJ Blocks - <Label>
  services/block-library-sections/shopify.app.<client>.toml   DTJ Sections - <Label>
  services/block-library-sections-2/shopify.app.<client>.toml DTJ Sections 2 - <Label>
and adds the three copies to APPS in services/install-catcher/wrangler.toml.
Each copy: not embedded, no scopes, opens the catcher on install, sends app/uninstalled to the catcher.
Prints the Windows variables tools/deploy.py reads the three client secrets from (the secrets themselves never pass through here).

A store INSIDE DTJ's own Shopify organization (a dev store, for example elevate-with-harsh) runs DTJ's original apps, not copies:

    python services/install-catcher/tools/add_client.py --org --shop elevate-with-harsh.myshopify.com --label "Elevate with Harsh"

adds its three entries to APPS ("grant": "org": the catcher gets a fresh token from the original app's client credentials grant on
every call, nothing is installed or stored) and writes no app files. tools/deploy.py then needs the original apps' client secrets
in DTJ_BLOCKS_CLIENT_SECRET, DTJ_SECTIONS_CLIENT_SECRET and DTJ_SECTIONS2_CLIENT_SECRET (the names tools/licence.py uses).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SERVICES = HERE.parent
APPS = {  # app part -> (code folder, display name). The first three since 9 Oct 2026; the other four since 21 Oct 2026 (home and collection
    # pages need them; /addshop sets all seven up). A client set up before keeps its three: every tool works on the parts a client has.
    "blocks": ("block-library", "DTJ Blocks"),
    "sections": ("block-library-sections", "DTJ Sections"),
    "sections2": ("block-library-sections-2", "DTJ Sections 2"),
    "heroes": ("block-library-heroes", "DTJ Heroes"),
    "commerce": ("block-library-commerce", "DTJ Commerce"),
    "shop": ("block-library-shop", "DTJ Shop"),
    "collection": ("block-library-collection", "DTJ Collection"),
}
FIRST_THREE = ("blocks", "sections", "sections2")
SHOP_RE = re.compile(r"^[a-z0-9][a-z0-9-]*\.myshopify\.com$")
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
API_VERSION = "2026-10"  # the stable version Shopify gives a new app (seen on the Rupa Divine copies, 9 Oct 2026)
# DTJ's original apps (for stores in DTJ's organization): app part -> (name in APPS "org_app", Windows variable with its client secret)
ORG_APPS = {
    "blocks": ("dtj-blocks", "DTJ_BLOCKS_CLIENT_SECRET"),
    "sections": ("dtj-sections", "DTJ_SECTIONS_CLIENT_SECRET"),
    "sections2": ("dtj-sections2", "DTJ_SECTIONS2_CLIENT_SECRET"),
    "heroes": ("dtj-heroes", "DTJ_HEROES_CLIENT_SECRET"),
    "commerce": ("dtj-commerce", "DTJ_COMMERCE_CLIENT_SECRET"),
    "shop": ("dtj-shop", "DTJ_SHOP_CLIENT_SECRET"),
    "collection": ("dtj-collection", "DTJ_COLLECTION_CLIENT_SECRET"),
}


def org_secret_name(org_app: str) -> str:
    """The catcher's secret holding an original app's client secret (worker.js orgSecretEnv)."""
    return "ORG_SECRET_" + re.sub(r"[^A-Z0-9]", "_", org_app.upper())


def original_client_id(services: Path, part: str) -> str:
    text = (services / APPS[part][0] / "shopify.app.toml").read_text(encoding="utf-8")
    m = re.search(r'^client_id\s*=\s*"([0-9a-f]{32})"', text, re.M)
    if not m:
        raise SystemExit(f"no client id in services/{APPS[part][0]}/shopify.app.toml")
    return m.group(1)


def client_key(shop: str) -> str:
    if not SHOP_RE.fullmatch(shop):
        raise SystemExit(f"{shop!r} is not a .myshopify.com address")
    return shop.split(".")[0]


def secret_env(client: str, part: str) -> str:
    """The Windows user variable holding that copy's client secret (as given to Harsh, 9 Oct 2026); client = the client's name."""
    return f"DTJ_SECRET_{re.sub(r'[^A-Z0-9]', '_', client.upper())}_{part.upper()}"


def app_toml(client: str, part: str, label: str, client_id: str, worker: str) -> str:
    key = f"{client}-{part}"
    name = f"{APPS[part][1]} - {label}"
    return f'''# Per-client copy of {APPS[part][1]} for {label} ({client}.myshopify.com). Written by services/install-catcher/tools/add_client.py.
# Linked with: shopify app config link --path services/{APPS[part][0]} --client-id {client_id} --file-name shopify.app.{client}.toml --force --no-input
# Released with: shopify app deploy --path services/{APPS[part][0]} --config {client} --allow-updates

client_id = "{client_id}"
name = "{name}"
application_url = "{worker}/start/{key}"
embedded = false

[access_scopes]
# no store data at all: the licence is a metafield on our own app installation
scopes = ""

[auth]
redirect_urls = [ "{worker}/callback/{key}" ]

[webhooks]
api_version = "{API_VERSION}"

  [[webhooks.subscriptions]]
  topics = [ "app/uninstalled" ]
  uri = "{worker}/webhooks/{key}"
'''


def set_apps(wrangler_text: str, apps: dict) -> str:
    block = "APPS = '''" + json.dumps(apps, indent=1, sort_keys=True) + "'''"
    new, n = re.subn(r"APPS = '''.*?'''", lambda _m: block, wrangler_text, flags=re.S)
    if n != 1:
        raise SystemExit("could not find APPS = '''...''' in wrangler.toml")
    return new


def current_apps(wrangler_text: str) -> dict:
    m = re.search(r"APPS = '''(.*?)'''", wrangler_text, flags=re.S)
    return json.loads(m.group(1)) if m else {}


def main(argv=None, services: Path = SERVICES, wrangler: Path = HERE / "wrangler.toml") -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shop", required=True)
    ap.add_argument("--label", required=True, help="the client's name as it should appear in the app names")
    ap.add_argument("--org", action="store_true", help="a store in DTJ's own Shopify organization: DTJ's original apps, no copies")
    ap.add_argument("--worker", help="the catcher's https address (app copies only)")
    ap.add_argument("--name", help="short name for files, app addresses and secret variables (default: the store's handle)")
    ap.add_argument("--parts", default=",".join(APPS), help=f"the apps to register (default all seven: {','.join(APPS)}); "
                                                           f"a client set up before 21 Oct 2026 has {','.join(FIRST_THREE)}")
    for part in APPS:
        ap.add_argument(f"--{part}-id", help=f"client id of the {APPS[part][1]} copy (app copies only)")
    args = ap.parse_args(argv)
    client = args.name or client_key(args.shop)
    client_key(args.shop)  # the store address is checked even when a name is given
    if not NAME_RE.fullmatch(client):
        raise SystemExit(f"--name {client!r}: use lowercase letters, digits and single dashes")
    parts = [p.strip() for p in args.parts.split(",") if p.strip()]
    unknown = [p for p in parts if p not in APPS]
    if unknown or not parts:
        raise SystemExit(f"--parts: unknown {unknown}; pick from {', '.join(APPS)}")
    apps = current_apps(wrangler.read_text(encoding="utf-8"))
    if args.org:
        for part in parts:
            org_app = ORG_APPS[part][0]
            apps[f"{client}-{part}"] = {"client_id": original_client_id(services, part), "shop": args.shop,
                                        "label": f"{APPS[part][1]} - {args.label}", "grant": "org", "org_app": org_app}
        wrangler.write_text(set_apps(wrangler.read_text(encoding="utf-8"), apps), encoding="utf-8")
        print(f"registered {', '.join(f'{client}-{p}' for p in parts)} in {wrangler.name} (DTJ's original apps, organization store)")
        print("the original apps' client secrets are read at deploy time from these Windows variables (never typed here):")
        for part in parts:
            print(f"  {ORG_APPS[part][1]}")
        return 0
    missing = [f"--{name}" for name in ("worker", *(f"{part}-id" for part in parts)) if not getattr(args, name.replace("-", "_"))]
    if missing:
        raise SystemExit(f"app copies need {', '.join(missing)} (or --org for a store in DTJ's own organization)")
    worker = args.worker.rstrip("/")
    if not re.fullmatch(r"https://[a-z0-9.-]+", worker):
        raise SystemExit("--worker must be an https address without a path")
    for part in parts:
        folder, display = APPS[part]
        cid = getattr(args, f"{part}_id")
        if not re.fullmatch(r"[0-9a-f]{32}", cid):
            raise SystemExit(f"--{part}-id {cid!r} does not look like a Shopify client id (32 hex characters)")
        path = services / folder / f"shopify.app.{client}.toml"
        path.write_text(app_toml(client, part, args.label, cid, worker), encoding="utf-8")
        apps[f"{client}-{part}"] = {"client_id": cid, "shop": args.shop, "label": f"{display} - {args.label}"}
        print(f"wrote {path.relative_to(services.parent)}")
    wrangler.write_text(set_apps(wrangler.read_text(encoding="utf-8"), apps), encoding="utf-8")
    print(f"registered {', '.join(f'{client}-{p}' for p in parts)} in {wrangler.name}")
    print("client secrets are read at deploy time from these Windows variables (never typed here):")
    for part in parts:
        print(f"  {secret_env(client, part)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
