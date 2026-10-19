"""DTJ's company key vault (Bitwarden) for the store factory: a new person signs in once and gets every key their access allows.

    python tools/team-setup/vault.py status              which keys are in the vault and which are on this laptop (names only)
    python tools/team-setup/vault.py pull                copy the keys you may see from the vault into your Windows user settings
    python tools/team-setup/vault.py pull --replace      the same, also overwriting keys this laptop already has
    python tools/team-setup/vault.py push NAME [NAME..]  copy keys from this laptop into the vault (Harsh, when a key is new or changed)
    python tools/team-setup/vault.py push --all          every store-factory key this laptop has

Why (Harsh, 12 Oct 2026): "if another developer moves in and I leave the company, how will they get those keys?" The keys live in
the company's Bitwarden organization, not on one laptop (docs/ACCESS-AND-KEYS.md). Run this in your OWN PowerShell: Bitwarden asks
for your master password itself, in a hidden prompt. Values never appear on screen, in a file, in a log or on a command line: they
travel through a pipe to Bitwarden's own program, and into the Windows user settings.

Where the keys sit in Bitwarden (organization collections; Bitwarden's own access rules decide who sees which):
  "DTJ Store Factory - Designers"   the shops' Theme Access passwords (DTJ_THEME_ACCESS_<SHOP>)
  "DTJ Store Factory - Developers"  the install service's keys, Cloudflare, the Shopify app secrets
One Login item per key: the item's NAME is the Windows variable's name, its PASSWORD is the value.
Personal keys (N8N_MCP_TOKEN: everyone makes their own in n8n) never go into the vault.
Needs the Bitwarden command-line tool: npm install -g @bitwarden/cli (the setup script installs it).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
from typing import Callable

DESIGNERS = "DTJ Store Factory - Designers"
DEVELOPERS = "DTJ Store Factory - Developers"
PERSONAL = {"N8N_MCP_TOKEN"}
# the store factory's shared keys: exact names, or one of these patterns (see docs/ACCESS-AND-KEYS.md)
KNOWN = {"DTJ_CATCHER_VAULT_KEY", "DTJ_CATCHER_CONTROL_KEY", "DTJ_CATCHER_BOT_KEY", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID",
         "DTJ_BLOCKS_CLIENT_SECRET", "DTJ_SECTIONS_CLIENT_SECRET", "DTJ_SECTIONS2_CLIENT_SECRET",
         # n8n/store-factory/setup_n8n.py --apply builds the bot's n8n credentials from these (n8n API key: n8n > Settings > n8n API)
         "DTJ_TELEGRAM_BOT_TOKEN", "N8N_API_KEY",
         # the brand intake (19 Oct 2026): DTJ's Google Drive login (page_builder/drive_upload.py --authorize) and the GitHub token n8n
         # uses to start the "Brand intake" workflow (/intake in the bot)
         "DTJ_GDRIVE_CLIENT_ID", "DTJ_GDRIVE_CLIENT_SECRET", "DTJ_GDRIVE_REFRESH_TOKEN", "DTJ_GITHUB_ACTIONS_TOKEN"}
PATTERNS = (re.compile(r"^DTJ_THEME_ACCESS_[A-Z0-9_]+$"), re.compile(r"^DTJ_SECRET_[A-Z0-9_]+_(BLOCKS|SECTIONS|SECTIONS2)$"))
NOTE = "Store factory key ({what}). Managed with tools/team-setup/vault.py; see docs/ACCESS-AND-KEYS.md. Never paste it into a chat."

Runner = Callable[[list, "str | None", dict], "subprocess.CompletedProcess[str]"]


class VaultError(Exception):
    pass


def is_known(name: str) -> bool:
    return name not in PERSONAL and (name in KNOWN or any(p.match(name) for p in PATTERNS))


def collection_for(name: str) -> str:
    return DESIGNERS if name.startswith("DTJ_THEME_ACCESS_") else DEVELOPERS


def what(name: str) -> str:
    if name.startswith("DTJ_THEME_ACCESS_"):
        return "Theme Access password for the shop " + name[len("DTJ_THEME_ACCESS_"):].lower().replace("_", "-")
    if name.startswith("DTJ_SECRET_"):
        return "client secret of a client's app copy"
    if name == "DTJ_TELEGRAM_BOT_TOKEN":
        return "the token of @DtjPageDesignerBot, from @BotFather"
    if name.startswith("DTJ_GDRIVE_"):
        return "DTJ's Google Drive login for the brand intake (dtjharshsharma@gmail.com; drive_upload.py --authorize)"
    if name == "DTJ_GITHUB_ACTIONS_TOKEN":
        return "GitHub token that lets n8n start the Brand intake workflow (/intake)"
    if name == "N8N_API_KEY":
        return "n8n API key: lets the setup create the bot's n8n credentials"
    if name.startswith("DTJ_CATCHER_"):
        return "install service key" + (": IRREPLACEABLE, every client reinstalls without it" if name == "DTJ_CATCHER_VAULT_KEY" else "")
    return "developer key"


# ------------------------------------------------------------------------------------------------ this laptop's Windows settings
def user_vars() -> dict[str, str]:
    """Every Windows user setting (name -> value), read from the registry so a value saved a minute ago counts."""
    out: dict[str, str] = {}
    if os.name != "nt":
        return {k: v for k, v in os.environ.items()}
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
        i = 0
        while True:
            try:
                name, value, _ = winreg.EnumValue(k, i)
            except OSError:
                break
            out[name] = str(value)
            i += 1
    return out


def save_user_var(name: str, value: str) -> None:
    if os.name != "nt":
        raise VaultError(f"saving {name} only works on Windows")
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)


# ------------------------------------------------------------------------------------------------ Bitwarden's command-line tool
def _run(cmd: list, stdin: str | None, env: dict) -> "subprocess.CompletedProcess[str]":
    exe = shutil.which(cmd[0]) or cmd[0]  # on Windows npm installs bw.cmd
    return subprocess.run([exe, *cmd[1:]], input=stdin, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=env, timeout=120, check=False)


def _unlock_interactive(env: dict) -> str:
    """Bitwarden asks for the master password itself (hidden); only the session key comes back, and it stays in this process."""
    exe = shutil.which("bw") or "bw"
    done = subprocess.run([exe, "unlock", "--raw"], stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", env=env,
                          check=False)
    if done.returncode != 0 or not done.stdout.strip():
        raise VaultError("Bitwarden did not unlock (wrong master password?). Nothing was changed.")
    return done.stdout.strip()


class Vault:
    def __init__(self, runner: Runner = _run, unlock: Callable[[dict], str] = _unlock_interactive, environ: dict | None = None):
        self.runner, self.unlock = runner, unlock
        self.env = dict(os.environ if environ is None else environ)
        self.secrets: list[str] = []  # values that must never be echoed in an error

    def bw(self, *args: str, stdin: str | None = None) -> str:
        done = self.runner(["bw", *args], stdin, self.env)
        if done.returncode != 0:
            text = (done.stderr or done.stdout or "").strip()
            for s in self.secrets + [self.env.get("BW_SESSION", "")]:
                if s:
                    text = text.replace(s, "[hidden]")
            raise VaultError(f"bw {args[0]} failed: {text[-300:]}")
        return done.stdout

    def open(self) -> None:
        if not (shutil.which("bw") or self.runner is not _run):
            raise VaultError("the Bitwarden command-line tool is missing: run  npm install -g @bitwarden/cli  (or the setup script)")
        status = json.loads(self.bw("status") or "{}").get("status")
        if status == "unauthenticated":
            raise VaultError("not signed in to Bitwarden on this laptop. In PowerShell run:  bw login   (company accounts on the EU "
                             "server first run:  bw config server https://vault.bitwarden.eu ), then run this again.")
        if status != "unlocked":  # "unlocked" only when this window already holds a valid BW_SESSION
            self.env["BW_SESSION"] = self.unlock(self.env)
        self.bw("sync")

    def collections(self) -> dict[str, tuple[str, str]]:
        """Collection name -> (organization id, collection id), for the store factory's collections this person can see."""
        found = {}
        for org in json.loads(self.bw("list", "organizations") or "[]"):
            for col in json.loads(self.bw("list", "org-collections", "--organizationid", org["id"]) or "[]"):
                if col.get("name") in (DESIGNERS, DEVELOPERS):
                    found[col["name"]] = (org["id"], col["id"])
        return found

    def items(self, cols: dict[str, tuple[str, str]]) -> dict[str, dict]:
        """Known key name -> its Bitwarden item, from the store factory's collections only."""
        out: dict[str, dict] = {}
        for org_id, col_id in cols.values():
            for item in json.loads(self.bw("list", "items", "--collectionid", col_id) or "[]"):
                name = str(item.get("name", ""))
                if is_known(name) and item.get("organizationId") == org_id:
                    if name in out and out[name].get("id") != item.get("id"):
                        raise VaultError(f"two vault items are named {name}: keep one (in the Bitwarden app), then run this again")
                    out[name] = item
        return out

    def create(self, name: str, value: str, org_id: str, col_id: str) -> None:
        # each bw call starts Bitwarden's tool afresh (slow on Windows: about a minute per key on 12 Oct 2026), so the item
        # template is asked for once per run
        if not hasattr(self, "_template"):
            self._template = self.bw("get", "template", "item")
        item = json.loads(self._template)
        item.update({"type": 1, "name": name, "notes": NOTE.format(what=what(name)), "organizationId": org_id, "collectionIds": [col_id],
                     "login": {"username": None, "password": value, "uris": [], "totp": None}})
        self.secrets.append(value)
        self.bw("create", "item", stdin=base64.b64encode(json.dumps(item).encode()).decode())

    def update(self, item: dict, value: str) -> None:
        item = {**item, "login": {**(item.get("login") or {}), "password": value}}
        self.secrets.append(value)
        self.bw("edit", "item", item["id"], stdin=base64.b64encode(json.dumps(item).encode()).decode())


