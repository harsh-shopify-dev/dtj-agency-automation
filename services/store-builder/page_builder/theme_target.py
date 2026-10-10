"""The client's DRAFT theme, reached with a Theme Access password (Shopify's Theme Access app): check it, back up its product page,
and write the approved product page into it. Nothing here can touch the live theme, publish a theme or delete a file.

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
from provision.theme import ThemeError, assert_not_live, parse_pushed_theme, push_files_cmd

PRODUCT_TEMPLATE = "templates/product.json"
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


def _run(cmd: Sequence[str], env: Mapping[str, str]) -> "subprocess.CompletedProcess[str]":
    exe = shutil.which(cmd[0]) or cmd[0]  # Windows needs the .cmd shim; a list and shell=False: no shell parsing of any value
    return subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, encoding="utf-8", errors="replace", env=dict(env),
                          stdin=subprocess.DEVNULL, timeout=600, check=False)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ThemeAccess:
    """One store, one Theme Access password. Every CLI call goes through _cli, which is the only place the password is used."""

    def __init__(self, store: str, token: str, runner: Runner = _run):
        if not token:
            raise ThemeError("no Theme Access password for this store")
        self.store = normalise_store(store)
        self._token = token
        self._runner = runner
        self.commands: list[list[str]] = []  # what ran, for the action log (the password is never part of a command)

    def __repr__(self) -> str:  # never show the password, even in a debugger or a traceback
        return f"ThemeAccess(store={self.store!r})"

    def _cli(self, cmd: list[str]) -> str:
        env = {**os.environ, "SHOPIFY_CLI_THEME_TOKEN": self._token, "SHOPIFY_FLAG_NO_COLOR": "1"}
        self.commands.append(list(cmd))
        done = self._runner(cmd, env)
        out = _ANSI.sub("", (done.stdout or "") + "\n" + (done.stderr or "")).replace(self._token, "[redacted]")
        if done.returncode != 0:
            raise ThemeError(f"shopify {' '.join(cmd[1:3])} failed ({done.returncode}): {out.strip()[:600]}")
        return _ANSI.sub("", done.stdout or "").replace(self._token, "[redacted]")

    def themes(self, theme_id: str) -> list[dict]:
        out = self._cli(["shopify", "theme", "list", "--store", self.store, "--id", str(theme_id), "--json"])
        start = min([i for i in (out.find("["), out.find("{")) if i >= 0], default=-1)
        if start < 0:
            return []
        data = json.JSONDecoder().raw_decode(out[start:])[0]
        return data if isinstance(data, list) else data.get("themes", [data])

    def pull(self, theme_id: str, files: Sequence[str], dest: Path) -> Path:
        dest.mkdir(parents=True, exist_ok=True)
        cmd = ["shopify", "theme", "pull", "--store", self.store, "--theme", str(theme_id), "--path", str(dest), "--nodelete"]
        for f in files:
            cmd += ["--only", f]
        self._cli(cmd)
        return dest

    def push_product_template(self, theme_id: str, staging: Path, file: str = PRODUCT_TEMPLATE) -> dict:
        if not re.fullmatch(r"templates/product(\.[a-z0-9-]+)?\.json", file):
            raise ThemeError(f"{file!r} is not a product template")
        cmd = push_files_cmd(self.store, str(staging), str(theme_id), [file]) + ["--json"]
        assert "--allow-live" not in cmd and "--publish" not in cmd and "--live" not in cmd
        return parse_pushed_theme(self._cli(cmd))


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
