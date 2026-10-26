"""Deploy "Reel Factory: Telegram Bot", the reel factory's own Telegram bot (Harsh, 25 Oct 2026: "we will create a new telegram
bot for this automation"; "build the workflow in n8n as discussed before and add notes for each node what they are doing").

    python n8n/reel-factory/deploy_reel_bot.py --dry-run     print the generated workflow code, change nothing
    python n8n/reel-factory/deploy_reel_bot.py               create it (UNPUBLISHED) or refresh its code nodes and notes
    python n8n/reel-factory/deploy_reel_bot.py --publish     publish it (needs the "DTJ Reel Bot" Telegram credential in n8n)

Telegram Message -> Read the Message -> Load Bot Users -> Load Open Questions -> Load Recent Photos -> Load Today's Reels
    -> Load Settings -> Who Is It -> What to Do
        answer -> Save the Answer (dtj_bot_answers)        -> Say What Happened -> Send
        photo  -> Save the Photo (dtj_bot_answers)         -> Say What Happened -> Send
        reel   -> Start New Reel (Reel Factory: New Reel)  -> Say What Happened -> Send
        limit  -> Save the Limit (dtj_reel_settings)       -> Say What Happened -> Send
        refs   -> Start Find References                    -> Say What Happened -> Send
        else   -> Send (help, status, refusals)
Read the Message -> Is It a Button? -> Answer the Button (stops the tapped button's spinner)
Every node carries a note (shown under it on the canvas) saying what it does. The code nodes are the .js files next to this
script (tested by test_reel_bot_nodes.py), sent byte for byte, read back and compared, and the live workflow is exported to
reel_bot.workflow.json. The bot's token is never in code: Harsh creates the bot in BotFather and puts its token in the n8n
credential "DTJ Reel Bot" himself.
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

NAME = "Reel Factory: Telegram Bot"
CREDENTIAL = "DTJ Reel Bot"
NEW_REEL, FIND_REFS = "Reel Factory: New Reel", "Reel Factory: Find References"
TABLES = ("dtj_bot_users", "dtj_bot_answers", "dtj_reel_jobs", "dtj_reel_settings")
CODE_NODES = {"Read the Message": "reel_bot_read.js", "Who Is It": "reel_bot_route.js", "Say What Happened": "reel_bot_reply.js"}
REEL_INPUTS = ["reel_type", "product_name", "audience", "brand_name", "product_images", "reference_reels", "language", "music",
               "facts", "notes", "requested_by", "chat_id"]
REFS_INPUTS = ["query", "sources", "limit", "requested_by", "chat_id", "mode", "audience", "hashtags", "creators"]
ANSWER_COLS = ["job", "key", "value", "choice", "by", "chat_id", "at"]
SETTINGS_COLS = [{"name": "key", "type": "string"}, {"name": "value", "type": "string"}, {"name": "set_by", "type": "string"},
                 {"name": "set_at", "type": "string"}]
SEND_FIELDS = {"appendAttribution": False, "parse_mode": "HTML", "disable_web_page_preview": True}
TODAY_IST = "={{ $now.setZone('Asia/Kolkata').startOf('day').toUTC().toISO() }}"

NOTES = {
    "Telegram Message": "Starts on every message, photo and button tap sent to the DTJ reel bot (one to one chats only).",
    "Read the Message": "Works out what the person wants: a tap or typed answer for a reel job, a product photo, /remake, /reel, "
                        "/reels N, /refs, /audience, /status or help. Never uses a message that looks like a password or key.",
    "Is It a Button?": "A button tap? Then the tapped button's loading spinner is stopped (next node).",
    "Answer the Button": "Tells Telegram the tap was received, so the button stops spinning.",
    "Load Bot Users": "The DTJ team list (dtj_bot_users, active people only). Only they may use the bot; admins may change the limit.",
    "Load Open Questions": "Questions a reel job is waiting on in this chat (open marks in dtj_bot_answers): a plain message answers the open one.",
    "Load Recent Photos": "Product photos this person sent to the bot (dtj_bot_answers, job reelpics-<chat>); the last 30 minutes count.",
    "Load Today's Reels": "Reels asked for today (dtj_reel_jobs, since midnight India time), for the daily limit and /status.",
    "Load Settings": "The bot's settings (dtj_reel_settings): the daily reel limit set with /reels N (10 when never set).",
    "Who Is It": "Decides what happens: answer, photo, new reel (unless today's limit is used), limit, reference search, or a reply "
                 "(help, status, a refusal with the reason). Unknown people get their Telegram number to send Harsh.",
    "What to Do": "Sends each request down its own path; everything else goes straight to Send.",
    "Save the Answer": "Saves the tap or typed answer in dtj_bot_answers (job, key, value, who, when), where the VPS worker, "
                       "reel_job.py and Find References read it. An Approve is that person's yes for that one step only.",
    "Save the Photo": "Keeps the photo's Telegram file id, so the next /remake or /reel uses it as a product picture (downloaded on the VPS).",
    "Start New Reel": "Starts Reel Factory: New Reel with the request (remake or UGC) and does not wait: the VPS worker asks "
                      "'tap Start if you are watching' in this chat.",
    "Save the Limit": "Saves today's reel limit (key daily_limit in dtj_reel_settings) with who set it and when.",
    "Start Find References": "Starts Reel Factory: Find References (/refs: winning reels of a brand; /audience: what an audience "
                             "watches) and does not wait; it sends its results to this chat.",
    "Say What Happened": "One short message saying what was done (or that it failed, so nothing is lost silently).",
    "Send": "Sends the reply in this chat through the DTJ reel bot.",
}


def _mapping(keys, src):
    return {"mappingMode": "defineBelow", "value": {k: f"={{{{ $json.{src}{k} }}}}" for k in keys}, "matchingColumns": [],
            "schema": [{"id": k, "displayName": k, "required": False, "defaultMatch": False, "display": True, "canBeUsedToMatch": True,
                        "type": "string"} for k in keys]}


def _rl(table_id, name):
    return {"__rl": True, "mode": "list", "value": table_id, "cachedResultName": name}


REFS_FLAG = "const REFS_READY = false;"


def code_of(name: str, refs_ready: bool = False) -> str:
    """A code node's file; the router's REFS_READY says whether Find References is published (n8n refuses to publish a workflow
    that starts an unpublished one, 25 Oct 2026)."""
    text = (HERE / CODE_NODES[name]).read_text(encoding="utf-8")
    return text.replace(REFS_FLAG, "const REFS_READY = true;") if refs_ready and name == "Who Is It" else text


def sdk_code(t: dict, wf: dict, refs_ready: bool = False) -> str:
    js = {name: code_of(name, refs_ready) for name in CODE_NODES}
    J = json.dumps

    def cfg(name, pos, params, extra=""):
        return (f"{{ name: {J(name)}, position: {J(pos)}, notes: {J(NOTES[name])}, notesInFlow: true, {extra}"
                f"parameters: {J(params)} }}")

    def code(var, name, pos):
        return (f"const {var} = node({{ type: 'n8n-nodes-base.code', version: 2, config: "
                f"{cfg(name, pos, {'mode': 'runOnceForAllItems', 'language': 'javaScript', 'jsCode': js[name]})} }});\n")

    def table(var, name, pos, params, extra="executeOnce: true, alwaysOutputData: true, onError: 'continueRegularOutput', "):
        return f"const {var} = node({{ type: 'n8n-nodes-base.dataTable', version: 1.1, config: {cfg(name, pos, params, extra)} }});\n"

    def get(table_name, conditions, **kw):
        return {"resource": "row", "operation": "get", "dataTableId": _rl(t[table_name], table_name), "matchType": "allConditions",
                "filters": {"conditions": conditions}, "returnAll": True, **kw}

    def start(var, name, pos, wf_name, keys):
        p = {"workflowId": _rl(wf[wf_name], wf_name), "workflowInputs": {**_mapping(keys, "inputs."), "attemptToConvertTypes": False,
             "convertFieldsToString": True}, "mode": "once", "options": {"waitForSubWorkflow": False}}
        keep_going = "onError: 'continueRegularOutput', alwaysOutputData: true, "
        return (f"const {var} = node({{ type: 'n8n-nodes-base.executeWorkflow', version: 1.3, config: "
                f"{cfg(name, pos, p, keep_going)} }});\n")

    def is_action(v):
        return {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                "conditions": [{"leftValue": "={{ $json.action }}", "rightValue": v, "operator": {"type": "string", "operation": "equals"}}],
                "combinator": "and"}
    cred = f"credentials: {{ telegramApi: newCredential({J(CREDENTIAL)}) }}, "
    chat = "={{ $('Read the Message').first().json.chat_id }}"
    return (
        "import { workflow, node, trigger, ifElse, switchCase, newCredential } from '@n8n/workflow-sdk';\n\n"
        "const telegramIn = trigger({ type: 'n8n-nodes-base.telegramTrigger', version: 1.5, config: "
        + cfg("Telegram Message", [0, 300], {"updates": ["message", "callback_query"], "additionalFields": {}}, cred) + " });\n"
        + code("readMessage", "Read the Message", [240, 300])
        + "const isButton = ifElse({ version: 2.2, config: " + cfg("Is It a Button?", [480, 560], {"conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
            "conditions": [{"leftValue": "={{ $json.callback_id }}", "operator": {"type": "string", "operation": "notEmpty", "singleValue": True}}],
            "combinator": "and"}}) + " });\n"
        + "const answerButton = node({ type: 'n8n-nodes-base.telegram', version: 1.2, config: " + cfg("Answer the Button", [720, 560],
            {"resource": "callback", "operation": "answerQuery", "queryId": "={{ $json.callback_id }}", "additionalFields": {}},
            cred + "onError: 'continueRegularOutput', ") + " });\n"
        + table("loadUsers", "Load Bot Users", [480, 300], get("dtj_bot_users", [{"keyName": "telegram_user_id", "condition": "isNotEmpty"}]))
        + table("loadOpen", "Load Open Questions", [720, 300], get("dtj_bot_answers", [{"keyName": "chat_id", "condition": "eq", "keyValue": chat},
                                                                                     {"keyName": "value", "condition": "isEmpty"}]))
        + table("loadPhotos", "Load Recent Photos", [960, 300], get("dtj_bot_answers", [
            {"keyName": "job", "condition": "eq", "keyValue": "=reelpics-{{ $('Read the Message').first().json.chat_id }}"}]))
        + table("loadToday", "Load Today's Reels", [1200, 300], get("dtj_reel_jobs", [{"keyName": "createdAt", "condition": "gte", "keyValue": TODAY_IST}]))
        + table("loadSettings", "Load Settings", [1440, 300], get("dtj_reel_settings", [{"keyName": "key", "condition": "isNotEmpty"}]))
        + code("whoIsIt", "Who Is It", [1680, 300])
        + "const whatToDo = switchCase({ version: 3.2, config: " + cfg("What to Do", [1920, 300], {
            "rules": {"values": [{"conditions": is_action(v), "renameOutput": True, "outputKey": v} for v in ("answer", "photo", "reel", "limit", "refs")]},
            "options": {"fallbackOutput": "extra", "renameFallbackOutput": "reply"}}) + " });\n"
        + table("saveAnswer", "Save the Answer", [2160, 0], {"resource": "row", "operation": "insert",
            "dataTableId": _rl(t["dtj_bot_answers"], "dtj_bot_answers"), "columns": _mapping(ANSWER_COLS, ""), "options": {}},
            "onError: 'continueRegularOutput', alwaysOutputData: true, ")
        + table("savePhoto", "Save the Photo", [2160, 160], {"resource": "row", "operation": "insert",
            "dataTableId": _rl(t["dtj_bot_answers"], "dtj_bot_answers"), "columns": _mapping(ANSWER_COLS, ""), "options": {}},
            "onError: 'continueRegularOutput', alwaysOutputData: true, ")
        + start("startReel", "Start New Reel", [2160, 320], NEW_REEL, REEL_INPUTS)
        + table("saveLimit", "Save the Limit", [2160, 480], {"resource": "row", "operation": "upsert",
            "dataTableId": _rl(t["dtj_reel_settings"], "dtj_reel_settings"), "matchType": "allConditions",
            "filters": {"conditions": [{"keyName": "key", "condition": "eq", "keyValue": "daily_limit"}]},
            "columns": _mapping(["key", "value", "set_by", "set_at"], ""), "options": {}},
            "onError: 'continueRegularOutput', alwaysOutputData: true, ")
        + start("startRefs", "Start Find References", [2160, 640], FIND_REFS, REFS_INPUTS)
        + code("sayWhat", "Say What Happened", [2400, 320])
        + "const send = node({ type: 'n8n-nodes-base.telegram', version: 1.2, config: " + cfg("Send", [2640, 460],
            {"resource": "message", "operation": "sendMessage", "chatId": "={{ $json.chat_id }}", "text": "={{ $json.text }}",
             "additionalFields": SEND_FIELDS}, cred + "onError: 'continueRegularOutput', ") + " });\n\n"
        "export default workflow('reel-factory-telegram-bot', " + J(NAME) + ")\n"
        "  .add(telegramIn).to(readMessage)\n"
        "  .add(readMessage).to(isButton.onTrue(answerButton))\n"
        "  .add(readMessage).to(loadUsers).to(loadOpen).to(loadPhotos).to(loadToday).to(loadSettings).to(whoIsIt)\n"
        "  .add(whoIsIt).to(whatToDo\n"
        "    .onCase(0, saveAnswer.to(sayWhat))\n"
        "    .onCase(1, savePhoto.to(sayWhat))\n"
        "    .onCase(2, startReel.to(sayWhat))\n"
        "    .onCase(3, saveLimit.to(sayWhat))\n"
        "    .onCase(4, startRefs.to(sayWhat))\n"
        "    .onCase(5, send))\n"
        "  .add(sayWhat).to(send)\n"
        "  .group('Load what the bot knows', [loadUsers, loadOpen, loadPhotos, loadToday, loadSettings], "
        "{ description: 'The team list, open questions, recent photos, today\\'s reels and the daily limit, read once per message' });\n"
    )


def find_table(name: str) -> str | None:
    found = [x for x in call("search_data_tables", {"query": name}).get("data", []) if x.get("name") == name]
    return found[0]["id"] if found else None


def tables() -> dict:
    out = {}
    for name in TABLES:
        tid = find_table(name)
        if not tid and name == "dtj_reel_settings":
            made = call("create_data_table", {"projectId": PROJECT, "name": name, "columns": SETTINGS_COLS})
            tid = made.get("id") or (made.get("dataTable") or {}).get("id")
            print(f"table {name}: created ({tid})")
        if not tid:
            raise RuntimeError(f"data table {name} is missing")
        out[name] = tid
    return out


def workflows() -> dict:
    out = {}
    for name in (NEW_REEL, FIND_REFS, NAME):
        found = [w for w in call("search_workflows", {"query": name}).get("data", []) if w.get("name") == name]
        out[name] = found[0]["id"] if found else None
        out[name + " active"] = bool(found and found[0].get("active"))
    for name in (NEW_REEL, FIND_REFS):
        if not out[name]:
            raise RuntimeError(f"workflow {name} is missing")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--publish", action="store_true")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if a.dry_run:
        print(sdk_code({n: f"<{n}>" for n in TABLES}, {NEW_REEL: "<new reel>", FIND_REFS: "<find refs>"}))
        return 0
    try:
        t, wf = tables(), workflows()
        refs_ready = wf[FIND_REFS + " active"]
        code = sdk_code(t, wf, refs_ready)
        wf_id = wf[NAME]
        if wf_id:
            ops = [{"type": "updateNodeParameters", "nodeName": n, "parameters": {"jsCode": code_of(n, refs_ready)}} for n in CODE_NODES]
            # n8n will not publish a workflow that starts an unpublished one: Find References is linked only once it is published
            ops.append({"type": "setNodeDisabled", "nodeName": "Start Find References", "disabled": not refs_ready})
            print("Find References published:", refs_ready, "-> /refs and /audience", "on" if refs_ready else "answer 'not ready yet'")
            print("exists: refreshing its code nodes", call("update_workflow", {"workflowId": wf_id, "operations": ops,
                  "versionName": "Reel bot: code nodes refreshed from git"}).get("appliedOperations"))
        else:
            check = call("validate_workflow", {"code": code})
            print("validate:", json.dumps(check)[:600])
            if check.get("valid") is False or check.get("errors"):
                return 1
            made = call("create_workflow_from_code", {"code": code, "projectId": PROJECT, "versionName": "Reel bot: first version",
                        "description": "The reel factory's own Telegram bot: /remake, /reel, /reels, /refs, /audience, /status, product "
                                       "photos, and every Approve / Start / Keep tap of a reel job (saved in dtj_bot_answers)."})
            print("created:", json.dumps(made)[:400])
            wf_id = made.get("workflowId") or made.get("id")
        creds = [c for c in call("list_credentials", {}).get("data", []) if c.get("name") == CREDENTIAL and c.get("type") == "telegramApi"]
        tg_nodes = ("Telegram Message", "Answer the Button", "Send")
        if creds:
            call("update_workflow", {"workflowId": wf_id, "versionName": "Reel bot: DTJ Reel Bot credential", "operations": [
                {"type": "setNodeCredential", "nodeName": n, "credentialKey": "telegramApi", "credentialId": creds[0]["id"],
                 "credentialName": CREDENTIAL} for n in tg_nodes] + [{"type": "setNodeDisabled", "nodeName": n, "disabled": False} for n in tg_nodes]})
            print(f"credential '{CREDENTIAL}' attached; Telegram nodes on")
        else:
            # n8n fills a missing credential with the first Telegram one it has (the STORE bot): if this workflow ran like that it would
            # take the store bot's messages. So its Telegram nodes stay off until the reel bot's own credential exists.
            call("update_workflow", {"workflowId": wf_id, "versionName": "Reel bot: Telegram nodes off until DTJ Reel Bot exists",
                                     "operations": [{"type": "setNodeDisabled", "nodeName": n, "disabled": True} for n in tg_nodes]})
            print(f"no Telegram credential named '{CREDENTIAL}' yet, so its Telegram nodes are OFF (n8n had filled in the store bot's). "
                  "Harsh: create the bot in BotFather, add the credential in n8n (Credentials > Add > Telegram API, name 'DTJ Reel Bot'), "
                  "then run this again and --publish")
        if a.publish:
            if not creds:
                print("not published: the credential is missing")
                return 1
            print("publish:", call("publish_workflow", {"workflowId": wf_id}))
        after = call("get_workflow_details", {"workflowId": wf_id})["workflow"]
    except (urllib.error.URLError, RuntimeError, OSError) as exc:
        print(f"not deployed: {exc}", file=sys.stderr)
        return 1
    live = {n["name"]: n for n in after["nodes"]}
    mismatched = [n for n in CODE_NODES if live.get(n, {}).get("parameters", {}).get("jsCode") != code_of(n, refs_ready)]
    no_notes = [n for n in NOTES if not live.get(n, {}).get("notes")]
    export = {k: after.get(k) for k in ("id", "name", "description", "nodes", "connections", "settings") if k in after}
    (HERE / "reel_bot.workflow.json").write_text(json.dumps(export, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"workflow {wf_id}: {len(live)} nodes; code identical: {not mismatched} {mismatched or ''}; nodes without a note: "
          f"{no_notes or 'none'}; active: {after.get('active')}; export: reel_bot.workflow.json")
    return 0 if not mismatched else 1


if __name__ == "__main__":
    raise SystemExit(main())