# ------------------------------------------------------------------------------------------------ the three jobs
def status(v: Vault, local: dict[str, str], out=print) -> int:
    cols = v.collections()
    for name in (DESIGNERS, DEVELOPERS):
        out(f"[{'ok' if name in cols else '--'}] collection '{name}'" + ("" if name in cols else ": not visible to you (or not made yet)"))
    items = v.items(cols)
    names = sorted(set(items) | {n for n in local if is_known(n)})
    for n in names:
        here = "on this laptop" if local.get(n) else "NOT on this laptop"
        there = "in the vault" if n in items else "NOT in the vault"
        out(f"  {n}: {there}, {here}" + ("   <- run: vault.py push " + n if local.get(n) and n not in items else ""))
    if "DTJ_CATCHER_VAULT_KEY" in local and "DTJ_CATCHER_VAULT_KEY" not in items:
        out("WARNING: DTJ_CATCHER_VAULT_KEY is only on this laptop. If this laptop is lost, every client reinstalls our apps. "
            "Run: python tools/team-setup/vault.py push DTJ_CATCHER_VAULT_KEY")
    return 0


def pull(v: Vault, local: dict[str, str], replace: bool, save=save_user_var, out=print) -> int:
    items = v.items(v.collections())
    if not items:
        out("No store-factory keys are visible to you in the vault. Ask Harsh to give you access to the collection "
            f"'{DESIGNERS}' (designers) or '{DEVELOPERS}' (developers).")
        return 1
    copied, kept = [], []
    for name, item in sorted(items.items()):
        value = str((item.get("login") or {}).get("password") or "").strip()
        if not value:
            out(f"  {name}: the vault item has no password; skipped")
            continue
        if local.get(name) and not replace:
            kept.append(name)
            continue
        save(name, value)
        copied.append(f"{name} ({len(value)} characters)")
    out("Copied into your Windows settings: " + (", ".join(copied) or "none"))
    if kept:
        out("Already on this laptop, left as they are (use --replace to overwrite): " + ", ".join(kept))
    out("Close Claude and PowerShell, then open them again, so they see the new settings.")
    return 0


