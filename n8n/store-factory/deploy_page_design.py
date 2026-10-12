"""Deploy v2 of "Store Factory: Page Design" to DTJ's n8n (one Claude Code hand-off; a "Run by Hand" start with a page brief).

    python n8n/store-factory/deploy_page_design.py --dry-run     print the operations, change nothing
    python n8n/store-factory/deploy_page_design.py               apply them (Harsh's go: "connect and deploy", 10 Oct 2026)

The code nodes are sent byte for byte from the files next to this script (page_brief.js, request_page_design.js,
reply_page_design.js), which test_page_design_nodes.py runs in Node. After the update the live workflow is read back, every code node
is compared with its file, and the export is saved as page_design.workflow.json. The workflow stays UNPUBLISHED: nothing runs on
its own. The token is read at run time from the Windows user variable N8N_MCP_TOKEN and is never printed or written.
Undo: n8n keeps every version (Workflow history, or the MCP tool restore_workflow_version).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
N8N = "https://n8n.srv2048145.hstgr.cloud/mcp-server/http"
WORKFLOW = "n8MzskKamTbVhZ3h"
TABLE = {"__rl": True, "mode": "list", "value": "7FWesTH7eVyLNuOQ", "cachedResultName": "dtj_client_intake"}
OLD_NODES = ("Ready for Approval?", "Request for Claude Code: Write to Draft", "Wait for Claude Code: Write to Draft",
             "Claude Code Reply: Write to Draft", "Record Write to Draft")
CODE_NODES = {"Page Brief (edit for each run)": "page_brief.js", "Request for Claude Code: Page Design": "request_page_design.js",
              "Claude Code Reply: Page Design": "reply_page_design.js"}
STICKY = (
    "## Store factory: page design (v2, 10 Oct 2026)\n"
    "**Start by hand:** edit the brief in **Page Brief (edit for each run)** (store, draft theme, product link, brand site, look "
    "references, notes), then press Execute workflow. Client briefs from the form start at **When a Brief Is Ready**.\n\n"
    "The run pauses at **Wait for Claude Code: Page Design**. In a Claude Code session opened in the dtj-agency-automation folder, say "
    "\"handle the Claude Code trigger in n8n\". The session reads the task list in **Request for Claude Code: Page Design**, researches "
    "the product, designs the whole page (DTJ Standard Product Page v1), runs every check and writes it into the DRAFT theme only "
    "(Harsh's standing rule; never the live theme), then posts the result here.\n\n"
    "The brief's row in **dtj_client_intake** gets page_status, preview_url, design_checks, samples and approve_code. "
    "Source in git: `n8n/store-factory/`."
)
DESCRIPTION = ("Store factory: a page brief (by hand or from the client form) goes to Claude Code, which designs the whole product page, "
               "checks it and writes it into the client's DRAFT theme. Records the result on the brief row.")


def _schema(names: list[tuple[str, str]], update: bool) -> list[dict]:
    base = {"required": False, "defaultMatch": False, "display": True}
    extra = {"canBeUsedToMatch": True} if update else {"readOnly": False, "removed": False}
    return [{"id": n, "displayName": n, **base, "type": t, **extra} for n, t in names]


def operations() -> list[dict]:
    code = {name: (HERE / f).read_text(encoding="utf-8") for name, f in CODE_NODES.items()}
    insert_cols = [("submitted_at", "string"), ("status", "string"), ("store_domain", "string"), ("theme_id", "string"),
                   ("brand_name", "string"), ("product_title", "string"), ("product_url", "string"), ("brand_website", "string"),
                   ("reference_brands", "string"), ("client_registry", "string"), ("template_suffix", "string"), ("notes", "string"),
                   ("problems", "string"), ("problem_count", "number"), ("brand_json", "string"), ("facts_json", "string"),
                   ("picture_links_json", "string"), ("raw_json", "string")]
    record_cols = [("page_status", "string"), ("approve_code", "string"), ("preview_url", "string"), ("design_checks", "string"),
                   ("samples", "number"), ("page_summary", "string"), ("page_note", "string"), ("approved_by", "string"),
                   ("page_updated_at", "string")]
    record_values = {n: f"={{{{ $json.{n} }}}}" for n, _ in record_cols}
    record_values["page_updated_at"] = "={{ $now.toISO() }}"
    ops: list[dict] = [{"type": "removeNode", "nodeName": n} for n in OLD_NODES]
    ops += [
        {"type": "updateNodeParameters", "nodeName": "Request for Claude Code: Page Design", "parameters": {"jsCode": code["Request for Claude Code: Page Design"]}},
        {"type": "updateNodeParameters", "nodeName": "Claude Code Reply: Page Design", "parameters": {"jsCode": code["Claude Code Reply: Page Design"]}},
        {"type": "setNodeParameter", "nodeName": "Record Page Design", "path": "/columns",
         "value": {"mappingMode": "defineBelow", "value": record_values, "schema": _schema(record_cols, update=True)}},
        {"type": "addNode", "node": {"name": "Run by Hand", "type": "n8n-nodes-base.manualTrigger", "typeVersion": 1, "position": [-480, 320], "parameters": {}}},
        {"type": "addNode", "node": {"name": "Page Brief (edit for each run)", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [-240, 320],
                                     "parameters": {"mode": "runOnceForAllItems", "language": "javaScript", "jsCode": code["Page Brief (edit for each run)"]}}},
        {"type": "addNode", "node": {"name": "Save Page Brief", "type": "n8n-nodes-base.dataTable", "typeVersion": 1.1, "position": [0, 320],
                                     "parameters": {"dataTableId": TABLE, "columns": {"mappingMode": "defineBelow",
                                                                                     "value": {n: f"={{{{ $json.{n} }}}}" for n, _ in insert_cols},
                                                                                     "matchingColumns": [], "schema": _schema(insert_cols, update=False)}}}},
        {"type": "addConnection", "source": "Run by Hand", "target": "Page Brief (edit for each run)"},
        {"type": "addConnection", "source": "Page Brief (edit for each run)", "target": "Save Page Brief"},
        {"type": "addConnection", "source": "Save Page Brief", "target": "Request for Claude Code: Page Design"},
        {"type": "setNodeParameter", "nodeName": "Sticky Note a4b3e49a", "path": "/content", "value": STICKY},
        {"type": "setNodeParameter", "nodeName": "Sticky Note a4b3e49a", "path": "/height", "value": 380},
        {"type": "setWorkflowMetadata", "description": DESCRIPTION},
    ]
    return ops


def _token() -> str:
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
        return winreg.QueryValueEx(k, "N8N_MCP_TOKEN")[0].strip()


def call(tool: str, arguments: dict) -> dict:
    """One MCP tool call (initialize, then tools/call). Returns the parsed JSON text of the tool's answer."""
    def rpc(body: dict, session: str | None):
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                   "Authorization": f"Bearer {_token()}", "User-Agent": "dtj-deploy/1.0"}
        if session:
            headers["Mcp-Session-Id"] = session
        req = urllib.request.Request(N8N, data=json.dumps(body).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=180) as r:
            raw, sid = r.read().decode("utf-8", "replace"), r.headers.get("Mcp-Session-Id")
        data = [l[5:].strip() for l in raw.splitlines() if l.startswith("data:")]
        return json.loads(data[-1] if data else raw), sid
    _, sid = rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                 "clientInfo": {"name": "dtj-deploy", "version": "1.0"}}}, None)
    res, _ = rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": tool, "arguments": arguments}}, sid)
    if "result" not in res:
        raise RuntimeError(f"{tool}: {json.dumps(res)[:600]}")
    text = "".join(c.get("text", "") for c in res["result"].get("content", []))
    if res["result"].get("isError"):
        raise RuntimeError(f"{tool} refused: {text[:1200]}")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"text": text}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ops = operations()
    for op in ops:
        print(f"- {op['type']}: {op.get('nodeName') or (op.get('node') or {}).get('name') or op.get('source', '') + ' -> ' + op.get('target', '') if op['type'] == 'addConnection' else op.get('nodeName') or (op.get('node') or {}).get('name') or ''}")
    if args.dry_run:
        print(f"dry run: {len(ops)} operations, nothing sent")
        return 0
    try:
        before = call("get_workflow_details", {"workflowId": WORKFLOW})["workflow"]
        names = {n["name"] for n in before["nodes"]}
        ops = [op for op in ops if not (op["type"] == "removeNode" and op["nodeName"] not in names)]  # already removed: skip
        if "Run by Hand" in names:
            print("the workflow already has v2 nodes: only the code, columns and notes are refreshed")
            ops = [op for op in ops if op["type"] not in ("addNode", "addConnection")]
        print(call("update_workflow", {"workflowId": WORKFLOW, "operations": ops}))
        after = call("get_workflow_details", {"workflowId": WORKFLOW})["workflow"]
    except (urllib.error.URLError, RuntimeError, OSError) as exc:
        print(f"not deployed: {exc}", file=sys.stderr)
        return 1
    live = {n["name"]: n for n in after["nodes"]}
    mismatched = [name for name, f in CODE_NODES.items()
                  if live.get(name, {}).get("parameters", {}).get("jsCode") != (HERE / f).read_text(encoding="utf-8")]
    left = [n for n in OLD_NODES if n in live]
    export = {k: after.get(k) for k in ("id", "name", "description", "nodes", "connections", "settings") if k in after}
    (HERE / "page_design.workflow.json").write_text(json.dumps(export, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"live nodes: {len(live)}; code nodes identical to the files: {not mismatched} {mismatched or ''}; old nodes left: {left or 'none'}; "
          f"active: {after.get('active')}; export saved: page_design.workflow.json")
    return 0 if not mismatched and not left else 1


if __name__ == "__main__":
    raise SystemExit(main())
