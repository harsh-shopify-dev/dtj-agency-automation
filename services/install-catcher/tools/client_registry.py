"""Write a client's block addresses for the page builder (services/store-builder/page_builder/clients/<client>.json), with no one
adding blocks in a theme editor.

    python services/install-catcher/tools/client_registry.py --client test-store-harsh-dtj

A DTJ block in a theme is `shopify://apps/<app handle>/blocks/<block>/<extension uuid>`, and every per-client app copy has its own
handle and uuid. The uuid is in the Shopify CLI's release record `services/<app>/.shopify/deploy-bundle/manifest.json`
(modules[type=theme_app_extension].uuid), which the NEXT release overwrites: run this right after releasing the client's copies.
The handle is what the store reports for the installed app (catcher /licence status, app_handle): before the client installs, the
handle stays "pending" and the page builder refuses the registry. Run again after the install to fill it in.
The manifest's app name must match the copy's label in wrangler.toml, so a release record from another client is never used.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parents[1]
SERVICES = HERE.parent
sys.path.insert(0, str(HERE / "tools"))
from add_client import APPS, FIRST_THREE, current_apps  # noqa: E402

PAGE_APP = {"blocks": "dtj-blocks", "sections": "dtj-sections", "sections2": "dtj-sections-2", "heroes": "dtj-heroes",
            "commerce": "dtj-commerce", "shop": "dtj-shop", "collection": "dtj-collection"}  # names in page_builder/registry.json
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def extension_uuid(folder: Path, label: str) -> str:
    path = folder / ".shopify" / "deploy-bundle" / "manifest.json"
    if not path.is_file():
        raise SystemExit(f"{path} not found: release the app first (shopify app deploy --config <client>)")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("name") != label:
        raise SystemExit(f"{path} is the release record of {manifest.get('name')!r}, not {label!r}: release {label} again, then rerun")
    mods = [m for m in manifest.get("modules", []) if m.get("type") == "theme_app_extension"]
    if len(mods) != 1 or not UUID.match(mods[0].get("uuid", "")):
        raise SystemExit(f"{path}: expected one theme extension with a uuid")
    return mods[0]["uuid"]


def build(client: str, status: Callable[[str], dict], services: Path = SERVICES, wrangler: Path = HERE / "wrangler.toml",
          clients_dir: Path | None = None) -> dict:
    apps = current_apps(wrangler.read_text(encoding="utf-8"))
    out_dir = clients_dir or services / "store-builder" / "page_builder" / "clients"
    path = out_dir / f"{client}.json"
    old = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    entry, shop = {}, None
    for part, (folder, _display) in APPS.items():
        key = f"{client}-{part}"
        if key not in apps:
            if part in FIRST_THREE:  # every client has these; the other four only from 21 Oct 2026 (/addshop)
                raise SystemExit(f"{key} is not registered with the catcher (add_client.py first)")
            continue
        cfg = apps[key]
        shop = cfg["shop"]
        uuid = extension_uuid(services / folder, cfg["label"])
        handle = (status(key) or {}).get("app_handle") or old.get("apps", {}).get(PAGE_APP[part], {}).get("handle") or "pending"
        entry[PAGE_APP[part]] = {"handle": handle, "uuid": uuid}
    data = {"_comment": "Written by services/install-catcher/tools/client_registry.py. handle: the store's own name for the installed app "
                        "(catcher status); uuid: the theme extension id from the CLI release record.",
            "store": shop, "apps": entry}
    out_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    return data


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--client", required=True, help="the client name used with add_client.py (e.g. test-store-harsh-dtj)")
    args = ap.parse_args(argv)
    from licence_call import call

    def status(key: str) -> dict:
        code, data = call(key, "status")
        return data if code == 200 else {}

    data = build(args.client, status)
    pending = [a for a, e in data["apps"].items() if e["handle"] == "pending"]
    print(json.dumps(data, indent=1))
    if pending:
        print(f"handles pending for {pending}: the client has not installed them yet; run again after the install", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
