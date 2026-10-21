"""The client's DRAFT theme, reached with a Theme Access password (Shopify's Theme Access app) or, when the laptop has none for the
store, with the Shopify CLI's own login (DTJ's partner account as the store's collaborator; Harsh, 21 Oct 2026: "My collaborator
login"): check it, back up its product page, write the approved page into it, and make the draft copy of the live theme. Nothing
here can touch the live theme, publish a theme or delete a file.

The password is read from the environment variable named by token_env_name(store) (on Windows also from the user's saved variables,
because a running app does not see variables saved after it started). It is handed to the Shopify CLI only through the
SHOPIFY_CLI_THEME_TOKEN variable of the child process: never on a command line, in a file, in a log or in printed output.

Commands as documented by `shopify theme list|pull|push --help` (CLI 4.x, read 9 Oct 2026): --password / SHOPIFY_CLI_THEME_TOKEN takes
"a password generated from the Theme Access app"; push --json returns {"theme": {id, name, role, editor_url, preview_url}}.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Callable, Mapping, Sequence

from provision import templates
from provision.theme import ThemeError, assert_not_live, cli_exe, outside_git, parse_pushed_theme, push_files_cmd

PRODUCT_TEMPLATE = "templates/product.json"
HOME_TEMPLATE = "templates/index.json"  # the home page (Harsh, 13 Oct 2026: home pages follow the same draft rule)
# the only files the page builder ever writes: page templates, and the header and footer groups (21 Oct 2026, run_chrome; on every page,
# so always a person's yes)
PAGE_FILES = re.compile(r"templates/((product|collection)(\.[a-z0-9-]+)?|index)\.json|sections/(header|footer)-group\.json")
SCHEMA_FILE = "config/settings_schema.json"
SUPPORTED_THEMES = ("Horizon", "Dawn")  # the layouts assemble.py knows (Dawn added 9 Oct 2026)
THEME_DIRS = ("assets", "blocks", "config", "layout", "locales", "sections", "snippets", "templates")
Runner = Callable[[Sequence[str], Mapping[str, str]], "subprocess.CompletedProcess[str]"]
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def normalise_store(store: str) -> str:
    s = store.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
    if not s.endswith(".myshopify.com"):
        s += ".myshopify.com"
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.myshopify\.com", s):
        raise ThemeError(f"{store!r} is not a .myshopify.com store address")
    return s


def token_env_name(store: str) -> str:
    handle = normalise_store(store).split(".")[0]
    return "DTJ_THEME_ACCESS_" + re.sub(r"[^A-Z0-9]", "_", handle.upper())


def read_token(store: str, environ: Mapping[str, str] | None = None, registry: bool = True) -> str | None:
    name = token_env_name(store)
    value = (environ if environ is not None else os.environ).get(name)
    if not value and registry and os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                value = winreg.QueryValueEx(key, name)[0]
        except OSError:
            value = None
    return value or None


# The CLI sometimes freezes (20 and 21 Oct 2026: a theme pull sat idle for 10+ minutes, no CPU, no child, while the same pull a minute
# later took 10 s). subprocess.run's own timeout cannot end it on Windows: it kills the cmd.exe shim, the node process under it keeps the
# pipes open and Python waits forever. So each call gets a limit, the WHOLE process tree is stopped when it passes, and a read is tried
# once more. A write is never repeated here: push_page reads the theme back to see whether a stopped write landed.
LIMITS = {"pull": 180, "list": 90, "push": 300, "duplicate": 300}


def _kill_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True, check=False)
    else:  # pragma: no cover - the team's laptops are Windows
        try:
            os.killpg(os.getpgid(pid), 9)
        except OSError:
            pass


def _run(cmd: Sequence[str], env: Mapping[str, str], popen=subprocess.Popen) -> "subprocess.CompletedProcess[str]":
    cmd, cwd, extra = outside_git(cmd)  # absolute --path, no git project in sight: the CLI's "uncommitted changes, proceed?" never comes
    exe = cli_exe(cmd[0])  # the .cmd shim on PATH, or the CLI inside the Claude app's own npm folder; a list and shell=False: no shell parsing
    kind = next((k for k in LIMITS if k in cmd[1:3]), "")
    limit = LIMITS.get(kind, 600)
    tries = 2 if kind in ("pull", "list") else 1
    for attempt in range(1, tries + 1):
        p = popen([exe, *cmd[1:]], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                  errors="replace", env={**env, **extra}, cwd=cwd)
        try:
            out, err = p.communicate(timeout=limit)
            return subprocess.CompletedProcess([exe, *cmd[1:]], p.returncode, out, err)
        except subprocess.TimeoutExpired:
            _kill_tree(p.pid)
            try:
                p.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                pass
    raise ThemeError(f"shopify {kind or ' '.join(cmd[1:3])} did not answer within {limit} s"
                     + (f" ({tries} tries); it was stopped" if tries > 1 else "; it was stopped (a write may still have landed: read the theme back)"))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


LOGIN_REFUSED = re.compile(r"log ?in|authenticat|not authori[sz]ed|unauthori[sz]ed|access denied|forbidden|\b40[13]\b|permission",
                           re.I)


class ThemeAccess:
    """One store, reached with a Theme Access password or (login=True) with the CLI's own login. Every CLI call goes through _cli,
    which is the only place the password is used."""

    def __init__(self, store: str, token: str | None, runner: Runner = _run, login: bool = False):
        if not token and not login:
            raise ThemeError("no Theme Access password for this store")
        self.store = normalise_store(store)
        self._token = token or ""
        self.login = not self._token  # no password: the CLI's own login (a collaborator account), never a browser prompt
        self._runner = runner
        self.commands: list[list[str]] = []  # what ran, for the action log (the password is never part of a command)

    def __repr__(self) -> str:  # never show the password, even in a debugger or a traceback
        return f"ThemeAccess(store={self.store!r}, login={self.login})"

    def _hide(self, text: str) -> str:
        return text.replace(self._token, "[redacted]") if self._token else text

    def _cli(self, cmd: list[str]) -> str:
        env = {**os.environ, "SHOPIFY_FLAG_NO_COLOR": "1"}
        if self._token:
            env["SHOPIFY_CLI_THEME_TOKEN"] = self._token
        else:
            env.pop("SHOPIFY_CLI_THEME_TOKEN", None)
            env["SHOPIFY_FLAG_NO_INPUT"] = "1"  # not logged in = a clear error now, not a login page waiting for a person
        self.commands.append(list(cmd))
        done = self._runner(cmd, env)
        out = self._hide(_ANSI.sub("", (done.stdout or "") + "\n" + (done.stderr or "")))
        if done.returncode != 0:
            if self.login and LOGIN_REFUSED.search(out):
                raise ThemeError(
                    f"the Shopify CLI on this laptop has no access to {self.store}'s themes ({out.strip()[:200]}). Either: the store "
                    "owner accepts DTJ's collaborator request (with Themes), then someone runs `shopify theme list --store "
                    f"{self.store}` once in their own terminal and logs in with DTJ's account; or save a Theme Access password as "
                    f"the user variable {token_env_name(self.store)}")
            raise ThemeError(f"shopify {' '.join(cmd[1:3])} failed ({done.returncode}): {out.strip()[:600]}")
        if "pushed with errors" in out:  # the CLI exits 0 when Shopify refuses a file (10 Oct 2026: a range value off its step)
            words = " ".join(x for x in (ln.strip(" │╭╮╰╯─") for ln in out.splitlines()) if x)  # drop the CLI's box drawing
            raise ThemeError(f"Shopify refused part of the push: {words[:600]}")
        return self._hide(_ANSI.sub("", done.stdout or ""))

    def themes(self, theme_id: str | None = None, role: str | None = None, name: str | None = None) -> list[dict]:
        cmd = ["shopify", "theme", "list", "--store", self.store, "--json"]
        for flag, value in (("--id", theme_id), ("--role", role), ("--name", name)):
            if value:
                cmd[5:5] = [flag, str(value)]
        out = self._cli(cmd)
        start = min([i for i in (out.find("["), out.find("{")) if i >= 0], default=-1)
        if start < 0:
            return []
        data = json.JSONDecoder().raw_decode(out[start:])[0]
        return data if isinstance(data, list) else data.get("themes", [data])

    def duplicate_live(self, name: str) -> dict:
        """The draft copy: the LIVE theme duplicated as a new UNPUBLISHED theme called `name` (never published, nothing deleted).
        Returns the new theme ({id, name, role}); refuses when a theme of that name exists already or the copy is not unpublished."""
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .:_()-]{2,49}", name):
            raise ThemeError(f"theme name {name!r}: 3 to 50 letters, digits, spaces and . : _ ( ) -")
        live = [t for t in self.themes(role="live") if t.get("role") == "live"]
        if len(live) != 1:
            raise ThemeError(f"could not find the one live theme of {self.store} ({len(live)} found)")
        if [t for t in self.themes(name=name) if t.get("name") == name]:
            raise ThemeError(f"a theme called {name!r} is on {self.store} already: use it, or choose another name")
        cmd = ["shopify", "theme", "duplicate", "--store", self.store, "--theme", str(live[0]["id"]), "--name", name, "--force", "--json"]
        assert "--publish" not in cmd and "--live" not in cmd and "--allow-live" not in cmd
        self._cli(cmd)
        made = [t for t in self.themes(name=name) if t.get("name") == name]  # read back: the CLI's own output format is not documented
        if len(made) != 1:
            raise ThemeError(f"the copy {name!r} was not found on {self.store} after duplicating ({len(made)} found)")
        if made[0].get("role") != "unpublished":
            raise ThemeError(f"the copy {name!r} has role {made[0].get('role')!r}, not unpublished: stop and tell Harsh")
        return {"id": str(made[0]["id"]), "name": name, "role": "unpublished", "from_live": str(live[0]["id"]),
                "from_live_name": live[0].get("name")}

    def pull(self, theme_id: str, files: Sequence[str], dest: Path) -> Path:
        dest.mkdir(parents=True, exist_ok=True)
        cmd = ["shopify", "theme", "pull", "--store", self.store, "--theme", str(theme_id), "--path", str(dest), "--nodelete"]
        for f in files:
            cmd += ["--only", f]
        self._cli(cmd)
        return dest

    def push_product_template(self, theme_id: str, staging: Path, file: str = PRODUCT_TEMPLATE) -> dict:
        """Write ONE page template (a product template or the home page) into the theme; nothing else, nothing deleted, never published."""
        if not PAGE_FILES.fullmatch(file):
            raise ThemeError(f"{file!r} is not a file the page builder writes (a product or collection template, templates/index.json, "
                             "or the header / footer group)")
        cmd = push_files_cmd(self.store, str(staging), str(theme_id), [file]) + ["--json"]
        assert "--allow-live" not in cmd and "--publish" not in cmd and "--live" not in cmd
        return parse_pushed_theme(self._cli(cmd))


def open_access(store: str, runner: Runner = _run, environ: Mapping[str, str] | None = None, registry: bool = True) -> ThemeAccess:
    """The Theme Access password when this laptop has one for the store, else the CLI's own login (its first call says clearly when
    that login has no access)."""
    token = read_token(store, environ, registry)
    return ThemeAccess(store, token, runner) if token else ThemeAccess(store, None, runner, login=True)


def template_file(suffix: str | None) -> str:
    """templates/product.json, or an alternate product template templates/product.<suffix>.json (a new page, chosen per product)."""
    if not suffix:
        return PRODUCT_TEMPLATE
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", suffix):
        raise ThemeError(f"template name {suffix!r}: use lowercase letters, numbers and dashes")
    return f"templates/product.{suffix}.json"


def check_target(access: ThemeAccess, theme_id: str, workdir: Path, file: str = PRODUCT_TEMPLATE) -> dict:
    """Read-only. Refuses a live, unknown or non-draft theme and a theme the builder does not support; backs up the page being replaced
    (`file`) and keeps the theme's own product.json (a Dawn page is built on it)."""
    if not str(theme_id).isdigit():
        raise ThemeError(f"theme id must be the number from the theme's address in Shopify admin, not {theme_id!r}")
    themes = access.themes(theme_id)
    assert_not_live(themes, theme_id)
    theme = next(t for t in themes if str(t.get("id")) == str(theme_id))
    if theme.get("role") != "unpublished":
        raise ThemeError(f"theme {theme_id} has role {theme.get('role')!r}; only a draft (unpublished) copy of the theme is allowed")
    before = access.pull(theme_id, sorted({SCHEMA_FILE, PRODUCT_TEMPLATE, file}), workdir)
    schema_path = before / SCHEMA_FILE
    if not schema_path.exists():
        raise ThemeError("could not read the theme's settings (config/settings_schema.json): is this an Online Store 2.0 theme?")
    info = next((s for s in json.loads(schema_path.read_text(encoding="utf-8")) if s.get("name") == "theme_info"), {})
    base = info.get("theme_name", "")
    if base not in SUPPORTED_THEMES:
        raise ThemeError(f"theme {theme_id} is built on {base or 'an unknown theme'!r}; the page builder supports {', '.join(SUPPORTED_THEMES)} only")
    current = before / file
    return {
        "store": access.store, "theme_id": str(theme_id), "theme_name": theme.get("name"), "role": theme.get("role"),
        "base_theme": base, "base_version": info.get("theme_version"), "file": file,
        "theme_product_template": str(before / PRODUCT_TEMPLATE) if (before / PRODUCT_TEMPLATE).exists() else None,
        "current_product_template_sha256": sha256(current.read_bytes()) if current.exists() else None,
        "backup": str(current) if current.exists() else None,
    }


