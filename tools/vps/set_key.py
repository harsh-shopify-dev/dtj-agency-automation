"""Save one key into the VPS worker's env file with a hidden prompt: the value is never shown, never on a command line, never in a log.

    python tools/vps/set_key.py ANTHROPIC_API_KEY        (then paste the key at the hidden prompt and press Enter)
    python tools/vps/set_key.py DTJ_CLAUDE_MAX_USD       the most one request may spend on the Claude API, e.g. 5

For keys that are not in DTJ's Bitwarden vault (the vault's own come with: python tools/team-setup/vault.py pull --env-file
~/.config/dtj/worker.env). After the prompt ends, type nothing else: the key is saved and the prompt is gone.
"""
from __future__ import annotations

import getpass
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "team-setup"))
from vault import env_file_saver  # noqa: E402

ENV_FILE = Path("~/.config/dtj/worker.env").expanduser()


def main(argv=None, ask=getpass.getpass, path: Path = ENV_FILE) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or not re.fullmatch(r"[A-Z][A-Z0-9_]{2,60}", args[0]):
        print("Name one key in capitals, e.g.: python tools/vps/set_key.py ANTHROPIC_API_KEY")
        return 1
    value = ask(f"{args[0]} (hidden, press Enter when pasted): ").strip()
    if not value:
        print("Nothing was entered: nothing saved.")
        return 1
    env_file_saver(path)(args[0], value)
    print(f"Saved {args[0]} ({len(value)} characters) in {path}. Type nothing more at this prompt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
