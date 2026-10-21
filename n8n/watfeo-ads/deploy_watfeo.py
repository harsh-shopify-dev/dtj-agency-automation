"""Deploy "WATFEO Ads: New Ad" to DTJ's n8n: a dedicated ad factory for ONE product, the book "We Are There For Each Other".

    python n8n/watfeo-ads/deploy_watfeo.py --dry-run     print the generated workflow code, change nothing
    python n8n/watfeo-ads/deploy_watfeo.py               create the data table and the workflow (or refresh the code nodes)

New WATFEO ad (form, n8n login) ─┐
From Another Workflow (later: the Telegram bot) ┴> Take the WATFEO Ad Request -> Save WATFEO Ad (dtj_watfeo_ads) -> Accepted?
    yes -> Load Earlier Ads (every row: the angles the team already used) -> Request for Claude Code: WATFEO Ad
        -> Wait for Claude Code: WATFEO Ad (3 days) -> Claude Code Reply: WATFEO Ad -> Record WATFEO Ad
                                                                                  -> Tell the Requester -> Send Result
    no  -> (stop: the row keeps the reason in ad_status)
The Claude Code session uses the skill watfeo-ugc-ads (.claude/skills/watfeo-ugc-ads). The code nodes are the .js files next to this
script (run in Node by test_watfeo_nodes.py), sent byte for byte; afterwards the live workflow is read back, compared and exported to
new_ad.workflow.json. Created UNPUBLISHED (publishing gives the form its live link: a separate yes). Undo: n8n keeps every version.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "store-factory"))
from n8n_mcp import PROJECT, call  # noqa: E402

NAME = "WATFEO Ads: New Ad"
TABLE = "dtj_watfeo_ads"
CREDENTIAL = "DTJ Page Bot"   # the Telegram API credential the store factory already uses
CODE_NODES = {"Take the WATFEO Ad Request": "take_watfeo_request.js", "Request for Claude Code: WATFEO Ad": "request_watfeo.js",
              "Claude Code Reply: WATFEO Ad": "reply_watfeo.js", "Tell the Requester": "tell_watfeo_requester.js"}
COLUMNS = json.loads((HERE / "tables.json").read_text(encoding="utf-8"))[TABLE]["columns"]
SAVE_COLS = [c for c in COLUMNS if c["name"] in ("submitted_at", "status", "kind", "language", "angle_asked", "count", "reference",
                                                  "notes", "requested_by", "telegram_chat_id", "raw_json", "ad_status")]
RECORD_COLS = [c for c in COLUMNS if c["name"] in ("ad_status", "final_path", "angle_used", "ad_note", "ad_updated_at")]
DESCRIPTION = ("WATFEO ad factory: UGC ads for the book 'We Are There For Each Other' only. A form -> a job -> Claude Code with the "
               "skill watfeo-ugc-ads makes scripts, prompts or a finished reel -> the result and the angle used are recorded.")
STICKY = ("## WATFEO ads: one book, endless fresh ads\n"
          "Fill **New WATFEO ad**: the language, what you need (a full reel, scripts only, or scripts + prompts), how many, and an "
          "angle number if you want one (1-58 from the skill's angle bank). The job is saved in **dtj_watfeo_ads**, which is also the "
          "team's record of angles already used.\n\n"
          "The run pauses at **Wait for Claude Code: WATFEO Ad**. On a DTJ laptop the person on duty opens Claude Code in the "
          "dtj-agency-automation folder and says \"handle the WATFEO ad request\" (or listens for it). Claude uses the skill "
          "**watfeo-ugc-ads** and answers here. Nothing is posted.\n\n"
          "Source in git: `n8n/watfeo-ads/` and `.claude/skills/watfeo-ugc-ads/`.")
FIELDS = [
    ("kind", "What do you need?", "dropdown", True, ["Full reel", "Scripts only", "Prompts only"]),
    ("language", "Language", "dropdown", True, ["English", "Hindi", "Hinglish"]),
    ("count", "How many ads", "number", True, None),
    ("angle", "Angle number (optional, 1-58)", "number", False, None),
    ("reference", "Reference reel to copy (optional link)", "text", False, None),
    ("notes", "Notes", "textarea", False, None),
    ("requested_by", "Your name", "text", True, None),
]


def form_fields() -> list[dict]:
    out = []
    for name, label, ftype, req, opts in FIELDS:
        f = {"fieldName": name, "fieldLabel": label, "fieldType": ftype, "requiredField": req}
        if opts:
            f["fieldOptions"] = {"values": [{"option": o} for o in opts]}
        out.append(f)
    return out


def sdk_code(table_id: str) -> str:
    js = {name: json.dumps((HERE / f).read_text(encoding="utf-8")) for name, f in CODE_NODES.items()}
    rl = f"{{ __rl: true, mode: 'list', value: '{table_id}', cachedResultName: '{TABLE}' }}"

    def schema(cols):
        return json.dumps([{"id": c["name"], "displayName": c["name"], "required": False, "defaultMatch": False, "display": True,
                            "type": c["type"], "canBeUsedToMatch": True} for c in cols])
    save_values = json.dumps({c["name"]: f"={{{{ $json.row.{c['name']} }}}}" for c in SAVE_COLS})
    rec_values = {c["name"]: f"={{{{ $json.{c['name']} }}}}" for c in RECORD_COLS}
    rec_values["ad_updated_at"] = "={{ $now.toISO() }}"

    def code_node(var, name, pos):
        return (f"const {var} = node({{ type: 'n8n-nodes-base.code', version: 2, config: {{ name: {json.dumps(name)}, position: {pos}, "
                f"parameters: {{ mode: 'runOnceForAllItems', language: 'javaScript', jsCode: {js[name]} }} }} }});\n")
    inputs = ", ".join(f"{{ name: '{n}', type: 'string' }}" for n, *_ in FIELDS) + ", { name: 'chat_id', type: 'string' }"
    return (
        "import { workflow, node, trigger, sticky, ifElse, expr, newCredential } from '@n8n/workflow-sdk';\n\n"
        "const form = trigger({ type: 'n8n-nodes-base.formTrigger', version: 2.6, config: { name: 'New WATFEO Ad', position: [0, 0], "
        "parameters: { authentication: 'n8nUserAuth', formTitle: 'New WATFEO ad', "
        "formDescription: 'UGC ads for We Are There For Each Other by Sagar Chudesara. Claude makes them while someone is on duty on a DTJ laptop; nothing is posted.', "
        f"formFields: {{ values: {json.dumps(form_fields())} }}, responseMode: 'onReceived', "
        "options: { appendAttribution: false, path: 'dtj-watfeo-ad', respondWithOptions: { values: { respondWith: 'text', "
        "formSubmittedText: 'Saved. Claude makes it while someone is on duty; the result is recorded in dtj_watfeo_ads.' } } } } } });\n"
        "const fromWorkflow = trigger({ type: 'n8n-nodes-base.executeWorkflowTrigger', version: 1.2, config: { name: 'From Another Workflow', "
        f"position: [0, 240], parameters: {{ inputSource: 'workflowInputs', workflowInputs: {{ values: [{inputs}] }} }} }} }});\n"
        + code_node("take", "Take the WATFEO Ad Request", "[240, 120]")
        + "const save = node({ type: 'n8n-nodes-base.dataTable', version: 1.1, config: { name: 'Save WATFEO Ad', position: [480, 120], "
          f"parameters: {{ resource: 'row', operation: 'insert', dataTableId: {rl}, "
          f"columns: {{ mappingMode: 'defineBelow', value: {save_values}, matchingColumns: [], schema: {schema(SAVE_COLS)} }} }} }} }});\n"
        + "const accepted = ifElse({ version: 2.2, config: { name: 'Accepted?', position: [720, 120], parameters: { conditions: { "
          "options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' }, conditions: [{ leftValue: expr('{{ $json.status }}'), "
          "rightValue: 'new', operator: { type: 'string', operation: 'equals' } }], combinator: 'and' } } } });\n"
        + "const earlier = node({ type: 'n8n-nodes-base.dataTable', version: 1.1, config: { name: 'Load Earlier Ads', position: [960, 0], "
          f"executeOnce: true, parameters: {{ resource: 'row', operation: 'get', dataTableId: {rl}, matchType: 'allConditions', "
          "filters: { conditions: [{ keyName: 'submitted_at', condition: 'isNotEmpty' }] }, returnAll: true } } });\n"
        + code_node("request", "Request for Claude Code: WATFEO Ad", "[1200, 0]")
        + "const wait = node({ type: 'n8n-nodes-base.wait', version: 1.1, config: { name: 'Wait for Claude Code: WATFEO Ad', position: [1440, 0], "
          "parameters: { resume: 'webhook', httpMethod: 'POST', limitWaitTime: true, limitType: 'afterTimeInterval', resumeAmount: 3, "
          "resumeUnit: 'days', options: {} } } });\n"
        + code_node("reply", "Claude Code Reply: WATFEO Ad", "[1680, 0]")
        + "const record = node({ type: 'n8n-nodes-base.dataTable', version: 1.1, config: { name: 'Record WATFEO Ad', position: [1920, -120], "
          f"parameters: {{ resource: 'row', operation: 'update', dataTableId: {rl}, matchType: 'allConditions', "
          "filters: { conditions: [{ keyName: 'id', condition: 'eq', keyValue: '={{ $json.row_id }}' }] }, "
          f"columns: {{ mappingMode: 'defineBelow', value: {json.dumps(rec_values)}, matchingColumns: [], schema: {schema(RECORD_COLS)} }} }} }} }});\n"
        + code_node("tell", "Tell the Requester", "[1920, 120]")
        + "const send = node({ type: 'n8n-nodes-base.telegram', version: 1.2, config: { name: 'Send Result', position: [2160, 120], "
          "parameters: { resource: 'message', operation: 'sendMessage', chatId: expr('{{ $json.chat_id }}'), text: expr('{{ $json.text }}'), "
          "additionalFields: { appendAttribution: false, parse_mode: 'HTML', disable_web_page_preview: true } }, "
          f"credentials: {{ telegramApi: newCredential({json.dumps(CREDENTIAL)}) }} }} }});\n"
        + f"const about = sticky({json.dumps(STICKY)}, [form, fromWorkflow, take], {{ color: 6, position: [-40, -440], width: 780, height: 400 }});\n\n"
        "export default workflow('watfeo-ads-new-ad', " + json.dumps(NAME) + ")\n"
        "  .add(form).to(take)\n"
        "  .add(fromWorkflow).to(take)\n"
        "  .add(take).to(save).to(accepted.onTrue(earlier.to(request.to(wait.to(reply.to(record))))))\n"
        "  .add(reply).to(tell.to(send))\n"
        "  .add(about);\n"
    )


def ensure_table() -> str:
    found = [t for t in call("search_data_tables", {"query": TABLE}).get("data", []) if t.get("name") == TABLE]
    if found:
        live = {c["name"] for c in found[0].get("columns", [])}
        missing = [c for c in COLUMNS if live and c["name"] not in live]
        for c in missing:
            call("add_data_table_column", {"dataTableId": found[0]["id"], "projectId": PROJECT, "name": c["name"], "type": c["type"]})
        print(f"table {TABLE}: exists ({found[0]['id']}){'; added ' + str([c['name'] for c in missing]) if missing else ''}")
        return found[0]["id"]
    made = call("create_data_table", {"projectId": PROJECT, "name": TABLE, "columns": COLUMNS})
    tid = made.get("id") or (made.get("dataTable") or {}).get("id")
    if not tid:
        raise RuntimeError(f"create_data_table gave no id: {json.dumps(made)[:300]}")
    print(f"table {TABLE}: created ({tid})")
    return tid


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.dry_run:
        print(sdk_code("<dtj_watfeo_ads id>"))
        return 0
    try:
        table_id = ensure_table()
        code = sdk_code(table_id)
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
            made = call("create_workflow_from_code", {"code": code, "description": DESCRIPTION, "projectId": PROJECT,
                                                      "versionName": "WATFEO ad factory: form to Claude Code hand-off"})
            print("created:", json.dumps(made)[:600])
            wf_id = made.get("workflowId") or made.get("id")
        creds = [c for c in call("list_credentials", {}).get("data", []) if c.get("name") == CREDENTIAL and c.get("type") == "telegramApi"]
        if creds:
            call("update_workflow", {"workflowId": wf_id, "operations": [{"type": "setNodeCredential", "nodeName": "Send Result",
                 "credentialKey": "telegramApi", "credentialId": creds[0]["id"], "credentialName": CREDENTIAL}]})
        after = call("get_workflow_details", {"workflowId": wf_id})["workflow"]
    except (urllib.error.URLError, RuntimeError, OSError) as exc:
        print(f"not deployed: {exc}", file=sys.stderr)
        return 1
    live = {n["name"]: n for n in after["nodes"]}
    mismatched = [n for n, f in CODE_NODES.items() if live.get(n, {}).get("parameters", {}).get("jsCode") != (HERE / f).read_text(encoding="utf-8")]
    export = {k: after.get(k) for k in ("id", "name", "description", "nodes", "connections", "settings") if k in after}
    (HERE / "new_ad.workflow.json").write_text(json.dumps(export, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"workflow {wf_id}: {len(live)} nodes; code identical to the files: {not mismatched} {mismatched or ''}; "
          f"active: {after.get('active')}; export saved: new_ad.workflow.json")
    return 0 if not mismatched else 1


if __name__ == "__main__":
    raise SystemExit(main())