def template_bytes(template: dict) -> bytes:
    """Exactly the bytes that are approved and pushed."""
    return (json.dumps(template, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def stage(template_path: Path, staging: Path, file: str = PRODUCT_TEMPLATE) -> Path:
    """A minimal theme folder holding only the product template (the CLI wants the standard theme folder layout)."""
    if staging.exists():
        shutil.rmtree(staging)
    for d in THEME_DIRS:
        (staging / d).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template_path, staging / file)
    return staging


def same_template(pushed: bytes, pulled_text: str) -> bool:
    """Shopify may add a comment header or reformat; compare the parsed JSON."""
    return templates.load(pulled_text)[1] == json.loads(pushed.decode("utf-8"))


def fetch_store_product(store: str, handle: str, get: Callable[[str], tuple[int, str, str]] | None = None) -> dict | None:
    """The product as the store shows it publicly (/products/<handle>.js). None when the store is password-protected or it fails:
    this is context for the plan, never page content."""
    def _get(url: str) -> tuple[int, str, str]:
        req = urllib.request.Request(url, headers={"User-Agent": "dtj-page-builder/1", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.geturl(), r.read().decode("utf-8", "replace")

    try:
        status, final_url, body = (get or _get)(f"https://{normalise_store(store)}/products/{handle}.js")
        if status != 200 or "/password" in final_url:
            return None
        p = json.loads(body)
    except Exception:  # noqa: BLE001 - optional context only
        return None
    return {
        "title": p.get("title"), "price_minor_units": p.get("price"), "compare_at_price_minor_units": p.get("compare_at_price"),
        "options": [o.get("name") if isinstance(o, dict) else o for o in p.get("options", [])],
        "variant_count": len(p.get("variants", [])), "available": p.get("available"), "image_count": len(p.get("images", [])),
    }
