"""Is this laptop ready to design store pages? Checks everything the page step needs and says, in plain words, what to fix.

    python tools/team-setup/check_setup.py                  every check (reads only; changes nothing on any store)
    python tools/team-setup/check_setup.py --missing-secrets  print only the names of the secret settings still missing (setup uses it)
    python tools/team-setup/check_setup.py --secret-names     print the names of every secret setting this laptop needs

Secrets are checked by NAME and LENGTH only: no value is ever printed. The store checks ask Shopify which themes exist (read-only).
Exit code: 0 = ready, 1 = something to fix.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "services" / "store-builder"))
sys.path.insert(0, str(REPO / "n8n" / "store-factory"))

N8N_VAR = "N8N_MCP_TOKEN"
OK, BAD, WARN = "[ OK ]", "[FIX ]", "[NOTE]"


def user_var(name: str) -> str:
    """A Windows user setting (the registry first, so a value saved a minute ago counts), else this window's environment."""
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                return str(winreg.QueryValueEx(k, name)[0]).strip()
        except OSError:
            pass
    return os.environ.get(name, "").strip()


def _version(cmd: list[str]) -> str | None:
    exe = shutil.which(cmd[0])
    if not exe:
        return None
    try:
        p = subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
        return (p.stdout or p.stderr).strip().splitlines()[0] if (p.stdout or p.stderr).strip() else "installed"
    except (OSError, subprocess.SubprocessError):
        return None


def stores_from_n8n() -> list[dict]:
    from n8n_mcp import STORES_TABLE, PROJECT, call
    rows = call("get_data_table_rows", {"dataTableId": STORES_TABLE, "projectId": PROJECT, "limit": 100})
    rows = rows.get("data") or rows.get("rows") or []
    return [r for r in rows if r.get("myshopify_domain") and r.get("active") is not False]


def stores_from_repo() -> list[dict]:
    out = []
    for f in sorted((REPO / "services/store-builder/page_builder/clients").glob("*.json")):
        try:
            store = json.loads(f.read_text(encoding="utf-8")).get("store")
        except (OSError, ValueError):
            continue
        if store:
            out.append({"store_name": f.stem, "myshopify_domain": store, "draft_theme_id": ""})
    return out


def main(argv=None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from page_builder.theme_target import ThemeAccess, ThemeError, token_env_name

    try:
        stores, source = stores_from_n8n(), "the n8n stores table"
    except Exception:  # noqa: BLE001 - n8n not reachable yet: fall back to the files in the repo
        stores, source = stores_from_repo(), "the store files in the repo"
    if "--missing-secrets" in argv or "--secret-names" in argv:  # names only, never values (the setup script asks for these)
        names = [N8N_VAR] + [token_env_name(s["myshopify_domain"]) for s in stores]
        if "--missing-secrets" in argv:
            names = [n for n in names if not user_var(n)]
        print("\n".join(dict.fromkeys(names)))
        return 0

    problems = 0

    def line(good: bool, text: str, fix: str = "", note: bool = False):
        nonlocal problems
        print(f"{OK if good else (WARN if note else BAD)} {text}")
        if not good and fix:
            print(f"       -> {fix}")
        if not good and not note:
            problems += 1

    print("DTJ page design: is this laptop ready?\n")
    # ---- programs
    py = sys.version_info
    line(py >= (3, 11), f"Python {py.major}.{py.minor}", "Install Python 3.13 (the setup script does it), then open a NEW PowerShell window.")
    for mod, pip_name in (("jsonschema", "jsonschema"), ("liquid", "python-liquid"), ("PIL", "Pillow")):
        try:
            __import__(mod)
            line(True, f"Python package {pip_name}")
        except ImportError:
            line(False, f"Python package {pip_name} is missing", "Run: python -m pip install -r services/store-builder/requirements.txt")
    for cmd, label, fix in ((["git", "--version"], "Git", "Install Git (the setup script does it)."),
                            (["node", "--version"], "Node.js", "Install Node.js LTS (the setup script does it)."),
                            (["shopify", "version"], "Shopify CLI", "Run: npm install -g @shopify/cli@latest")):
        v = _version(cmd)
        line(bool(v), f"{label}: {v or 'not found'}", fix)
    browsers = [p for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")
                if Path(p).exists()]
    line(bool(browsers), "A browser for the page screenshots (Chrome or Edge)", "Install Google Chrome (the setup script does it).")

    # ---- the project and its n8n connection
    branch = _version(["git", "-C", str(REPO), "rev-parse", "--abbrev-ref", "HEAD"])
    line(bool(branch), f"Project folder: {REPO} (branch {branch or '?'})", "Download the project with git clone (see the guide).")
    mcp = REPO / ".mcp.json"
    mcp_ok = mcp.exists() and "n8n.srv2048145.hstgr.cloud" in mcp.read_text(encoding="utf-8") and "${N8N_MCP_TOKEN}" in mcp.read_text(encoding="utf-8")
    line(mcp_ok, "n8n connection file (.mcp.json)", "Run the setup script again: it copies .mcp.example.json to .mcp.json.")
    tok = user_var(N8N_VAR)
    line(bool(tok), f"n8n access token saved ({N8N_VAR}: {len(tok)} characters)" if tok else f"n8n access token ({N8N_VAR}) is not saved",
         "Run the setup script: it asks for the token (create it in n8n: Settings > MCP access).")
    if tok:
        try:
            from n8n_mcp import call
            call("search_workflows", {"query": "Store Factory"})
            line(True, "n8n answers with this token")
        except Exception as exc:  # noqa: BLE001
            line(False, f"n8n did not accept the token ({str(exc)[:120]})", "Create a new token in n8n and save it again with the setup script.")

    # ---- every shop: its design password and its draft theme
    print(f"\nShops (from {source}):")
    if not stores:
        line(False, "No shops found", "Ask Harsh: the stores table in n8n (dtj_stores) is empty or n8n is not reachable.")
    for s in stores:
        name, domain = s.get("store_name") or s["myshopify_domain"], s["myshopify_domain"]
        var = token_env_name(domain)
        pw = user_var(var)
        if not pw:
            line(False, f"{name}: design password not saved ({var})", "Run the setup script: it asks for it (Shopify admin > Apps > Theme Access).")
            continue
        theme = str(s.get("draft_theme_id") or "")
        if not theme:
            line(True, f"{name}: design password saved ({len(pw)} characters); draft theme not checked (no id here)")
            continue
        try:
            found = ThemeAccess(domain, pw).themes(theme)
            role = (found[0].get("role") if found else "missing") or "?"
            line(role == "unpublished", f"{name}: draft theme {theme} is {role}",
                 "Ask Harsh: the saved draft theme is missing or is not a draft (pages are only ever written to a draft).")
        except ThemeError as exc:
            line(False, f"{name}: Shopify refused the design password ({str(exc)[:100]})",
                 "Ask for a new Theme Access password for this shop and save it again with the setup script.")

    print("\nReady to design pages." if not problems else f"\n{problems} thing(s) to fix: follow the arrows above, then run this check again.")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
