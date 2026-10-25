"""DTJ Store Builder: the one DTJ app that may add a brand's products, collections and policy pages to a store (Harsh, 21 Oct 2026:
"A new DTJ Store Builder app"). The seven block apps keep no permissions; this one has only what the brand copy needs. It lives in
DTJ's organization like DTJ's original apps, so on a store of that organization (a dev store) the install service gets a fresh key
for it on every call (src/copy.js) and keeps none.

    python services/install-catcher/tools/store_builder.py create --approved-by "<who said yes>"
        make the app in DTJ's organization (Shopify CLI), write services/store-builder-app/shopify.app.toml with its permissions,
        save its client secret in the Windows user variable DTJ_STORE_BUILDER_CLIENT_SECRET (never shown) and its client id in
        wrangler.toml (BUILDER_CLIENT_ID), then release the configuration (shopify app deploy)
    python services/install-catcher/tools/store_builder.py status
        what is done: the app file, the client id, the secret (set or not, never the value)

Then deploy the install service (tools/deploy.py puts the secret up). On each store, a person installs it once: Dev Dashboard > Apps >
DTJ Store Builder > Install app > the store. Creating and releasing the app is Tier 2: it needs a named yes (--approved-by).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "services" / "store-builder"))
from add_shop import CLIENT_ID_RE, ORG_ID, SECRET_RE, WORKER, Failed, default_cli, default_save  # noqa: E402
from deploy import BUILDER_VAR, read_var  # noqa: E402

NAME = "DTJ Store Builder"
FOLDER = ROOT / "services" / "store-builder-app"
# 22 Oct 2026: + online store pages and navigation (About / Contact / FAQ and the menus of a store handed over ready to sell)
SCOPES = "read_products,write_products,read_publications,write_publications,read_legal_policies,write_legal_policies,read_online_store_pages,write_online_store_pages,read_online_store_navigation,write_online_store_navigation"
WRANGLER = HERE.parent / "wrangler.toml"


def app_toml(client_id: str) -> str:
    return (
        "# DTJ Store Builder (services/install-catcher/tools/store_builder.py): the brand copy's app, nothing else.\n"
        "# Only the permissions the brand copy needs (src/copy.js); it has no blocks and no admin pages.\n"
        f'client_id = "{client_id}"\n'
        f'name = "{NAME}"\n'
        f'application_url = "{WORKER}/builder"\n'
        "embedded = false\n\n"
        "[webhooks]\n"
        'api_version = "2026-10"\n\n'
        "[access_scopes]\n"
        f'scopes = "{SCOPES}"\n'
        "optional_scopes = [ ]\n"
        "use_legacy_install_flow = false\n\n"
        "[auth]\n"
        "redirect_urls = [ ]\n"
    )


def set_builder_id(text: str, client_id: str) -> str:
    """wrangler.toml's [vars] gets BUILDER_CLIENT_ID (not secret); an existing one is replaced."""
    line = f'BUILDER_CLIENT_ID = "{client_id}"  # DTJ Store Builder (tools/store_builder.py): the brand copy\'s app'
    if re.search(r"(?m)^BUILDER_CLIENT_ID\s*=", text):
        return re.sub(r"(?m)^BUILDER_CLIENT_ID\s*=.*$", line, text)
    if "[vars]" not in text:
        raise Failed("wrangler.toml has no [vars] section")
    return text.replace("[vars]\n", "[vars]\n" + line + "\n", 1)


def run_cli(cli, cmd: list[str], what: str) -> str:
    done = cli(cmd)
    out = (done.stdout or "") + "\n" + (done.stderr or "")
    if done.returncode != 0:
        raise Failed(f"{what} failed: {SECRET_RE.sub('SHOPIFY_API_SECRET=[hidden]', out).strip()[-500:]}")
    return out


def create(approved_by: str, cli=default_cli, save=default_save, folder: Path = FOLDER, wrangler: Path = WRANGLER, out=print) -> str:
    if not approved_by.strip():
        raise Failed("creating and releasing DTJ Store Builder needs --approved-by (who said yes)")
    toml = folder / "shopify.app.toml"
    m = CLIENT_ID_RE.search(toml.read_text(encoding="utf-8")) if toml.exists() else None
    if m:
        client_id = m.group(1)
        out(f"{NAME} exists already ({toml}): reused")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            run_cli(cli, ["shopify", "app", "init", "--name", NAME, "--organization-id", ORG_ID, "--template", "none", "--path", tmp,
                          "--no-input"], f"creating {NAME}")
            ids = [mm.group(1) for f in Path(tmp).rglob("shopify.app*.toml") for mm in [CLIENT_ID_RE.search(f.read_text(encoding="utf-8"))] if mm]
            if len(ids) != 1:
                raise Failed(f"creating {NAME}: the CLI made no single app file with a client id ({len(ids)} found)")
        client_id = ids[0]
        folder.mkdir(parents=True, exist_ok=True)
        out(f"  created {NAME}")
    toml.write_text(app_toml(client_id), encoding="utf-8")
    shown = run_cli(cli, ["shopify", "app", "env", "show", "--path", str(folder), "--no-input"], f"reading the key of {NAME}")
    secret = SECRET_RE.search(shown)
    if not secret:
        raise Failed(f"the CLI gave no client secret for {NAME}")
    save(BUILDER_VAR, secret.group(1))  # straight into the Windows user variable: never printed, never in a file
    wrangler.write_text(set_builder_id(wrangler.read_text(encoding="utf-8"), client_id), encoding="utf-8")
    run_cli(cli, ["shopify", "app", "deploy", "--path", str(folder), "--allow-updates", "--no-input",
                  "--message", f"{NAME}: the brand copy's permissions ({approved_by})"], f"releasing {NAME}")
    out(f"  released {NAME} with: {SCOPES}")
    return client_id


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create")
    c.add_argument("--approved-by", required=True)
    sub.add_parser("status")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if a.cmd == "status":
        toml = FOLDER / "shopify.app.toml"
        m = CLIENT_ID_RE.search(toml.read_text(encoding="utf-8")) if toml.exists() else None
        print(json.dumps({"app_file": str(toml) if toml.exists() else None, "client_id": m.group(1) if m else None,
                          "secret_saved": bool(read_var(BUILDER_VAR)),
                          "in_wrangler": bool(re.search(r"(?m)^BUILDER_CLIENT_ID\s*=", WRANGLER.read_text(encoding="utf-8")))}, indent=1))
        return 0
    try:
        client_id = create(a.approved_by)
    except Failed as exc:
        print(f"stopped: {exc}", file=sys.stderr)
        return 1
    print(f"done: {NAME} ({client_id}). Next: deploy the install service (tools/deploy.py), then install the app on the store once.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
