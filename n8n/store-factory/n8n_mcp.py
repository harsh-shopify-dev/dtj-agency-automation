"""One call to DTJ's n8n through its MCP server (used by the deploy scripts in this folder).

The token is read at run time from the Windows USER variable N8N_MCP_TOKEN (the registry, so a value saved after a program started
is still seen), or on the VPS from the environment, and is never printed or written anywhere.
"""
from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_HOST = "n8n.srv2048145.hstgr.cloud"  # DTJ's n8n since 10 Oct 2026 (moved from n8n.srv1969859.hstgr.cloud)


def n8n_host(mcp_json: Path = Path(__file__).resolve().parents[2] / ".mcp.json") -> str:
    """The n8n server Claude Code in this folder talks to: the "n8n" address in .mcp.json (so a move to a new server is one
    edit there), else DTJ's current server."""
    try:
        url = json.loads(mcp_json.read_text(encoding="utf-8"))["mcpServers"]["n8n"]["url"]
    except (OSError, ValueError, KeyError, TypeError):
        return DEFAULT_HOST
    m = re.match(r"^https://([a-z0-9.-]+)/", str(url))
    return m.group(1) if m else DEFAULT_HOST


N8N_HOST = n8n_host()
ENDPOINT = f"https://{N8N_HOST}/mcp-server/http"
PROJECT = "NuKdhPFWwCCbm1K3"
INTAKE_TABLE = "7FWesTH7eVyLNuOQ"   # dtj_client_intake
STORES_TABLE = "QaOZ6MuvFLyft2y9"   # dtj_stores
PAGE_DESIGN = "n8MzskKamTbVhZ3h"    # Store Factory: Page Design


def token() -> str:
    """The Windows user variable on a laptop; the environment on the VPS (the worker's EnvironmentFile)."""
    import os
    if os.name != "nt":
        return os.environ.get("N8N_MCP_TOKEN", "").strip()
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
        return winreg.QueryValueEx(k, "N8N_MCP_TOKEN")[0].strip()


SESSION_SECONDS = 240  # one MCP session is reused this long (23 Oct 2026: the VPS worker's own reads made n8n answer 429)
_SESSION = {"id": None, "at": 0.0, "stateless": False}  # n8n gives no session id and takes tools/call without one (checked 23 Oct 2026)
_LOCK = threading.Lock()


def _init(rpc) -> str | None:
    _, sid = rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                 "clientInfo": {"name": "dtj-deploy", "version": "1.0"}}}, None)
    return sid


def call(tool: str, arguments: dict, clock=time.monotonic, sleep=time.sleep) -> dict:
    """tools/call on a reused session (initialize only when there is none, it is old, or n8n dropped it); a 429 is waited out twice.
    Returns the tool's answer parsed as JSON (or {"text": ...}). Raises RuntimeError on a refusal."""
    def rpc(body: dict, session: str | None):
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                   "Authorization": f"Bearer {token()}", "User-Agent": "dtj-deploy/1.0"}
        if session:
            headers["Mcp-Session-Id"] = session
        req = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=180) as r:
            raw, sid = r.read().decode("utf-8", "replace"), r.headers.get("Mcp-Session-Id")
        data = [line[5:].strip() for line in raw.splitlines() if line.startswith("data:")]
        return json.loads(data[-1] if data else raw), sid

    body = {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": tool, "arguments": arguments}}
    res = None
    for attempt in range(3):
        with _LOCK:
            if not _SESSION["stateless"] and (not _SESSION["id"] or clock() - _SESSION["at"] > SESSION_SECONDS):
                sid = _init(rpc)
                _SESSION.update(id=sid, at=clock(), stateless=sid is None)  # no id: no initialize needed from now on
            sid = _SESSION["id"]
        try:
            res, _ = rpc(body, sid)
            break
        except urllib.error.HTTPError as exc:
            if exc.code in (400, 404) and attempt == 0:  # the session ended on n8n's side: a fresh one, once
                with _LOCK:
                    _SESSION.update(id=None)
                continue
            if exc.code == 429 and attempt < 2:
                sleep(5 * (attempt + 1))
                continue
            raise
    if "result" not in res:
        raise RuntimeError(f"{tool}: {json.dumps(res)[:600]}")
    text = "".join(c.get("text", "") for c in res["result"].get("content", []))
    if res["result"].get("isError"):
        raise RuntimeError(f"{tool} refused: {text[:1500]}")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"text": text}