def push(v: Vault, local: dict[str, str], names: list[str], out=print) -> int:
    bad = [n for n in names if not is_known(n)]
    if bad:
        out("Not a store-factory key (or a personal one that never goes into the vault): " + ", ".join(bad))
        return 1
    missing = [n for n in names if not local.get(n)]
    if missing:
        out("Not on this laptop, nothing to copy: " + ", ".join(missing))
        return 1
    cols = v.collections()
    need = sorted({collection_for(n) for n in names} - set(cols))
    if need:
        out("Make these collections in the Bitwarden organization first (Collections > New), then run this again: " + ", ".join(need))
        return 1
    items = v.items(cols)
    for name in names:
        value = local[name].strip()
        org_id, col_id = cols[collection_for(name)]
        item = items.get(name)
        if item is None:
            v.create(name, value, org_id, col_id)
            out(f"  {name}: added to '{collection_for(name)}' ({len(value)} characters)")
        elif str((item.get("login") or {}).get("password") or "") == value:
            out(f"  {name}: already in the vault, same value")
        else:
            v.update(item, value)
            out(f"  {name}: the vault had an older value; updated (the old one stays in Bitwarden's password history)")
    return 0


def main(argv=None, vault: Vault | None = None, local: dict | None = None, save=save_user_var) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="job", required=True)
    sub.add_parser("status")
    p = sub.add_parser("pull")
    p.add_argument("--replace", action="store_true")
    p = sub.add_parser("push")
    p.add_argument("names", nargs="*")
    p.add_argument("--all", action="store_true")
    args = ap.parse_args(argv)
    local = user_vars() if local is None else local
    v = vault or Vault()
    try:
        v.open()
        if args.job == "status":
            return status(v, local)
        if args.job == "pull":
            return pull(v, local, args.replace, save=save)
        names = sorted(n for n in local if is_known(n)) if args.all else args.names
        if not names:
            print("Name the keys to copy (for example: push DTJ_CATCHER_VAULT_KEY), or use --all.")
            return 1
        return push(v, local, names)
    except VaultError as exc:
        print(f"Stopped: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
