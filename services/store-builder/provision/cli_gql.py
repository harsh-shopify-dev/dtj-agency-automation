"""Transport that sends GraphQL through `shopify store execute` (the CLI holds the sign-in token, so no token
is ever in our files or environment). The allowlist in gql.check_operation is applied again here, and
--allow-mutations is added only for a mutation that passed it.

Observed behaviour (CLI 4.8.4, 5 Oct 2026): success prints the `data` object as JSON; failure prints a boxed
JSON block containing "errors" and exits non-zero.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Sequence

from .gql import check_operation
from .theme import cli_exe

Runner = Callable[[Sequence[str]], "subprocess.CompletedProcess[str]"]
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_AUTH = re.compile(r"access denied|unauthori[sz]ed|\b40[13]\b|not authenticated|no stored|scopes?\b.*(missing|required)|re-?run .*store auth", re.I)
_THROTTLE = re.compile(r"throttl|\b429\b|rate limit", re.I)


def _run(cmd: Sequence[str]) -> "subprocess.CompletedProcess[str]":
    exe = cli_exe(cmd[0])  # on PATH, or inside the Claude app's own npm folder
    return subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, encoding="utf-8", errors="replace",
                          stdin=subprocess.DEVNULL, timeout=180, check=False)


def _clean(text: str) -> str:
    return _ANSI.sub("", text).replace("\r", "")


def _first_json(text: str):
    start = text.find("{")
    if start < 0:
        return None
    try:
        return json.JSONDecoder().raw_decode(text[start:])[0]
    except ValueError:
        return None


def make_cli_transport(store: str, api_version: str, runner: Runner = _run):
    def transport(url: str, headers: dict, body: bytes) -> tuple[int, dict, dict]:
        request = json.loads(body)
        kind = check_operation(request["query"])  # defence in depth: never trust the caller
        with tempfile.TemporaryDirectory() as tmp:
            qf, vf = Path(tmp, "q.graphql"), Path(tmp, "v.json")
            qf.write_text(request["query"], encoding="utf-8")
            vf.write_text(json.dumps(request.get("variables") or {}), encoding="utf-8")
            cmd = ["shopify", "store", "execute", "--store", store, "--version", api_version, "--json",
                   "--query-file", str(qf), "--variable-file", str(vf)]
            if kind == "mutation":
                cmd.append("--allow-mutations")
            done = runner(cmd)
        out = _clean((done.stdout or "") + "\n" + (done.stderr or ""))
        parsed = _first_json(out)
        if done.returncode == 0 and isinstance(parsed, dict) and "errors" not in parsed:
            return 200, {}, {"data": parsed}
        errors = parsed.get("errors") if isinstance(parsed, dict) else None
        message = "; ".join(str(e.get("message")) for e in errors or [] if isinstance(e, dict)) or out.strip()[-400:]
        if _AUTH.search(message):
            return 401, {}, {"errors": [{"message": message}]}
        if _THROTTLE.search(message):
            return 429, {}, {"errors": [{"message": message}]}
        return 400, {}, {"errors": [{"message": message}]}

    return transport
