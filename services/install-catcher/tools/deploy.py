"""Deploy the install catcher to Cloudflare (Tier 2: Harsh approves each deploy).

    python services/install-catcher/tools/deploy.py --dry-run      # say what would happen, touch nothing
    python services/install-catcher/tools/deploy.py                # create storage if needed, set secrets, deploy, check /health

Reads (Windows user variables or this shell's environment; never printed, never on a command line):
  CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID       the Cloudflare login for wrangler
  DTJ_SECRET_<CLIENT>_BLOCKS / _SECTIONS / _SECTIONS2   each client app copy's client secret (see add_client.py)
  DTJ_BLOCKS_CLIENT_SECRET / DTJ_SECTIONS_CLIENT_SECRET / DTJ_SECTIONS2_CLIENT_SECRET   DTJ's original apps' client secrets, only
      when APPS has a store in DTJ's own organization ("grant": "org", add_client.py --org); each is put once as ORG_SECRET_<APP>
Creates once and keeps a local backup as Windows user variables (Cloudflare never shows a secret again; losing VAULT_KEY would
mean every client reinstalling): DTJ_CATCHER_VAULT_KEY, DTJ_CATCHER_CONTROL_KEY (signs licence_call.py requests) and
DTJ_CATCHER_BOT_KEY (the Telegram bot's key: Harsh copies it into n8n's credential "DTJ Catcher Bot Key", never into chat).
Secrets reach wrangler only through its standard input (`wrangler secret put NAME` reads the value from stdin).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Callable, Mapping, Sequence

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from add_client import APPS as PARTS, ORG_APPS, current_apps, org_secret_name, secret_env  # noqa: E402

Runner = Callable[[Sequence[str], Mapping[str, str], str | None], "subprocess.CompletedProcess[str]"]


def read_var(name: str, environ: Mapping[str, str] | None = None) -> str | None:
    value = (environ if environ is not None else os.environ).get(name)
    if not value and environ is None and os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                value = winreg.QueryValueEx(key, name)[0]
        except OSError:
            value = None
    return value or None


def save_var(name: str, value: str) -> None:
    """Keep a local backup of a generated catcher key as a Windows user variable (never printed)."""
    if os.name != "nt":
        raise SystemExit(f"save {name} somewhere safe by hand: this backup step only runs on Windows")
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)


def _run(cmd: Sequence[str], env: Mapping[str, str], stdin: str | None) -> "subprocess.CompletedProcess[str]":
    exe = shutil.which(cmd[0]) or cmd[0]
    return subprocess.run([exe, *cmd[1:]], input=stdin, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=dict(env), cwd=str(HERE), timeout=600, check=False)


class Deploy:
    def __init__(self, runner: Runner = _run, environ: Mapping[str, str] | None = None, save: Callable[[str, str], None] = save_var,
                 wrangler_toml: Path = HERE / "wrangler.toml", dry_run: bool = False):
        self.runner, self.environ, self.save, self.toml, self.dry = runner, environ, save, wrangler_toml, dry_run
        self.log: list[str] = []
        token, account = read_var("CLOUDFLARE_API_TOKEN", environ), read_var("CLOUDFLARE_ACCOUNT_ID", environ)
        missing = [n for n, v in (("CLOUDFLARE_API_TOKEN", token), ("CLOUDFLARE_ACCOUNT_ID", account)) if not v]
        if missing:
            raise SystemExit(f"missing Windows variable(s): {', '.join(missing)} (see services/install-catcher/README.md)")
        self._secrets = [token]
        self.env = {**os.environ, "CLOUDFLARE_API_TOKEN": token, "CLOUDFLARE_ACCOUNT_ID": account, "WRANGLER_SEND_METRICS": "false"}

    def wrangler(self, *args: str, stdin: str | None = None, what: str = "", allow: str = "") -> str:
        cmd = ["npx", "--yes", "wrangler@4", *args]
        self.log.append(" ".join(cmd) + (f"   (value from {what} via stdin)" if what else ""))
        if self.dry:
            return ""
        done = self.runner(cmd, self.env, stdin)
        out = (done.stdout or "") + "\n" + (done.stderr or "")
        for s in self._secrets:
            out = out.replace(s, "[redacted]")
        if done.returncode != 0:
            if allow and allow in out:
                return "\x00" + out  # an expected answer (for example: the Worker does not exist yet)
            raise SystemExit(f"wrangler {' '.join(args[:2])} failed: {out.strip()[-600:]}")
        return out

    def ensure_kv(self) -> None:
        text = self.toml.read_text(encoding="utf-8")
        if "REPLACE_WITH_KV_ID" not in text:
            return
        out = self.wrangler("kv", "namespace", "create", "VAULT")
        if self.dry:
            return
        m = re.search(r'id\s*=\s*"([0-9a-f]{32})"', out) or re.search(r'"id"\s*:\s*"([0-9a-f]{32})"', out)
        if not m:
            raise SystemExit("could not read the new storage id from wrangler's answer")
        self.toml.write_text(text.replace("REPLACE_WITH_KV_ID", m.group(1)), encoding="utf-8")

    def existing_secrets(self) -> set[str]:
        """The secret names already set. A brand-new Worker does not exist yet: deploy it first (with no secrets every route refuses),
        because `wrangler secret put` needs an existing Worker (wrangler: 'If this is a new Worker, run wrangler deploy first')."""
        out = self.wrangler("secret", "list", "--format", "json", allow="not found")
        if self.dry:
            return set()
        if out.startswith("\x00"):
            self.url = self._deploy()
            return set()
        start = out.find("[")
        return {s["name"] for s in json.loads(out[start:out.rindex("]") + 1])} if start >= 0 else set()

    def put_secret(self, name: str, value: str, what: str) -> None:
        self._secrets.append(value)
        self.wrangler("secret", "put", name, stdin=value, what=what)

    def catcher_key(self, name: str, backup_var: str, make: Callable[[], str], existing: set[str]) -> None:
        backup = read_var(backup_var, self.environ)
        if name in existing and backup:
            return  # set before, and we hold the backup
        if name in existing and not backup:
            raise SystemExit(f"{name} is set in Cloudflare but its local backup {backup_var} is missing: stop and ask Harsh")
        value = backup or make()
        if not backup and not self.dry:
            self.save(backup_var, value)
        self.put_secret(name, value, backup_var)

    def run(self) -> str | None:
        apps = current_apps(self.toml.read_text(encoding="utf-8"))
        wanted = []
        org_vars = {org_app: var for org_app, var in ORG_APPS.values()}
        for app, cfg in apps.items():
            part = app.rsplit("-", 1)[1]
            if part not in PARTS:
                raise SystemExit(f"unknown app part in {app}")
            if cfg.get("grant") == "org":  # DTJ's original app on a store in DTJ's organization: one shared secret per app
                var = org_vars.get(cfg.get("org_app", ""))
                if not var:
                    raise SystemExit(f"{app}: unknown org_app {cfg.get('org_app')!r}")
                value = read_var(var, self.environ)
                if not value:
                    raise SystemExit(f"missing Windows variable {var} (the client secret of DTJ's original app, needed for {cfg['label']}); "
                                     "nothing was deployed")
                if all(name != org_secret_name(cfg["org_app"]) for name, _v, _w in wanted):
                    wanted.append((org_secret_name(cfg["org_app"]), value, var))
                continue
            var = secret_env(app.rsplit("-", 1)[0], part)  # named after the client, not the store address
            value = read_var(var, self.environ)
            if not value:
                raise SystemExit(f"missing Windows variable {var} (the client secret of {cfg['label']}); nothing was deployed")
            wanted.append(("SECRET_" + re.sub(r"[^A-Z0-9]", "_", app.upper()), value, var))
        self.ensure_kv()
        existing = self.existing_secrets()
        self.catcher_key("VAULT_KEY", "DTJ_CATCHER_VAULT_KEY", lambda: base64.b64encode(secrets.token_bytes(32)).decode(), existing)
        self.catcher_key("CONTROL_KEY", "DTJ_CATCHER_CONTROL_KEY", lambda: secrets.token_hex(32), existing)
        # the Telegram bot's own key (n8n sends it in a header from an encrypted credential; revocable without touching CONTROL_KEY)
        self.catcher_key("BOT_KEY", "DTJ_CATCHER_BOT_KEY", lambda: secrets.token_hex(32), existing)
        for name, value, var in wanted:
            self.put_secret(name, value, var)
        url = self._deploy()  # the code and the secrets together
        return url or getattr(self, "url", None)

    def _deploy(self) -> str | None:
        out = self.wrangler("deploy")
        if self.dry:
            return None
        m = re.search(r"https://[a-z0-9.-]+\.workers\.dev", out)
        return m.group(0) if m else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    d = Deploy(dry_run=args.dry_run)
    url = d.run()
    for line in d.log:
        print(("would run: " if args.dry_run else "ran: ") + line)
    if url:
        req = urllib.request.Request(f"{url}/health", headers={"User-Agent": "dtj-deploy/1"})  # Cloudflare blocks Python's default agent
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"deployed: {url}  /health -> {r.status} {r.read().decode()[:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
