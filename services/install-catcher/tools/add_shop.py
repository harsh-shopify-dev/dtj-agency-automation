"""Add a client shop end to end with one command (Harsh, 21 Oct 2026: "cant we make the installation process a one step process from
telegram ... i will connect my partner account where it will create and install the copies to the clients store where i will provide the
shopify domain of the store").

    python services/install-catcher/tools/add_shop.py --shop clientstore.myshopify.com --label "Brand Name" [--name short] [--chat <telegram id>]
        [--theme <draft theme id>] [--approved-by "<name>"]
    python services/install-catcher/tools/add_shop.py --shop clientstore.myshopify.com --link blocks=<install link> --link heroes=<...>
    python services/install-catcher/tools/add_shop.py --shop clientstore.myshopify.com --status

Steps, kept in .work/add-shop/<client>.json so a second run continues where the first stopped:
   1 create   the seven app copies in DTJ's Shopify organization: shopify app init --name "<App> - <Label>" --organization-id <org> --no-input
   2 files    each copy's settings in its app folder and the install service's list (add_client.py)
   3 link     each copy linked to its folder (shopify app config link), then our settings written again so they win
   4 secrets  each copy's client secret from `shopify app env show` straight into the Windows user variable DTJ_SECRET_<CLIENT>_<APP>
              (never printed, never in a file)
   5 release  each copy released (shopify app deploy --config <client>): an app release, so the request itself is the person's yes
   6 catcher  the install service deployed with the new copies' secrets (deploy.py)
   7 links    Shopify makes a custom-distribution install link ONLY on each app's Distribution page (no API, no CLI): a person, or Claude in
              the laptop's browser with that person's yes, records each with --link <part>=<url>
   8 send     one Telegram message with seven Install buttons (the store OWNER opens them: a collaborator was refused)
   9 wait     the installs: the install service reports each one, the bar says "4 of 7"; then the page builder's client list gets the
              copies' block addresses (client_registry.py)
  10 shop     the shop goes into n8n's shop list (dtj_stores) so page requests for it work (active once its draft theme is known)
Exit codes: 0 done; 3 waiting (for the install links or the installs: run it again later); 1 failed (the message says what and why).
The Theme Access password for page writes stays the store's own step (the Theme Access app, Shopify emails the password).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE / "tools"))
sys.path.insert(0, str(ROOT / "services" / "store-builder"))
sys.path.insert(0, str(ROOT / "n8n" / "store-factory"))
import add_client  # noqa: E402
from add_client import APPS, SHOP_RE, client_key, secret_env  # noqa: E402

ORG_ID = "141167028"  # DTJ's Shopify organization (Dev Dashboard address; not a secret)
WORKER = "https://dtj-install-catcher.ultimateecomwithharsh.workers.dev"
STATE_DIR = ROOT / ".work" / "add-shop"
STAGES = {
    "create": ("Creating the app copies", 0, 25),
    "link": ("Linking the copies", 25, 33),
    "secrets": ("Saving their keys (never shown)", 33, 38),
    "release": ("Releasing the copies", 38, 68),
    "catcher": ("Updating the install service", 68, 74),
    "links": ("Waiting for the install links", 74, 78),
    "wait": ("Waiting for the installs", 78, 97),
    "shop": ("Adding the shop to the list", 97, 100),
}
UNITS = {"create": "app", "link": "app", "secrets": "app", "release": "app", "wait": "install"}
LINK_RE = re.compile(r"^https://[a-z0-9.-]+/[^\s]*client_id=(?P<id>[0-9a-f]{32})[^\s]*$")
SECRET_RE = re.compile(r"SHOPIFY_API_SECRET\s*=\s*(\S+)")
CLIENT_ID_RE = re.compile(r'^client_id\s*=\s*"([0-9a-f]{32})"', re.M)
WAITING = 3


class Failed(Exception):
    pass


def default_cli(cmd: list[str]) -> subprocess.CompletedProcess:
    """The Shopify CLI with a time limit that stops the whole process tree (page_builder.theme_target._run) and no git prompt."""
    from page_builder.theme_target import _run  # noqa: PLC0415
    return _run(cmd, dict(__import__("os").environ))


def default_save(name: str, value: str) -> None:
    from deploy import save_var  # noqa: PLC0415  (a Windows user variable; the value never reaches a command line)
    save_var(name, value)


def default_status(app_key: str) -> dict | None:
    from licence_call import call  # noqa: PLC0415
    try:
        code, data = call(app_key, "status")
    except Exception:  # noqa: BLE001 - not installed yet answers an error
        return None
    return data if code == 200 and isinstance(data, dict) and data.get("app_handle") else None


class AddShop:
    def __init__(self, shop: str, label: str, name: str | None = None, *, chat: str = "", theme: str = "", approved_by: str = "",
                 cli: Callable[[list[str]], subprocess.CompletedProcess] = default_cli, save: Callable[[str, str], None] = default_save,
                 status: Callable[[str], dict | None] = default_status, progress=None, telegram=None, n8n=None,
                 services: Path = ROOT / "services", wrangler: Path = HERE / "wrangler.toml", state_dir: Path = STATE_DIR,
                 deploy_catcher: Callable[[], int] | None = None, registry: Callable[[str], dict] | None = None, out=print,
                 sleep=time.sleep, clock=time.monotonic):
        if not SHOP_RE.fullmatch(shop):
            raise Failed(f"{shop!r} is not a .myshopify.com address: use the store's ORIGINAL address from its admin")
        self.shop, self.label = shop, label.strip()
        self.client = name or client_key(shop)
        if not add_client.NAME_RE.fullmatch(self.client):
            raise Failed(f"--name {self.client!r}: lowercase letters, digits and single dashes")
        self.chat, self.theme, self.approved_by = str(chat or ""), str(theme or ""), approved_by
        self.cli, self.save, self.status, self.out, self.sleep, self.clock = cli, save, status, out, sleep, clock
        self.services, self.wrangler = services, wrangler
        self.path = state_dir / f"{self.client}.json"
        self.s = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.s.setdefault("shop", shop)
        if self.s["shop"] != shop:
            raise Failed(f"{self.path} belongs to {self.s['shop']}, not {shop}")
        self.s.setdefault("label", self.label)
        for key in ("ids", "linked", "secrets", "released", "links", "installed"):
            self.s.setdefault(key, {})
        self.progress, self.telegram, self.n8n = progress, telegram, n8n
        self.deploy_catcher, self.registry = deploy_catcher, registry

    # ---- bookkeeping
    def save_state(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.s, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    def bar(self, stage: str, done: int = 0, total: int = 0) -> None:
        if self.progress:
            self.progress.step(stage, done, total)

    def run_cli(self, cmd: list[str], what: str) -> str:
        try:
            done = self.cli(cmd)
        except Exception as exc:  # noqa: BLE001 - a frozen CLI is stopped by the runner and raises: the step stops cleanly
            raise Failed(f"{what}: {exc}") from exc
        out = (done.stdout or "") + "\n" + (done.stderr or "")
        if done.returncode != 0:
            shown = SECRET_RE.sub("SHOPIFY_API_SECRET=[hidden]", out).strip()[-500:]
            raise Failed(f"{what} failed: {shown}")
        return out

    def display(self, part: str) -> str:
        return f"{APPS[part][1]} - {self.label}"

    def folder(self, part: str) -> Path:
        return self.services / APPS[part][0]

    # ---- the steps
    def create(self) -> None:
        todo = [p for p in APPS if p not in self.s["ids"]]
        for i, part in enumerate(APPS, 1):
            if part not in todo:
                continue
            made = self.folder(part) / f"shopify.app.{self.client}.toml"  # made earlier (another laptop, or lost state): never twice
            m = CLIENT_ID_RE.search(made.read_text(encoding="utf-8")) if made.exists() else None
            if m:
                self.s["ids"][part] = m.group(1)
                self.save_state()
                self.out(f"  {self.display(part)} exists already ({made.name}): reused")
                continue
            self.bar("create", i - 1, len(APPS))
            with tempfile.TemporaryDirectory() as tmp:
                self.run_cli(["shopify", "app", "init", "--name", self.display(part), "--organization-id", ORG_ID, "--template", "none",
                              "--path", tmp, "--no-input"], f"creating {self.display(part)}")
                tomls = list(Path(tmp).rglob("shopify.app*.toml"))
                ids = [m.group(1) for f in tomls for m in [CLIENT_ID_RE.search(f.read_text(encoding="utf-8"))] if m]
                if len(ids) != 1:
                    raise Failed(f"creating {self.display(part)}: the CLI made no single app file with a client id ({len(ids)} found)")
            self.s["ids"][part] = ids[0]
            self.save_state()
            self.out(f"  created {self.display(part)}")
        self.bar("create", len(APPS), len(APPS))

    def write_files(self) -> None:
        args = ["--shop", self.shop, "--label", self.label, "--name", self.client, "--worker", WORKER, "--parts", ",".join(APPS)]
        for part in APPS:
            args += [f"--{part}-id", self.s["ids"][part]]
        add_client.main(args, services=self.services, wrangler=self.wrangler)

    def link(self) -> None:
        for i, part in enumerate(APPS, 1):
            if self.s["linked"].get(part):
                continue
            self.bar("link", i - 1, len(APPS))
            self.run_cli(["shopify", "app", "config", "link", "--path", str(self.folder(part)), "--client-id", self.s["ids"][part],
                          "--file-name", f"shopify.app.{self.client}.toml", "--force", "--no-input"], f"linking {self.display(part)}")
            self.s["linked"][part] = True
            self.save_state()
        self.write_files()  # the link pulled Shopify's defaults into the files: our settings win again

    def secrets(self) -> None:
        for i, part in enumerate(APPS, 1):
            if self.s["secrets"].get(part):
                continue
            self.bar("secrets", i - 1, len(APPS))
            out = self.run_cli(["shopify", "app", "env", "show", "--path", str(self.folder(part)), "--config", self.client, "--no-input"],
                               f"reading the key of {self.display(part)}")
            m = SECRET_RE.search(out)
            if not m:
                raise Failed(f"the CLI gave no client secret for {self.display(part)}")
            self.save(secret_env(self.client, part), m.group(1))  # straight into the Windows user variable
            self.s["secrets"][part] = secret_env(self.client, part)  # the variable's NAME only
            self.save_state()

    def release(self) -> None:
        for i, part in enumerate(APPS, 1):
            if self.s["released"].get(part):
                continue
            self.bar("release", i - 1, len(APPS))
            self.run_cli(["shopify", "app", "deploy", "--path", str(self.folder(part)), "--config", self.client, "--allow-updates",
                          "--message", f"{self.label} copy (add_shop, {self.approved_by or 'person'})", "--no-input"],
                         f"releasing {self.display(part)}")
            self.s["released"][part] = True
            self.save_state()
            self.out(f"  released {self.display(part)}")

    def catcher(self) -> None:
        if self.s.get("catcher"):
            return
        self.bar("catcher")
        code = (self.deploy_catcher or (lambda: subprocess.run([sys.executable, str(HERE / "tools" / "deploy.py")], check=False).returncode))()
        if code != 0:
            raise Failed("the install service could not be deployed (deploy.py said why above)")
        self.s["catcher"] = True
        self.save_state()

    def add_links(self, pairs: list[str]) -> None:
        for pair in pairs:
            part, _, url = pair.partition("=")
            part, url = part.strip(), url.strip()
            if part not in APPS:
                raise Failed(f"--link {pair!r}: the part must be one of {', '.join(APPS)}")
            m = LINK_RE.match(url)
            if not m or m.group("id") != self.s["ids"].get(part):
                raise Failed(f"--link {part}: not an install link of {self.display(part)} (its client id must be in it)")
            self.s["links"][part] = url
        self.save_state()

    def send_links(self) -> None:
        if self.s.get("links_sent"):
            return
        rows = [[{"text": f"Install {APPS[p][1]}", "url": self.s["links"][p]}] for p in APPS]
        text = (f"{self.label} ({self.shop}): the store OWNER opens each Install button while logged in to that store's admin and presses "
                f"Install on Shopify's page (a collaborator login was refused before: if that is not you, forward this message to the "
                f"owner). I report each one here.")
        if self.telegram and self.chat:
            self.telegram("sendMessage", {"chat_id": self.chat, "text": text, "reply_markup": {"inline_keyboard": rows}})
        else:
            self.out(text)
            for p in APPS:
                self.out(f"  {APPS[p][1]}: {self.s['links'][p]}")
        self.s["links_sent"] = True
        self.save_state()

    def wait(self, minutes: float) -> bool:
        end = self.clock() + minutes * 60
        while True:
            for part in APPS:
                if part not in self.s["installed"]:
                    got = self.status(f"{self.client}-{part}")
                    if got:
                        self.s["installed"][part] = got.get("app_handle", "")
                        self.save_state()
                        self.out(f"  installed {self.display(part)}")
            self.bar("wait", len(self.s["installed"]), len(APPS))
            if len(self.s["installed"]) == len(APPS) or self.clock() >= end:
                break
            self.sleep(20)
        if len(self.s["installed"]) < len(APPS):
            return False
        if self.registry:
            self.registry(self.client)
        return True

    def add_to_shop_list(self) -> None:
        if self.s.get("listed") or not self.n8n:
            return
        self.bar("shop")
        self.n8n({"store_name": self.label, "myshopify_domain": self.shop, "other_domains": "", "draft_theme_id": self.theme,
                  "client_registry": f"page_builder/clients/{self.client}.json", "brand_name": self.label, "brand_website": "",
                  "reference_brands": "", "store_notes": "added by /addshop (add_shop.py)" + ("" if self.theme else ": set draft_theme_id, then active"),
                  "active": bool(self.theme)})
        self.s["listed"] = True
        self.save_state()

    def answer(self, status: str, note: str) -> None:
        """The body for n8n's "Store Factory: Add Shop" (reply.py --body .work/add-shop/<client>.answer.json), written after every run."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = {"shop_status": status, "installed": len(self.s["installed"]), "note": note[:700], "shop": self.shop, "label": self.label}
        (self.path.parent / f"{self.client}.answer.json").write_text(json.dumps(body, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    def run(self, wait_minutes: float = 30) -> int:
        code = self._run(wait_minutes)
        self.answer(*{0: ("done", "all 7 apps installed; next: the draft theme id and the Theme Access password for page writes"),
                      WAITING: ("waiting for installs", self.waiting_note or "some installs are still missing"),
                      1: ("could not add", self.stop_note)}[code])
        return code

    def _run(self, wait_minutes: float) -> int:
        self.waiting_note, self.stop_note = "", ""
        try:
            self.create()
            self.write_files()
            self.link()
            self.secrets()
            self.release()
            self.catcher()
            missing = [p for p in APPS if p not in self.s["links"]]
            if missing:
                self.bar("links", len(APPS) - len(missing), len(APPS))
                self.out("waiting for the install links (Shopify makes them only on each app's Distribution page: Custom distribution, "
                         f"{self.shop}, Generate link): " + ", ".join(self.display(p) for p in missing))
                self.out(f"record them with: add_shop.py --shop {self.shop} --link <part>=<url> ... (parts: {', '.join(missing)})")
                self.waiting_note = f"waiting for {len(missing)} install link(s) from the Dev Dashboard"
                return WAITING
            self.send_links()
            if not self.wait(wait_minutes):
                self.out(f"{len(self.s['installed'])} of {len(APPS)} installed so far: run add_shop.py --shop {self.shop} again to keep waiting")
                self.waiting_note = f"{len(self.s['installed'])} of {len(APPS)} installed; the Install buttons are in Telegram"
                return WAITING
            self.add_to_shop_list()
            if self.progress:
                self.progress.finish(True, f"{self.label}: all {len(APPS)} apps connected. Page requests for this shop work once its draft "
                                           "theme and Theme Access password are set.")
            self.out(f"done: {self.shop} has all {len(APPS)} apps connected")
            return 0
        except Failed as exc:
            if self.progress:
                self.progress.finish(False, str(exc)[:300])
            self.out(f"stopped: {exc}")
            self.stop_note = str(exc)
            return 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shop", required=True, help="the store's ORIGINAL .myshopify.com address")
    ap.add_argument("--label", help="the client's name as it should appear in the app names (needed the first time)")
    ap.add_argument("--name", help="short name for files and variables (default: the store's handle)")
    ap.add_argument("--chat", default="", help="the Telegram chat for the progress bar and the Install buttons")
    ap.add_argument("--theme", default="", help="the store's DRAFT theme id, when known (the shop list needs it for page requests)")
    ap.add_argument("--approved-by", default="", help="who asked for it (recorded in the release message)")
    ap.add_argument("--link", action="append", default=[], help="<part>=<install link> from an app's Distribution page (repeatable)")
    ap.add_argument("--wait-minutes", type=float, default=30)
    ap.add_argument("--status", action="store_true", help="show where this shop's setup is and stop")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    client = a.name or client_key(a.shop)
    state = STATE_DIR / f"{client}.json"
    if a.status:
        s = json.loads(state.read_text(encoding="utf-8")) if state.exists() else {}
        for key in ("ids", "linked", "secrets", "released", "links", "installed"):
            print(f"{key:10} {len(s.get(key, {}))} of {len(APPS)}")
        print(f"catcher    {'deployed' if s.get('catcher') else 'not yet'} | shop list {'added' if s.get('listed') else 'not yet'}")
        return 0
    label = a.label or (json.loads(state.read_text(encoding="utf-8")).get("label") if state.exists() else None)
    if not label:
        ap.error("--label is needed the first time")
    from page_builder.progress import PageProgress, _post  # noqa: PLC0415
    import os  # noqa: PLC0415

    token = os.environ.get("DTJ_TELEGRAM_BOT_TOKEN") or (__import__("deploy").read_var("DTJ_TELEGRAM_BOT_TOKEN") or "")
    progress = PageProgress(STATE_DIR / f"{client}.progress.json", token=token, stages=STAGES, units=UNITS)
    if a.chat and not progress.s.get("message_id"):
        progress.start(a.chat, f"Adding a shop: {label} ({a.shop})")

    def telegram(method: str, data: dict) -> None:
        if token:
            _post(f"https://api.telegram.org/bot{token}/{method}", data)

    def n8n_row(row: dict) -> None:
        from n8n_mcp import call  # noqa: PLC0415
        from setup_n8n import find_tables, table_rows  # noqa: PLC0415
        tables = find_tables(call, "dtj_stores")
        if not tables:
            raise Failed("n8n has no dtj_stores table")
        if any(r.get("myshopify_domain") == row["myshopify_domain"] for r in table_rows(call, tables[0])):
            return  # already on the list
        call("add_data_table_rows", {"dataTableId": tables[0]["id"], "projectId": tables[0].get("projectId"), "rows": [row]})

    def registry(cl: str) -> dict:
        import client_registry  # noqa: PLC0415
        return client_registry.build(cl, default_status)

    try:
        job = AddShop(a.shop, label, a.name, chat=a.chat, theme=a.theme, approved_by=a.approved_by, progress=progress if a.chat else None,
                      telegram=telegram, n8n=n8n_row, registry=registry)
        if a.link:
            job.add_links(a.link)
    except Failed as exc:
        print(f"stopped: {exc}", file=sys.stderr)
        return 1
    return job.run(a.wait_minutes)


if __name__ == "__main__":
    sys.exit(main())
