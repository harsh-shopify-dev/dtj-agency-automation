"""One call to DTJ's n8n through its MCP server (used by the deploy scripts in this folder).

The token is read at run time from the Windows USER variable N8N_MCP_TOKEN (the registry, so a value saved after a program started
is still seen) and is never printed or written anywhere.
"""
from __future__ import annotations

import json
import urllib.request

N8N_HOST = "n8n.srv2048145.hstgr.cloud"
ENDPOINT = f"https://{N8N_HOST}/mcp-server/http"
PROJECT = "NuKdhPFWwCCbm1K3"
INTAKE_TABLE = "7FWesTH7eVyLNuOQ"   # dtj_client_intake
STORES_TABLE = "QaOZ6MuvFLyft2y9"   # dtj_stores
PAGE_DESIGN = "n8MzskKamTbVhZ3h"    # Store Factory: Page Design


def token() -> str:
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
        return winreg.QueryValueEx(k, "N8N_MCP_TOKEN")[0].strip()


def call(tool: str, arguments: dict) -> dict:
    """initialize, then tools/call; returns the tool's answer parsed as JSON (or {"text": ...}). Raises RuntimeError on a refusal."""
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

    _, sid = rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                 "clientInfo": {"name": "dtj-deploy", "version": "1.0"}}}, None)
    res, _ = rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": tool, "arguments": arguments}}, sid)
    if "result" not in res:
        raise RuntimeError(f"{tool}: {json.dumps(res)[:600]}")
    text = "".join(c.get("text", "") for c in res["result"].get("content", []))
    if res["result"].get("isError"):
        raise RuntimeError(f"{tool} refused: {text[:1500]}")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"text": text}
