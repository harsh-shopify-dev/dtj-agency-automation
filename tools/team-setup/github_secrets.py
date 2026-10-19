"""Copy the keys the GitHub workflows need from this laptop into the repo's GitHub secrets (Settings > Secrets and variables > Actions).

    python tools/team-setup/github_secrets.py            which secrets GitHub has and which this laptop could send (names only)
    python tools/team-setup/github_secrets.py push       send every one this laptop has (GitHub replaces the old value)
    python tools/team-setup/github_secrets.py push NAME  send just that one

Why (Harsh, 19 Oct 2026: "keep everything centric nothing on this device"): the brand intake runs on GitHub
(.github/workflows/brand-intake.yml), so its Google Drive login and the bot token must live in GitHub, not on one laptop. Switching
the Drive to another Gmail later = `python -m page_builder.drive_upload --authorize ...` with that Gmail, then `push` again.
Run it in your OWN PowerShell; it needs the GitHub command-line tool signed in (gh auth login) with admin rights on the repo.
Values travel only through a pipe to `gh secret set`: never on screen, in a file, a log or on a command line.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from typing import Callable

import vault

REPO = "harsh-shopify-dev/dtj-agency-automation"
# secret name -> what it is for (the same names as the Windows user variables and the vault items)
NEEDED = {
    "DTJ_GDRIVE_CLIENT_ID": "brand intake: DTJ's Google app (drive_upload.py --authorize)",
    "DTJ_GDRIVE_CLIENT_SECRET": "brand intake: DTJ's Google app",
    "DTJ_GDRIVE_REFRESH_TOKEN": "brand intake: the Drive login (the Gmail that owns 'DTJ Clients')",
    "DTJ_TELEGRAM_BOT_TOKEN": "brand intake: answers in Telegram with the Drive link",
}
Run = Callable[[list, "str | None"], "subprocess.CompletedProcess[str]"]


def _gh(args: list, stdin: str | None = None) -> "subprocess.CompletedProcess[str]":
    exe = shutil.which("gh")
    if not exe:
        raise SystemExit("the GitHub command-line tool (gh) is not installed: winget install GitHub.cli, then gh auth login")
    return subprocess.run([exe, *args], input=stdin, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=60, check=False)


def on_github(run: Run) -> set[str]:
    done = run(["secret", "list", "--repo", REPO, "--json", "name", "--jq", ".[].name"], None)
    if done.returncode != 0:
        raise SystemExit(f"could not read the repo's secrets: {done.stderr.strip()[:300]} (signed in? gh auth status)")
    return {line.strip() for line in done.stdout.splitlines() if line.strip()}


def main(argv=None, run: Run = _gh, local: dict | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", nargs="?", choices=["status", "push"], default="status")
    ap.add_argument("names", nargs="*", help="with push: only these secrets")
    args = ap.parse_args(argv)
    local = vault.user_vars() if local is None else local
    unknown = [n for n in args.names if n not in NEEDED]
    if unknown:
        ap.error(f"not a secret the workflows use: {', '.join(unknown)} (known: {', '.join(NEEDED)})")
    have = on_github(run)
    if args.action == "status":
        for name, why in NEEDED.items():
            where = ("on GitHub" if name in have else "NOT on GitHub") + (", on this laptop" if local.get(name) else ", not on this laptop")
            print(f"  {name}: {where}  ({why})")
        missing = [n for n in NEEDED if n not in have]
        print("all set" if not missing else f"{len(missing)} missing: run `python tools/team-setup/github_secrets.py push`")
        return 0 if not missing else 1
    problems = 0
    for name in args.names or list(NEEDED):
        value = local.get(name, "")
        if not value:
            print(f"  {name}: not on this laptop (python tools/team-setup/vault.py pull, or see docs/ACCESS-AND-KEYS.md)")
            problems += 1
            continue
        done = run(["secret", "set", name, "--repo", REPO], value)
        if done.returncode != 0:
            print(f"  {name}: GitHub refused: {done.stderr.replace(value, '***').strip()[:300]}")
            problems += 1
        else:
            print(f"  {name}: {'replaced' if name in have else 'added'}")
    print("done" if not problems else f"done, {problems} not sent")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
