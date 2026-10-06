"""Shopify CLI wrapper. Builds the exact command, refuses anything aimed at a live theme, and
only runs it when the caller says so (the caller checks Config.decide first).

Commands confirmed from `shopify theme push --help` (CLI 4.8.4):
  --unpublished with --theme <name> creates a NEW unpublished theme; --json returns its details.
"""
from __future__ import annotations

import json
import subprocess
from typing import Callable, Sequence

Runner = Callable[[Sequence[str]], "subprocess.CompletedProcess[str]"]


class ThemeError(Exception):
    pass


def _run(cmd: Sequence[str]) -> "subprocess.CompletedProcess[str]":
    # shell=False and a list: no shell parsing of any value. Windows needs the .cmd shim, so use shutil.which.
    import shutil

    exe = shutil.which(cmd[0]) or cmd[0]
    return subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, timeout=900, check=False)


def push_new_unpublished_cmd(store: str, theme_dir: str, theme_name: str) -> list[str]:
    if not theme_name.strip():
        raise ThemeError("theme name is required")
    return ["shopify", "theme", "push", "--store", store, "--path", theme_dir,
            "--unpublished", "--theme", theme_name, "--json"]


def push_files_cmd(store: str, theme_dir: str, theme_id: str, files: Sequence[str]) -> list[str]:
    """Narrow push to an existing theme: only named files, never delete anything."""
    if not files:
        raise ThemeError("name the files to push (--only is required)")
    if not str(theme_id).isdigit():
        raise ThemeError("theme id must be the numeric id, not a name or 'live'")
    cmd = ["shopify", "theme", "push", "--store", store, "--path", theme_dir, "--theme", str(theme_id), "--nodelete"]
    for name in files:
        cmd += ["--only", name]
    return cmd


def theme_list_cmd(store: str) -> list[str]:
    return ["shopify", "theme", "list", "--store", store, "--json"]


def theme_check_cmd(theme_dir: str) -> list[str]:
    return ["shopify", "theme", "check", "--path", theme_dir]


def assert_not_live(themes: list[dict], theme_id: str) -> None:
    """`themes` is the parsed output of theme_list_cmd. Refuse if the target is the live theme or unknown."""
    match = [t for t in themes if str(t.get("id")) == str(theme_id)]
    if not match:
        raise ThemeError(f"theme {theme_id} was not found on this store; refusing to push")
    if match[0].get("role") == "live":
        raise ThemeError(f"theme {theme_id} is the LIVE theme; automation never touches it")


def parse_pushed_theme(stdout: str) -> dict:
    """Read `--json` output from a push. Returns the theme dict; raises if Shopify did not report one."""
    try:
        data = json.loads(stdout)
    except ValueError as exc:
        raise ThemeError("could not read the CLI JSON output") from exc
    theme = data.get("theme") if isinstance(data, dict) else None
    if not theme or not theme.get("id"):
        raise ThemeError("the CLI did not report a theme id; do not call this push done")
    if theme.get("role") == "live":
        raise ThemeError("the CLI reports the theme is live; stop")
    return theme


def run(cmd: Sequence[str], runner: Runner = _run) -> "subprocess.CompletedProcess[str]":
    done = runner(cmd)
    if done.returncode != 0:
        raise ThemeError(f"command failed ({done.returncode}): {(done.stderr or done.stdout).strip()[:500]}")
    return done
