"""Deploy "Reel Factory: New Reel" to DTJ's n8n: a form (product, pictures, winning reels, language, facts) -> a saved job ->
a Claude Code hand-off on the reel VPS -> the result recorded on the job row (and sent back on Telegram when asked from there).

    python n8n/reel-factory/deploy_reel.py --dry-run     print the generated workflow code, change nothing
    python n8n/reel-factory/deploy_reel.py               create the data table and the workflow (or refresh the code nodes)

New UGC Reel (form, n8n login) ─┐
From Another Workflow (later: the Telegram bot's /reel) ┴> Take the Reel Request -> Save Reel Job (dtj_reel_jobs) -> Accepted?
    yes -> Request for Claude Code: Reel -> Wait for Claude Code: Reel (3 days) -> Claude Code Reply: Reel -> Record Reel
                                                                                                         -> Tell the Requester -> Send Result
    no  -> (stop: the row keeps the reason in reel_status)
The code nodes are the .js files next to this script (run in Node by test_reel_nodes.py), sent byte for byte; afterwards the live
workflow is read back, compared and exported to new_reel.workflow.json. The workflow is created UNPUBLISHED: the form's test URL
works from the editor; publishing it (the form's production URL) is a separate yes. Undo: n8n keeps every version.
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

NAME = "Reel Factory: New Reel"
TABLE = "dtj_reel_jobs"
CREDENTIAL = "DTJ Reel Bot"   # the reel factory's own Telegram bot (Harsh, 25 Oct 2026: "we will create a new telegram bot")
CODE_NODES = {"Take the Reel Request": "take_reel_request.js", "Request for Claude Code: Reel": "request_reel.js",
              "Claude Code Reply: Reel": "reply_reel.js", "Tell the Requester": "tell_reel_requester.js"}
COLUMNS = json.loads((HERE / "tables.json").read_text(encoding="utf-8"))[TABLE]["columns"]
SAVE_COLS = [c for c in COLUMNS if c["name"] in ("submitted_at", "status", "reel_type", "product_name", "audience", "brand_name", "product_images",
                                                  "reference_reels", "language", "music", "facts", "notes", "requested_by",
                                                  "telegram_chat_id", "raw_json", "reel_status")]
RECORD_COLS = [c for c in COLUMNS if c["name"] in ("reel_status", "final_path", "job_folder", "duration_s", "lufs", "generations",
                                                    "credits_used", "reel_note", "reel_updated_at")]
DESCRIPTION = ("Reel factory: a product and winning reference reels -> Claude Code on the reel VPS makes a finished 9:16 UGC ad "
               "(ChatGPT + Google Flow in the browser, checks, LaMa, edit, captions). Records the result on dtj_reel_jobs.")
STICKY = ("## Reel factory: new UGC reel\n"
          "Fill the form **New UGC Reel** (links to the product pictures and to 1-5 winning reels, the language, the approved facts). "
          "The job is saved in **dtj_reel_jobs**, then the run pauses at **Wait for Claude Code: Reel**.\n\n"
          "On the reel VPS, the person on duty runs Claude Code in the dtj-agency-automation folder and says \"handle the Claude Code "
          "trigger in n8n\" (or \"listen for reel requests\"). Claude makes the reel in the logged-in browser (ChatGPT, Google Flow), "
          "checks every take, removes the Flow sparkle, edits, captions, and posts the result here. Nothing is posted to Meta.\n\n"
          "Source in git: `n8n/reel-factory/` and `services/reel-factory/`.")
# a plain-English note on every node (shown under it on the canvas; Harsh, 25 Oct 2026: "add notes for each node what they are doing")
NOTES = {
    "New UGC Reel": "The n8n form (needs an n8n login) to ask for a reel by hand: remake or UGC, product, pictures, reference reels, audience, language, facts.",
    "From Another Workflow": "Where the reel bot's /remake and /reel arrive (Reel Factory: Telegram Bot): the same fields plus the person's Telegram chat.",
    "Take the Reel Request": "Checks the request and makes the job row: a remake needs exactly one reference reel; a UGC reel needs a language and approved facts; every link must be https, a VPS path or a photo sent to the bot. A refusal keeps its reason.",
    "Save Reel Job": "Saves the job in dtj_reel_jobs. Its row id is the job id in Telegram (r<id>).",
    "Accepted?": "Only a complete request goes on; a refused one stops here, with the reason on its row.",
    "Request for Claude Code: Reel": "Writes Claude's full task list for this reel type (remake or UGC): the VPS folders and tools, the watcher's check before each of the 3 Telegram approvals (plan, pictures, final reel), and how to answer n8n. The VPS worker reads it.",
    "Wait for Claude Code: Reel": "Pauses (up to 3 days). The VPS worker asks 'tap Start if you are watching' in the reel bot; after the tap Claude makes the reel and answers this step with reply.py.",
    "Claude Code Reply: Reel": "Reads Claude's answer (reel ready / needs a look / could not make, the file, length, loudness, credits used) and refuses half answers.",
    "Record Reel": "Writes the result on the job's row in dtj_reel_jobs.",
    "Tell the Requester": "For a reel asked in Telegram: one short message with the result and where the file is. Nothing is posted anywhere.",
    "Send Result": "Sends that message to the requester's chat (through the reel bot once its 'DTJ Reel Bot' credential is attached)."
}
FIELDS = [
    ("reel_type", "Reel type", "dropdown", True, ""),
    ("product_name", "Product name", "text", True, "e.g. Senso Instant Detox Green Tea Kahwa"),
    ("audience", "Audience (who it is for)", "text", False, "e.g. Gujarati home cooks 30-50, Gen Z urban India"),
    ("brand_name", "Brand name", "text", False, ""),
    ("product_images", "Product pictures (links, one per line)", "textarea", True, "https://... (front of the pack, label readable)"),
    ("reference_reels", "Winning reference reels (links, one per line)", "textarea", True, "https://... (mp4 or a Drive link anyone can open)"),
    ("language", "Language", "dropdown", False, ""),
    ("music", "Background music (licensed; link)", "text", False, "leave empty for no music"),
    ("facts", "Approved facts (only these may be said)", "textarea", False, "UGC: pack text, the product page's claims, offers the client approved"),
    ("notes", "Notes for the reel", "textarea", False, ""),
    ("requested_by", "Your name", "text", True, ""),
]


def form_fields() -> list[dict]:
    out = []
    for name, label, ftype, req, ph in FIELDS:
        f = {"fieldName": name, "fieldLabel": label, "fieldType": ftype, "requiredField": req}
        if ph:
            f["placeholder"] = ph
        if ftype == "dropdown":
            opts = ("Remake a reference edit", "UGC script reel") if name == "reel_type" else ("English", "Hindi", "Hinglish", "Gujarati")
            f["fieldOptions"] = {"values": [{"option": o} for o in opts]}
        out.append(f)
    return out


def _schema(cols):
    return [{"id": c["name"], "displayName": c["name"], "required": False, "defaultMatch": False, "display": True,
             "type": c["type"], "canBeUsedToMatch": True} for c in cols]


def save_columns() -> dict:
    return {"mappingMode": "defineBelow", "value": {c["name"]: f"={{{{ $json.row.{c['name']} }}}}" for c in SAVE_COLS},
            "matchingColumns": [], "schema": _schema(SAVE_COLS)}


def sdk_code(table_id: str) -> str:
    js = {name: json.dumps((HERE / f).read_text(encoding="utf-8")) for name, f in CODE_NODES.items()}
    rl = f"{{ __rl: true, mode: 'list', value: '{table_id}', cachedResultName: '{TABLE}' }}"

    def schema(cols):
        return json.dumps([{"id": c["name"], "displayName": c["name"], "required": False, "defaultMatch": False, "display": True,
                            "type": c["type"], "canBeUsedToMatch": True} for c in cols])
    save_values = json.dumps({c["name"]: f"={{{{ $json.row.{c['name']} }}}}" for c in SAVE_COLS})
    rec_values = {c["name"]: f"={{{{ $json.{c['name']} }}}}" for c in RECORD_COLS}
    rec_values["reel_updated_at"] = "={{ $now.toISO() }}"

    def code_node(var, name, pos):
        return (f"const {var} = node({{ type: 'n8n-nodes-base.code', version: 2, config: {{ name: {json.dumps(name)}, position: {pos}, notes: {json.dumps(NOTES[name])}, notesInFlow: true, "
                f"parameters: {{ mode: 'runOnceForAllItems', language: 'javaScript', jsCode: {js[name]} }} }} }});\n")
    inputs = ", ".join(f"{{ name: '{n}', type: 'string' }}" for n, *_ in FIELDS) + ", { name: 'chat_id', type: 'string' }"
    return (
        "import { workflow, node, trigger, sticky, ifElse, expr, newCredential } from '@n8n/workflow-sdk';\n\n"
        "const form = trigger({ type: 'n8n-nodes-base.formTrigger', version: 2.6, config: { name: 'New UGC Reel', position: [0, 0], "
        "parameters: { authentication: 'n8nUserAuth', formTitle: 'New UGC reel', "
        "formDescription: 'One product, 1-5 winning reels to copy, the facts the reel may say. Claude makes the reel on the reel VPS while someone is on duty; nothing is posted.', "
        f"formFields: {{ values: {json.dumps(form_fields())} }}, responseMode: 'onReceived', "
        "options: { appendAttribution: false, path: 'dtj-new-reel', respondWithOptions: { values: { respondWith: 'text', "
        "formSubmittedText: 'Saved. The reel is made while someone is on duty on the reel VPS; the result is recorded in dtj_reel_jobs.' } } } } } });\n"
        "const fromWorkflow = trigger({ type: 'n8n-nodes-base.executeWorkflowTrigger', version: 1.2, config: { name: 'From Another Workflow', "
        f"position: [0, 240], parameters: {{ inputSource: 'workflowInputs', workflowInputs: {{ values: [{inputs}] }} }} }} }});\n"
        + code_node("take", "Take the Reel Request", "[240, 120]")
        + "const save = node({ type: 'n8n-nodes-base.dataTable', version: 1.1, config: { name: 'Save Reel Job', position: [480, 120], "
          f"parameters: {{ resource: 'row', operation: 'insert', dataTableId: {rl}, "
          f"columns: {{ mappingMode: 'defineBelow', value: {save_values}, matchingColumns: [], schema: {schema(SAVE_COLS)} }} }} }} }});\n"
        + "const accepted = ifElse({ version: 2.2, config: { name: 'Accepted?', position: [720, 120], parameters: { conditions: { "
          "options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' }, conditions: [{ leftValue: expr('{{ $json.status }}'), "
          "rightValue: 'new', operator: { type: 'string', operation: 'equals' } }], combinator: 'and' } } } });\n"
        + code_node("request", "Request for Claude Code: Reel", "[960, 0]")
        + "const wait = node({ type: 'n8n-nodes-base.wait', version: 1.1, config: { name: 'Wait for Claude Code: Reel', position: [1200, 0], "
          "parameters: { resume: 'webhook', httpMethod: 'POST', limitWaitTime: true, limitType: 'afterTimeInterval', resumeAmount: 3, "
          "resumeUnit: 'days', options: {} } } });\n"
        + code_node("reply", "Claude Code Reply: Reel", "[1440, 0]")
        + "const record = node({ type: 'n8n-nodes-base.dataTable', version: 1.1, config: { name: 'Record Reel', position: [1680, -120], "
          f"parameters: {{ resource: 'row', operation: 'update', dataTableId: {rl}, matchType: 'allConditions', "
          "filters: { conditions: [{ keyName: 'id', condition: 'eq', keyValue: '={{ $json.row_id }}' }] }, "
          f"columns: {{ mappingMode: 'defineBelow', value: {json.dumps(rec_values)}, matchingColumns: [], schema: {schema(RECORD_COLS)} }} }} }} }});\n"
        + code_node("tell", "Tell the Requester", "[1680, 120]")
        + "const send = node({ type: 'n8n-nodes-base.telegram', version: 1.2, config: { name: 'Send Result', position: [1920, 120], "
          "parameters: { resource: 'message', operation: 'sendMessage', chatId: expr('{{ $json.chat_id }}'), text: expr('{{ $json.text }}'), "
          "additionalFields: { appendAttribution: false, parse_mode: 'HTML', disable_web_page_preview: true } }, "
          f"credentials: {{ telegramApi: newCredential({json.dumps(CREDENTIAL)}) }} }} }});\n"
        + f"const about = sticky({json.dumps(STICKY)}, [form, fromWorkflow, take], {{ color: 5, position: [-40, -420], width: 760, height: 380 }});\n\n"
        "export default workflow('reel-factory-new-reel', " + json.dumps(NAME) + ")\n"
        "  .add(form).to(take)\n"
        "  .add(fromWorkflow).to(take)\n"
        "  .add(take).to(save).to(accepted.onTrue(request.to(wait.to(reply.to(record)))))\n"
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
        print(sdk_code("<dtj_reel_jobs id>"))
        return 0
    try:
        table_id = ensure_table()
        code = sdk_code(table_id)
        found = [w for w in call("search_workflows", {"query": NAME}).get("data", []) if w.get("name") == NAME]
        if found:
            wf_id = found[0]["id"]
            ops = [{"type": "updateNodeParameters", "nodeName": n, "parameters": {"jsCode": (HERE / f).read_text(encoding="utf-8")}}
                   for n, f in CODE_NODES.items()]
            # the fields that came later (25 Oct 2026: reel type, audience, Gujarati): the form, the bot's inputs, what is saved
            ops += [{"type": "setNodeParameter", "nodeName": "New UGC Reel", "path": "/formFields/values", "value": form_fields()},
                    {"type": "setNodeParameter", "nodeName": "From Another Workflow", "path": "/workflowInputs/values",
                     "value": [{"name": n, "type": "string"} for n, *_ in FIELDS] + [{"name": "chat_id", "type": "string"}]},
                    {"type": "setNodeParameter", "nodeName": "Save Reel Job", "path": "/columns", "value": save_columns()}]
            print("exists: refreshing its code nodes", call("update_workflow", {"workflowId": wf_id, "operations": ops}))
        else:
            check = call("validate_workflow", {"code": code})
            print("validate:", json.dumps(check)[:800])
            if check.get("valid") is False or check.get("errors"):
                return 1
            made = call("create_workflow_from_code", {"code": code, "description": DESCRIPTION, "projectId": PROJECT,
                                                      "versionName": "New UGC reel: form to Claude Code hand-off"})
            print("created:", json.dumps(made)[:600])
            wf_id = made.get("workflowId") or made.get("id")
        creds = [c for c in call("list_credentials", {}).get("data", []) if c.get("name") == CREDENTIAL and c.get("type") == "telegramApi"]
        if creds:
            call("update_workflow", {"workflowId": wf_id, "operations": [{"type": "setNodeCredential", "nodeName": "Send Result",
                 "credentialKey": "telegramApi", "credentialId": creds[0]["id"], "credentialName": CREDENTIAL}]})
        else:
            print(f"no Telegram credential named '{CREDENTIAL}': Send Result stays without one (only Telegram jobs need it)")
        after = call("get_workflow_details", {"workflowId": wf_id})["workflow"]
    except (urllib.error.URLError, RuntimeError, OSError) as exc:
        print(f"not deployed: {exc}", file=sys.stderr)
        return 1
    live = {n["name"]: n for n in after["nodes"]}
    mismatched = [n for n, f in CODE_NODES.items() if live.get(n, {}).get("parameters", {}).get("jsCode") != (HERE / f).read_text(encoding="utf-8")]
    export = {k: after.get(k) for k in ("id", "name", "description", "nodes", "connections", "settings") if k in after}
    (HERE / "new_reel.workflow.json").write_text(json.dumps(export, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"workflow {wf_id}: {len(live)} nodes; code identical to the files: {not mismatched} {mismatched or ''}; "
          f"active: {after.get('active')}; export saved: new_reel.workflow.json")
    return 0 if not mismatched else 1


if __name__ == "__main__":
    raise SystemExit(main())
