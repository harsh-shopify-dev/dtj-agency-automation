"""Deploy "Store Factory: Page Design" to DTJ's n8n: one Claude Code hand-off for a saved brief.

    python n8n/store-factory/deploy_page_design.py --dry-run     print the operations, change nothing
    python n8n/store-factory/deploy_page_design.py               apply them

Briefs come in at "When a Brief Is Ready" (row_id), started by "Store Factory: New Page" (a product link, by hand or from the
Telegram bot) or by the client form ("Shopify Automation"). The code nodes are sent byte for byte from request_page_design.js and
reply_page_design.js (run in Node by test_page_design_nodes.py); afterwards the live workflow is read back, compared with the files
and exported to page_design.workflow.json. The workflow stays UNPUBLISHED. Running it again is safe: it only sends what is missing
or changed. Undo: n8n keeps every version (Workflow history, or restore_workflow_version).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from n8n_mcp import INTAKE_TABLE, PAGE_DESIGN, call  # noqa: E402

HERE = Path(__file__).resolve().parent
OLD_NODES = ("Ready for Approval?", "Request for Claude Code: Write to Draft", "Wait for Claude Code: Write to Draft",
             "Claude Code Reply: Write to Draft", "Record Write to Draft",
             # the 10 Oct start-by-hand path moved to "Store Factory: New Page" (a product link is enough there)
             "Run by Hand", "Page Brief (edit for each run)", "Save Page Brief")
CODE_NODES = {"Request for Claude Code: Page Design": "request_page_design.js", "Claude Code Reply: Page Design": "reply_page_design.js"}
STICKY = (
    "## Store factory: page design\n"
    "Started with a brief row id by **Store Factory: New Page** (paste a product link there, or send it to the Telegram bot) or by "
    "the client form.\n\n"
    "The run pauses at **Wait for Claude Code: Page Design**. In a Claude Code session opened in the dtj-agency-automation folder, say "
    "\"handle the Claude Code trigger in n8n\". The session reads the task list in **Request for Claude Code: Page Design**, researches "
    "the product, designs the whole page (DTJ Standard Product Page v1), runs every check and writes it into the DRAFT theme only "
    "(Harsh's standing rule; never the live theme), then posts the result here.\n\n"
    "The brief's row in **dtj_client_intake** gets page_status, preview_url, design_checks, samples and approve_code. "
    "Source in git: `n8n/store-factory/`."
)
DESCRIPTION = ("Store factory: a saved page brief goes to Claude Code, which designs the whole product page, checks it and writes it "
               "into the client's DRAFT theme. Records the result on the brief row.")
RECORD_COLS = [("page_status", "string"), ("approve_code", "string"), ("preview_url", "string"), ("design_checks", "string"),
               ("samples", "number"), ("page_summary", "string"), ("page_note", "string"), ("approved_by", "string"),
               ("page_updated_at", "string")]


def operations(live_names: set[str] | None = None) -> list[dict]:
    names = live_names if live_names is not None else set(OLD_NODES)
    code = {name: (HERE / f).read_text(encoding="utf-8") for name, f in CODE_NODES.items()}
    values = {n: f"={{{{ $json.{n} }}}}" for n, _ in RECORD_COLS}
    values["page_updated_at"] = "={{ $now.toISO() }}"
    schema = [{"id": n, "displayName": n, "required": False, "defaultMatch": False, "display": True, "type": t, "canBeUsedToMatch": True}
              for n, t in RECORD_COLS]
    ops: list[dict] = [{"type": "removeNode", "nodeName": n} for n in OLD_NODES if n in names]
    ops += [{"type": "updateNodeParameters", "nodeName": name, "parameters": {"jsCode": js}} for name, js in code.items()]
    ops += [
        {"type": "setNodeParameter", "nodeName": "Record Page Design", "path": "/columns",
         "value": {"mappingMode": "defineBelow", "value": values, "schema": schema}},
        {"type": "setNodeParameter", "nodeName": "Sticky Note a4b3e49a", "path": "/content", "value": STICKY},
        {"type": "setNodeParameter", "nodeName": "Sticky Note a4b3e49a", "path": "/height", "value": 380},
        {"type": "setWorkflowMetadata", "description": DESCRIPTION},
    ]
    return ops


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.dry_run:
        for op in operations():
            print(f"- {op['type']}: {op.get('nodeName', '')}")
        print("dry run: nothing sent")
        return 0
    try:
        before = call("get_workflow_details", {"workflowId": PAGE_DESIGN})["workflow"]
        ops = operations({n["name"] for n in before["nodes"]})
        for op in ops:
            print(f"- {op['type']}: {op.get('nodeName', '')}")
        print(call("update_workflow", {"workflowId": PAGE_DESIGN, "operations": ops}))
        after = call("get_workflow_details", {"workflowId": PAGE_DESIGN})["workflow"]
    except (urllib.error.URLError, RuntimeError, OSError) as exc:
        print(f"not deployed: {exc}", file=sys.stderr)
        return 1
    live = {n["name"]: n for n in after["nodes"]}
    mismatched = [name for name, f in CODE_NODES.items()
                  if live.get(name, {}).get("parameters", {}).get("jsCode") != (HERE / f).read_text(encoding="utf-8")]
    left = [n for n in OLD_NODES if n in live]
    export = {k: after.get(k) for k in ("id", "name", "description", "nodes", "connections", "settings") if k in after}
    (HERE / "page_design.workflow.json").write_text(json.dumps(export, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"live nodes: {len(live)}; code identical to the files: {not mismatched} {mismatched or ''}; old nodes left: {left or 'none'}; "
          f"active: {after.get('active')}; table {INTAKE_TABLE}; export saved: page_design.workflow.json")
    return 0 if not mismatched and not left else 1


if __name__ == "__main__":
    raise SystemExit(main())
