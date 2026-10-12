"""Deploy "Store Factory: New Page" to DTJ's n8n: a product link (+ an optional note) is all a person gives.

    python n8n/store-factory/deploy_new_page.py --dry-run     print the generated workflow code, change nothing
    python n8n/store-factory/deploy_new_page.py               create it (or refresh its code nodes when it exists)

Run by Hand -> What to Design (edit me) ─┐
From Another Workflow (the Telegram bot) ┴> Take the Request -> Load Stores (dtj_stores) -> Match the Store -> Matched?
    yes -> Save Brief (dtj_client_intake) -> Start Page Design (does not wait) -> Started   (the answer to show the person)
    no  -> Not Started                                                                      (a plain reason; nothing saved)
The code nodes are the .js files next to this script (run in Node by test_new_page_nodes.py), sent byte for byte; afterwards the live
workflow is read back, compared and exported to new_page.workflow.json. The workflow stays UNPUBLISHED (a manual run or a call
from another workflow still works). Undo: n8n keeps every version.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from n8n_mcp import INTAKE_TABLE, PAGE_DESIGN, STORES_TABLE, call  # noqa: E402

HERE = Path(__file__).resolve().parent
NAME = "Store Factory: New Page"
CODE_NODES = {"What to Design (edit me)": "what_to_design.js", "Take the Request": "take_request.js",
              "Match the Store": "match_store.js", "Started": "started.js", "Not Started": "not_started.js"}
ROW_COLS = [("submitted_at", "string"), ("status", "string"), ("store_domain", "string"), ("theme_id", "string"), ("brand_name", "string"),
            ("product_title", "string"), ("product_url", "string"), ("brand_website", "string"), ("reference_brands", "string"),
            ("client_registry", "string"), ("template_suffix", "string"), ("notes", "string"), ("problems", "string"),
            ("problem_count", "number"), ("brand_json", "string"), ("facts_json", "string"), ("picture_links_json", "string"),
            ("raw_json", "string"), ("requested_by", "string"), ("telegram_chat_id", "string")]
DESCRIPTION = ("Store factory: a product link (by hand or from the Telegram bot) -> the shop from dtj_stores -> a saved brief -> "
               "Store Factory: Page Design (Claude Code designs the page into the draft theme).")
STICKY = ("## New page: just a product link\n"
          "**By hand:** open **What to Design (edit me)**, paste the product link from the shop's website (and a note if you like), "
          "save, press **Execute workflow**. The output of **Started** (or **Not Started**) says what happens next.\n\n"
          "**From the Telegram bot:** the bot calls this workflow with the link and the person's note.\n\n"
          "The shop is found in the data table **dtj_stores** (one row per shop: addresses, draft theme, app copies, brand site). "
          "A shop that is not in it is refused with a plain message. Source in git: `n8n/store-factory/`.")


def sdk_code() -> str:
    js = {name: json.dumps((HERE / f).read_text(encoding="utf-8")) for name, f in CODE_NODES.items()}
    values = json.dumps({n: f"={{{{ $json.row.{n} }}}}" for n, _ in ROW_COLS})
    schema = json.dumps([{"id": n, "displayName": n, "required": False, "defaultMatch": False, "display": True, "type": t,
                          "readOnly": False, "removed": False} for n, t in ROW_COLS])
    code_node = lambda var, name, pos: (  # noqa: E731
        f"const {var} = node({{ type: 'n8n-nodes-base.code', version: 2, config: {{ name: {json.dumps(name)}, position: {pos}, "
        f"parameters: {{ mode: 'runOnceForAllItems', language: 'javaScript', jsCode: {js[name]} }} }} }});\n")
    return (
        "import { workflow, node, trigger, sticky, ifElse, expr } from '@n8n/workflow-sdk';\n\n"
        "const byHand = trigger({ type: 'n8n-nodes-base.manualTrigger', version: 1, config: { name: 'Run by Hand', position: [0, 0] } });\n"
        + code_node("whatToDesign", "What to Design (edit me)", "[240, 0]")
        + "const fromWorkflow = trigger({ type: 'n8n-nodes-base.executeWorkflowTrigger', version: 1.2, config: { name: 'From Another Workflow', "
          "position: [240, 240], parameters: { inputSource: 'workflowInputs', workflowInputs: { values: ["
          "{ name: 'product_link', type: 'string' }, { name: 'note', type: 'string' }, { name: 'requested_by', type: 'string' }, "
          "{ name: 'chat_id', type: 'string' }] } } } });\n"
        + code_node("takeRequest", "Take the Request", "[480, 120]")
        + "const loadStores = node({ type: 'n8n-nodes-base.dataTable', version: 1.1, config: { name: 'Load Stores', position: [720, 120], "
          "executeOnce: true, alwaysOutputData: true, parameters: { resource: 'row', operation: 'get', "
          f"dataTableId: {{ __rl: true, mode: 'list', value: '{STORES_TABLE}', cachedResultName: 'dtj_stores' }}, matchType: 'allConditions', "
          "filters: { conditions: [{ keyName: 'myshopify_domain', condition: 'isNotEmpty' }] }, returnAll: true } } });\n"
        + code_node("matchStore", "Match the Store", "[960, 120]")
        + "const matched = ifElse({ version: 2.2, config: { name: 'Matched?', position: [1200, 120], parameters: { conditions: { "
          "options: { caseSensitive: true, leftValue: '', typeValidation: 'loose' }, conditions: [{ leftValue: expr('{{ $json.ok }}'), "
          "rightValue: '', operator: { type: 'boolean', operation: 'true', singleValue: true } }], combinator: 'and' } } } });\n"
        + "const saveBrief = node({ type: 'n8n-nodes-base.dataTable', version: 1.1, config: { name: 'Save Brief', position: [1440, 0], "
          "parameters: { resource: 'row', operation: 'insert', "
          f"dataTableId: {{ __rl: true, mode: 'list', value: '{INTAKE_TABLE}', cachedResultName: 'dtj_client_intake' }}, "
          f"columns: {{ mappingMode: 'defineBelow', value: {values}, matchingColumns: [], schema: {schema} }} }} }} }});\n"
        + "const startDesign = node({ type: 'n8n-nodes-base.executeWorkflow', version: 1.3, config: { name: 'Start Page Design', "
          "position: [1680, 0], parameters: { "
          f"workflowId: {{ __rl: true, mode: 'list', value: '{PAGE_DESIGN}', cachedResultName: 'Store Factory: Page Design' }}, "
          "workflowInputs: { mappingMode: 'defineBelow', value: { row_id: '={{ $json.id }}' }, matchingColumns: [], schema: [{ id: 'row_id', "
          "displayName: 'row_id', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'number' }], "
          "attemptToConvertTypes: false, convertFieldsToString: true }, mode: 'each', options: { waitForSubWorkflow: false } } } });\n"
        + code_node("started", "Started", "[1920, 0]")
        + code_node("notStarted", "Not Started", "[1440, 240]")
        + f"const about = sticky({json.dumps(STICKY)}, [byHand, whatToDesign, fromWorkflow, takeRequest], "
          "{ color: 5, position: [-40, -380], width: 760, height: 340 });\n\n"
        "export default workflow('store-factory-new-page', " + json.dumps(NAME) + ")\n"
        "  .add(byHand).to(whatToDesign).to(takeRequest)\n"
        "  .add(fromWorkflow).to(takeRequest)\n"
        "  .add(takeRequest).to(loadStores).to(matchStore)\n"
        "  .to(matched.onTrue(saveBrief.to(startDesign.to(started))).onFalse(notStarted))\n"
        "  .add(about);\n"
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    code = sdk_code()
    if args.dry_run:
        print(code)
        return 0
    try:
        found = [w for w in call("search_workflows", {"query": NAME}).get("data", []) if w.get("name") == NAME]
        if found:
            wf_id = found[0]["id"]
            ops = [{"type": "updateNodeParameters", "nodeName": n, "parameters": {"jsCode": (HERE / f).read_text(encoding="utf-8")}}
                   for n, f in CODE_NODES.items()]
            print("exists: refreshing its code nodes", call("update_workflow", {"workflowId": wf_id, "operations": ops}))
        else:
            check = call("validate_workflow", {"code": code})
            print("validate:", json.dumps(check)[:800])
            if check.get("valid") is False or check.get("errors"):
                return 1
            made = call("create_workflow_from_code", {"code": code, "description": DESCRIPTION,
                                                      "versionName": "New page from a product link"})
            print("created:", json.dumps(made)[:600])
            wf_id = made.get("workflowId") or made.get("id")
        after = call("get_workflow_details", {"workflowId": wf_id})["workflow"]
    except (urllib.error.URLError, RuntimeError, OSError) as exc:
        print(f"not deployed: {exc}", file=sys.stderr)
        return 1
    live = {n["name"]: n for n in after["nodes"]}
    mismatched = [n for n, f in CODE_NODES.items() if live.get(n, {}).get("parameters", {}).get("jsCode") != (HERE / f).read_text(encoding="utf-8")]
    export = {k: after.get(k) for k in ("id", "name", "description", "nodes", "connections", "settings") if k in after}
    (HERE / "new_page.workflow.json").write_text(json.dumps(export, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"workflow {wf_id}: {len(live)} nodes; code identical to the files: {not mismatched} {mismatched or ''}; "
          f"active: {after.get('active')}; export saved: new_page.workflow.json")
    return 0 if not mismatched else 1


if __name__ == "__main__":
    raise SystemExit(main())
