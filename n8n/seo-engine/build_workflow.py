"""Write weekly_report.workflow.json, the n8n export of "SEO Engine: Weekly Report", from the code files in this folder.

    python n8n/seo-engine/build_workflow.py           write the export
    python n8n/seo-engine/build_workflow.py --check   exit 1 if the export differs from what the code files make (the tests run this)

Two lanes in one workflow:
  Report from GitHub (webhook, JWT signed with "DTJ SEO Report Key") -> Check the Report -> Load Bot Users -> Load Batches
      -> Plan the Report -> Log the Report (dtj_action_log)
                         -> Save or Dead Letter
                              save        -> Save the Batch (dtj_seo_batches) -> Report Messages -> Message Kind
                                               file -> Send the Report File | ask -> Ask Yes or No | text -> Send
                              dead_letter -> Keep in Dead Letter (dtj_dead_letter) -> Dead Letter Alert -> Send
  Answer from the Bot (called by the bot's "SEO Answer" when someone taps Yes / No) -> Find the Batch -> Load the Team
      -> Decide the Answer -> Record or Reply
                              record  -> Save the Answer (only while the row still says "waiting") -> Apply On?
                                           true  -> Start SEO Apply (GitHub: run "SEO apply fixes") -> Answer Messages
                                           false -> Answer Messages
                                         Answer Messages -> Send, and -> Log the Answer (dtj_action_log, once)
                              confirm -> Ask Who Approves (a teammate confirms Harsh can't be reached)
                              reply   -> Send
No token or key is in this file: credentials are referenced by name and attached in n8n (deploy_seo_engine.py).
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPORT = HERE / "weekly_report.workflow.json"
NAME = "SEO Engine: Weekly Report"
DESCRIPTION = ("Monday SEO report from GitHub (signed) to the DTJ bot's admins with Yes / No for the fixes batch; records one named answer "
               "per batch. Shadow: a yes is recorded, nothing applied, until Harsh turns the apply on.")
WEBHOOK_PATH = "dtj-seo-weekly"
TELEGRAM = {"telegramApi": {"name": "DTJ Page Bot"}}
GITHUB = {"httpBearerAuth": {"name": "DTJ GitHub Actions"}}
JWT = {"jwtAuth": {"name": "DTJ SEO Report Key"}}
BOT_USERS_ID = "xJ9O19tBBmCJc1Hc"  # dtj_bot_users on DTJ's n8n (deploy re-points every table by name on another server)
APPLY_URL = "https://api.github.com/repos/harsh-shopify-dev/dtj-agency-automation/actions/workflows/seo-apply.yml/dispatches"
SEND_FIELDS = {"appendAttribution": False, "parse_mode": "HTML", "disable_web_page_preview": True}
CODE = {"Check the Report": "check_report.js", "Plan the Report": "plan_report.js", "Report Messages": "report_messages.js",
        "Dead Letter Alert": "dead_letter_alert.js", "Decide the Answer": "answer_plan.js", "Answer Messages": "answer_messages.js"}
INPUTS = [("row_id", "number"), ("answer", "string"), ("by", "string"), ("user_id", "string"), ("chat_id", "string")]


def tables() -> dict:
    return json.loads((HERE / "tables.json").read_text(encoding="utf-8"))


def table(name: str) -> dict:
    return {"__rl": True, "mode": "list", "value": BOT_USERS_ID if name == "dtj_bot_users" else "", "cachedResultName": name}


def mapping(table_name: str, source: str, only: list[str] | None = None) -> dict:
    cols = [c for c in tables()[table_name]["columns"] if only is None or c["name"] in only]
    return {"mappingMode": "defineBelow", "value": {c["name"]: f"={{{{ $json.{source}{c['name']} }}}}" for c in cols},
            "matchingColumns": [], "schema": [{"id": c["name"], "displayName": c["name"], "required": False, "defaultMatch": False,
                                               "display": True, "type": c["type"], "canBeUsedToMatch": True} for c in cols],
            "attemptToConvertTypes": False, "convertFieldsToString": False}


def rule(value: str, field: str = "$json.action") -> dict:
    return {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                           "conditions": [{"leftValue": f"={{{{ {field} }}}}", "rightValue": value,
                                           "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"},
            "renameOutput": True, "outputKey": value}


def two_buttons() -> dict:
    return {"rows": [{"row": {"buttons": [{"text": "={{ $json.yes_text }}", "additionalFields": {"callback_data": "={{ $json.yes_data }}"}},
                                          {"text": "={{ $json.no_text }}", "additionalFields": {"callback_data": "={{ $json.no_data }}"}}]}}]}


def node(name: str, ntype: str, version: float, pos: list[int], params: dict, **extra) -> dict:
    out = {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"dtj/{NAME}/{name}")), "name": name, "type": ntype, "typeVersion": version,
           "position": pos, "parameters": params}
    out.update(extra)
    return out


def code_node(name: str, pos: list[int]) -> dict:
    return node(name, "n8n-nodes-base.code", 2, pos, {"mode": "runOnceForAllItems", "language": "javaScript",
                                                      "jsCode": (HERE / CODE[name]).read_text(encoding="utf-8")})


def read_rows(name: str, tname: str, key: str, pos: list[int]) -> dict:
    return node(name, "n8n-nodes-base.dataTable", 1.1, pos, {
        "resource": "row", "operation": "get", "dataTableId": table(tname), "matchType": "allConditions",
        "filters": {"conditions": [{"keyName": key, "condition": "isNotEmpty"}]}, "returnAll": True},
        executeOnce=True, alwaysOutputData=True)


def insert(name: str, tname: str, source: str, pos: list[int], **extra) -> dict:
    return node(name, "n8n-nodes-base.dataTable", 1.1, pos, {"resource": "row", "operation": "insert", "dataTableId": table(tname),
                                                           "columns": mapping(tname, source), "options": {}}, **extra)


def telegram(name: str, pos: list[int], buttons: bool = False) -> dict:
    p = {"resource": "message", "operation": "sendMessage", "chatId": "={{ $json.chat_id }}", "text": "={{ $json.text }}"}
    if buttons:
        p.update(replyMarkup="inlineKeyboard", inlineKeyboard=two_buttons())
    p["additionalFields"] = dict(SEND_FIELDS)
    return node(name, "n8n-nodes-base.telegram", 1.2, pos, p, onError="continueRegularOutput",
                webhookId=str(uuid.uuid5(uuid.NAMESPACE_URL, f"dtj/{NAME}/{name}/hook")), credentials=TELEGRAM)


def sticky(name: str, pos: list[int], text: str, w: int, h: int) -> dict:
    return node(name, "n8n-nodes-base.stickyNote", 1, pos, {"content": text, "height": h, "width": w, "color": 5})


def build() -> dict:
    nodes = [
        sticky("About the Report", [-40, -420], "## Monday SEO report (from GitHub)\n"
               "`.github/workflows/seo-weekly.yml` sends the report here, signed (JWT, credential **DTJ SEO Report Key**). "
               "Unsigned requests are refused at the door; a signed one that fails its checks goes to **dtj_dead_letter** and the "
               "admins are told. Otherwise the admins in **dtj_bot_users** get the report file and the fixes, with Yes / No when "
               "there is something to apply and the check read the whole site. One row per batch in **dtj_seo_batches**.", 1000, 260),
        node("Report from GitHub", "n8n-nodes-base.webhook", 2, [0, 0],
             {"httpMethod": "POST", "path": WEBHOOK_PATH, "authentication": "jwtAuth", "responseMode": "onReceived", "options": {}},
             webhookId=str(uuid.uuid5(uuid.NAMESPACE_URL, f"dtj/{NAME}/webhook")), credentials=JWT),
        code_node("Check the Report", [240, 0]),
        read_rows("Load Bot Users", "dtj_bot_users", "telegram_user_id", [480, 0]),
        read_rows("Load Batches", "dtj_seo_batches", "batch_id", [720, 0]),
        code_node("Plan the Report", [960, 0]),
        insert("Log the Report", "dtj_action_log", "log.", [1200, -200], onError="continueRegularOutput"),
        node("Save or Dead Letter", "n8n-nodes-base.switch", 3.2, [1200, 0],
             {"rules": {"values": [rule("save"), rule("dead_letter")]}, "options": {}}),
        insert("Save the Batch", "dtj_seo_batches", "row.", [1440, -60]),
        code_node("Report Messages", [1680, -60]),
        node("Message Kind", "n8n-nodes-base.switch", 3.2, [1920, -60],
             {"rules": {"values": [rule("file", "$json.kind"), rule("ask", "$json.kind"), rule("text", "$json.kind")]}, "options": {}}),
        node("Send the Report File", "n8n-nodes-base.telegram", 1.2, [2160, -220],
             {"resource": "message", "operation": "sendDocument", "chatId": "={{ $json.chat_id }}", "binaryData": True,
              "binaryPropertyName": "data", "additionalFields": {"caption": "={{ $json.caption }}"}},
             onError="continueRegularOutput", webhookId=str(uuid.uuid5(uuid.NAMESPACE_URL, f"dtj/{NAME}/file/hook")), credentials=TELEGRAM),
        telegram("Ask Yes or No", [2160, -60], buttons=True),
        telegram("Send", [2160, 160]),
        insert("Keep in Dead Letter", "dtj_dead_letter", "dead.", [1440, 160]),
        code_node("Dead Letter Alert", [1680, 160]),

        sticky("About the Answers", [-40, 420], "## The Yes / No taps (from the bot)\n"
               "The bot's **Who Is It** hands every `seo:` button here. One named answer per batch: Harsh's, or a teammate's when "
               "Harsh can't be reached (they confirm that first; recorded as \"<name> (Harsh not reachable)\"). **Shadow** while "
               "`APPLY_ON` is false in *Decide the Answer* (and *Report Messages*): the answer is recorded and nothing is applied. "
               "On: a yes starts GitHub's **SEO apply fixes** with the run, the name and the batch id.", 1000, 240),
        node("Answer from the Bot", "n8n-nodes-base.executeWorkflowTrigger", 1.1, [0, 700],
             {"inputSource": "workflowInputs", "workflowInputs": {"values": [{"name": n, "type": t} for n, t in INPUTS]}}),
        read_rows("Find the Batch", "dtj_seo_batches", "batch_id", [240, 700]),
        read_rows("Load the Team", "dtj_bot_users", "telegram_user_id", [480, 700]),
        code_node("Decide the Answer", [720, 700]),
        node("Record or Reply", "n8n-nodes-base.switch", 3.2, [960, 700],
             {"rules": {"values": [rule("record"), rule("confirm"), rule("reply")]}, "options": {}}),
        node("Save the Answer", "n8n-nodes-base.dataTable", 1.1, [1200, 600], {
            "operation": "update", "dataTableId": table("dtj_seo_batches"), "matchType": "allConditions",
            "filters": {"conditions": [{"keyName": "id", "condition": "eq", "keyValue": "={{ $json.row_id }}"},
                                       {"keyName": "status", "condition": "eq", "keyValue": "waiting"}]},
            "columns": mapping("dtj_seo_batches", "", ["status", "answered_by", "approved_by", "answered_at", "apply_status"]),
            "options": {}}, alwaysOutputData=True),
        node("Apply On?", "n8n-nodes-base.if", 2.2, [1440, 600], {"conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
            "conditions": [{"leftValue": "={{ $('Decide the Answer').first().json.dispatch === true && !!$json.id }}", "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True}}], "combinator": "and"}, "options": {}}),
        node("Start SEO Apply", "n8n-nodes-base.httpRequest", 4.2, [1680, 520], {
            "method": "POST", "url": APPLY_URL, "authentication": "genericCredentialType", "genericAuthType": "httpBearerAuth",
            "sendHeaders": True, "headerParameters": {"parameters": [{"name": "Accept", "value": "application/vnd.github+json"},
                                                                     {"name": "X-GitHub-Api-Version", "value": "2022-11-28"},
                                                                     {"name": "User-Agent", "value": "dtj-n8n-seo/1"}]},
            "sendBody": True, "contentType": "json", "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify($('Decide the Answer').first().json.body) }}",
            "options": {"response": {"response": {"fullResponse": True, "neverError": True}}, "timeout": 30000}},
            onError="continueRegularOutput", credentials=GITHUB),
        code_node("Answer Messages", [1920, 600]),
        insert("Log the Answer", "dtj_action_log", "log.", [2160, 440], executeOnce=True, onError="continueRegularOutput"),
        telegram("Ask Who Approves", [1200, 820], buttons=True),
    ]
    wires = [("Report from GitHub", 0, "Check the Report"), ("Check the Report", 0, "Load Bot Users"), ("Load Bot Users", 0, "Load Batches"),
             ("Load Batches", 0, "Plan the Report"), ("Plan the Report", 0, "Log the Report"), ("Plan the Report", 0, "Save or Dead Letter"),
             ("Save or Dead Letter", 0, "Save the Batch"), ("Save or Dead Letter", 1, "Keep in Dead Letter"),
             ("Save the Batch", 0, "Report Messages"), ("Report Messages", 0, "Message Kind"),
             ("Message Kind", 0, "Send the Report File"), ("Message Kind", 1, "Ask Yes or No"), ("Message Kind", 2, "Send"),
             ("Keep in Dead Letter", 0, "Dead Letter Alert"), ("Dead Letter Alert", 0, "Send"),
             ("Answer from the Bot", 0, "Find the Batch"), ("Find the Batch", 0, "Load the Team"), ("Load the Team", 0, "Decide the Answer"),
             ("Decide the Answer", 0, "Record or Reply"), ("Record or Reply", 0, "Save the Answer"),
             ("Record or Reply", 1, "Ask Who Approves"), ("Record or Reply", 2, "Send"),
             ("Save the Answer", 0, "Apply On?"), ("Apply On?", 0, "Start SEO Apply"), ("Apply On?", 1, "Answer Messages"),
             ("Start SEO Apply", 0, "Answer Messages"), ("Answer Messages", 0, "Send"), ("Answer Messages", 0, "Log the Answer")]
    conns: dict = {}
    for src, idx, dst in wires:
        outs = conns.setdefault(src, {"main": []})["main"]
        while len(outs) <= idx:
            outs.append([])
        outs[idx].append({"node": dst, "type": "main", "index": 0})
    return {"name": NAME, "description": DESCRIPTION, "nodes": nodes, "connections": conns,
            "settings": {"executionOrder": "v1", "availableInMCP": True}}


def text() -> str:
    return json.dumps(build(), indent=1, ensure_ascii=False) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if a.check:
        same = EXPORT.exists() and EXPORT.read_text(encoding="utf-8") == text()
        print("export matches the code files" if same else "export differs: run python n8n/seo-engine/build_workflow.py")
        return 0 if same else 1
    EXPORT.write_text(text(), encoding="utf-8")
    print(f"wrote {EXPORT.name}: {len(build()['nodes'])} nodes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
