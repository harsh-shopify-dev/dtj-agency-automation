"""Deploy the Telegram bot: "Store Factory: Telegram Bot" + the result message at the end of "Store Factory: Page Design".

    python n8n/store-factory/deploy_telegram_bot.py --dry-run             print the generated bot workflow code, change nothing
    python n8n/store-factory/deploy_telegram_bot.py                       create the bot (first time); later: add the app switch
                                                                           once, or refresh the code nodes; add Page Design's
                                                                           "Tell the Requester" + "Send Result"
    python n8n/store-factory/deploy_telegram_bot.py --attach-credential   put the saved credentials on their nodes: Telegram API
                                                                           "DTJ Page Bot" and Header Auth "DTJ Catcher Bot Key"

Telegram Message -> Read the Message -> Load Bot Users -> Load Shops -> Who Is It -> What to Do
    design  -> Ask New Page (Store Factory: New Page, waits for its answer) -> Write the Answers -> Send
    switch  -> Ask for the Shop List (install catcher /licence state "list", bot key) -> Pick the Shop -> What Next
                   licence -> Licence Calls -> Ask the Switch (install catcher /licence, bot key) -> Licence Report -> Send
                   confirm -> Ask to Confirm (the "Yes, switch ..." / "Cancel" buttons)
                   reply   -> Send
    reply   -> Send
Read the Message -> Is It a Button? -> Answer the Button (stops the button's spinner)
Page Design: Claude Code Reply -> Tell the Requester -> Send Result (only for briefs that came from Telegram).
No token or key passes through this script or git: Harsh pastes them into n8n's credential screens himself. Changes to a published
workflow stay in its draft until it is published again.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from n8n_mcp import PAGE_DESIGN, call  # noqa: E402

HERE = Path(__file__).resolve().parent
NAME = "Store Factory: Telegram Bot"
NEW_PAGE = "Z3s9hqny1d2shvXT"
BOT_USERS = "xJ9O19tBBmCJc1Hc"
STORES = "QaOZ6MuvFLyft2y9"
CREDENTIAL = "DTJ Page Bot"                 # n8n Telegram API credential (the bot token)
SWITCH_CREDENTIAL = "DTJ Catcher Bot Key"   # n8n Header Auth credential: name X-DTJ-Bot-Key, value = the catcher's BOT_KEY
CATCHER = "https://dtj-install-catcher.ultimateecomwithharsh.workers.dev/licence"
CODE_NODES = {"Read the Message": "bot_read.js", "Who Is It": "bot_route.js", "Write the Answers": "bot_answer.js",
              "Pick the Shop": "bot_switch.js", "Licence Calls": "licence_calls.js", "Licence Report": "licence_report.js"}
SWITCH_NODES = ("Ask the Switch", "Ask for the Shop List")  # the HTTP steps that carry the bot's key
NOTIFY_JS = "notify_result.js"
SEND_FIELDS = {"appendAttribution": False, "parse_mode": "HTML", "disable_web_page_preview": True}
DESCRIPTION = "Store factory Telegram bot: a team member sends a product link, the bot starts Store Factory: New Page and replies."
STICKY = ("## DTJ page bot (Telegram)\n"
          "A team member sends a product link (and a note) to the bot in a private chat. Only people in the data table "
          "**dtj_bot_users** (active) may use it; anyone else gets their Telegram number to send to Harsh. Roles: requester, designer "
          "(also told when a page waits for Claude Code), admin.\n\n"
          "The link goes to **Store Factory: New Page**; the answer comes back here. When the page is done, **Store Factory: Page "
          "Design** sends the preview link to the person who asked.\n\n"
          "Credential: Telegram API **DTJ Page Bot** (the token is pasted by Harsh in n8n, never in git or chat). "
          "Source in git: `n8n/store-factory/`.")


def code(file: str) -> str:
    return (HERE / file).read_text(encoding="utf-8")


def _code(var: str, name: str, file: str, pos: str) -> str:
    return (f"const {var} = node({{ type: 'n8n-nodes-base.code', version: 2, config: {{ name: {json.dumps(name)}, position: {pos}, "
            f"parameters: {{ mode: 'runOnceForAllItems', language: 'javaScript', jsCode: {json.dumps(code(file))} }} }} }});\n")


def sdk_code() -> str:
    """The first version of the bot (a link in, an answer out). The app switch is added to the live workflow by switch_ops()."""
    inputs = ["product_link", "note", "requested_by", "chat_id"]
    values = json.dumps({k: f"={{{{ $json.{k} }}}}" for k in inputs})
    schema = json.dumps([{"id": k, "displayName": k, "required": False, "defaultMatch": False, "display": True,
                          "canBeUsedToMatch": True, "type": "string"} for k in inputs])
    return (
        "import { workflow, node, trigger, sticky, ifElse, expr, newCredential } from '@n8n/workflow-sdk';\n\n"
        "const telegramIn = trigger({ type: 'n8n-nodes-base.telegramTrigger', version: 1.5, config: { name: 'Telegram Message', "
        "position: [0, 120], parameters: { updates: ['message'], additionalFields: {} }, "
        f"credentials: {{ telegramApi: newCredential({json.dumps(CREDENTIAL)}) }} }} }});\n"
        + _code("readMessage", "Read the Message", "bot_read.js", "[240, 120]")
        + "const loadUsers = node({ type: 'n8n-nodes-base.dataTable', version: 1.1, config: { name: 'Load Bot Users', position: [480, 120], "
          "executeOnce: true, alwaysOutputData: true, parameters: { resource: 'row', operation: 'get', "
          f"dataTableId: {{ __rl: true, mode: 'list', value: '{BOT_USERS}', cachedResultName: 'dtj_bot_users' }}, matchType: 'allConditions', "
          "filters: { conditions: [{ keyName: 'telegram_user_id', condition: 'isNotEmpty' }] }, returnAll: true } } });\n"
        + _code("whoIsIt", "Who Is It", "bot_route.js", "[720, 120]")
        + "const startPage = ifElse({ version: 2.2, config: { name: 'Start a Page?', position: [960, 120], parameters: { conditions: { "
          "options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' }, conditions: [{ leftValue: expr('{{ $json.action }}'), "
          "rightValue: 'design', operator: { type: 'string', operation: 'equals' } }], combinator: 'and' } } } });\n"
        + "const askNewPage = node({ type: 'n8n-nodes-base.executeWorkflow', version: 1.3, config: { name: 'Ask New Page', position: [1200, 0], "
          f"parameters: {{ workflowId: {{ __rl: true, mode: 'list', value: '{NEW_PAGE}', cachedResultName: 'Store Factory: New Page' }}, "
          f"workflowInputs: {{ mappingMode: 'defineBelow', value: {values}, matchingColumns: [], schema: {schema}, "
          "attemptToConvertTypes: false, convertFieldsToString: true }, mode: 'once', options: { waitForSubWorkflow: true } } } });\n"
        + _code("writeAnswers", "Write the Answers", "bot_answer.js", "[1440, 0]")
        + "const send = node({ type: 'n8n-nodes-base.telegram', version: 1.2, config: { name: 'Send', position: [1680, 120], "
          "onError: 'continueRegularOutput', parameters: { resource: 'message', operation: 'sendMessage', chatId: expr('{{ $json.chat_id }}'), "
          f"text: expr('{{{{ $json.text }}}}'), additionalFields: {json.dumps(SEND_FIELDS)} }}, "
          f"credentials: {{ telegramApi: newCredential({json.dumps(CREDENTIAL)}) }} }} }});\n"
        + f"const about = sticky({json.dumps(STICKY)}, [telegramIn, readMessage, loadUsers, whoIsIt], "
          "{ color: 5, position: [-40, -300], width: 980, height: 300 });\n\n"
        "export default workflow('store-factory-telegram-bot', " + json.dumps(NAME) + ")\n"
        "  .add(telegramIn).to(readMessage).to(loadUsers).to(whoIsIt)\n"
        "  .to(startPage.onTrue(askNewPage.to(writeAnswers.to(send))).onFalse(send))\n"
        "  .add(about);\n"
    )


def credential_id(name: str, ctype: str) -> str | None:
    found = [c for c in call("list_credentials", {}).get("data", []) if c.get("name") == name and c.get("type") == ctype]
    return found[0]["id"] if found else None


def _action_is(value: str) -> dict:
    return {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
            "conditions": [{"leftValue": "={{ $json.action }}", "rightValue": value, "operator": {"type": "string", "operation": "equals"}}],
            "combinator": "and"}


def _add(name: str, ntype: str, version: float, pos: list[int], params: dict) -> dict:
    return {"type": "addNode", "node": {"name": name, "type": ntype, "typeVersion": version, "position": pos, "parameters": params}}


def switch_ops(live: set[str], telegram_id: str | None) -> list[dict]:
    """The app switch (12 Oct 2026): admin commands /shops /status /on /off, confirm buttons, the calls to the install catcher."""
    ops: list[dict] = [
        {"type": "setNodeParameter", "nodeName": "Telegram Message", "path": "/updates", "value": ["message", "callback_query"]},
        {"type": "updateNodeParameters", "nodeName": "Read the Message", "parameters": {"jsCode": code("bot_read.js")}},
        {"type": "updateNodeParameters", "nodeName": "Who Is It", "parameters": {"jsCode": code("bot_route.js")}},
        _add("Load Shops", "n8n-nodes-base.dataTable", 1.1, [600, 120], {
            "resource": "row", "operation": "get", "dataTableId": {"__rl": True, "mode": "list", "value": STORES, "cachedResultName": "dtj_stores"},
            "matchType": "allConditions", "filters": {"conditions": [{"keyName": "myshopify_domain", "condition": "isNotEmpty"}]}, "returnAll": True}),
        {"type": "setNodeSettings", "nodeName": "Load Shops", "settings": {"executeOnce": True, "alwaysOutputData": True}},
        {"type": "removeConnection", "source": "Load Bot Users", "target": "Who Is It"},
        {"type": "addConnection", "source": "Load Bot Users", "target": "Load Shops"},
        {"type": "addConnection", "source": "Load Shops", "target": "Who Is It"},
        {"type": "setNodePosition", "nodeName": "Who Is It", "position": [840, 120]},
    ]
    if "Start a Page?" in live:
        ops.append({"type": "removeNode", "nodeName": "Start a Page?"})
    ops += [
        _add("What to Do", "n8n-nodes-base.switch", 3.2, [1080, 120], {
            "rules": {"values": [{"conditions": _action_is(v), "renameOutput": True, "outputKey": v} for v in ("design", "licence", "confirm")]},
            "options": {"fallbackOutput": "extra", "renameFallbackOutput": "reply"}}),
        {"type": "addConnection", "source": "Who Is It", "target": "What to Do"},
        {"type": "addConnection", "source": "What to Do", "sourceIndex": 0, "target": "Ask New Page"},
        _add("Licence Calls", "n8n-nodes-base.code", 2, [1320, 240], {"mode": "runOnceForAllItems", "language": "javaScript",
                                                                      "jsCode": code("licence_calls.js")}),
        {"type": "addConnection", "source": "What to Do", "sourceIndex": 1, "target": "Licence Calls"},
        _add("Ask the Switch", "n8n-nodes-base.httpRequest", 4.2, [1560, 240], {
            "method": "POST", "url": CATCHER, "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
            "sendHeaders": True, "headerParameters": {"parameters": [{"name": "User-Agent", "value": "dtj-n8n-bot/1"}]},
            "sendBody": True, "contentType": "json", "specifyBody": "json", "jsonBody": "={{ $json.body }}",
            "options": {"response": {"response": {"fullResponse": True, "neverError": True}}, "timeout": 60000}}),
        {"type": "setNodeSettings", "nodeName": "Ask the Switch", "settings": {"onError": "continueRegularOutput"}},
        {"type": "addConnection", "source": "Licence Calls", "target": "Ask the Switch"},
        _add("Licence Report", "n8n-nodes-base.code", 2, [1800, 240], {"mode": "runOnceForAllItems", "language": "javaScript",
                                                                       "jsCode": code("licence_report.js")}),
        {"type": "addConnection", "source": "Ask the Switch", "target": "Licence Report"},
        {"type": "addConnection", "source": "Licence Report", "target": "Send"},
        _add("Ask to Confirm", "n8n-nodes-base.telegram", 1.2, [1320, 400], {
            "resource": "message", "operation": "sendMessage", "chatId": "={{ $json.chat_id }}", "text": "={{ $json.text }}",
            "replyMarkup": "inlineKeyboard", "inlineKeyboard": {"rows": [{"row": {"buttons": [
                {"text": "={{ $json.yes_text }}", "additionalFields": {"callback_data": "={{ $json.yes_data }}"}},
                {"text": "Cancel", "additionalFields": {"callback_data": "lic:cancel"}}]}}]},
            "additionalFields": SEND_FIELDS}),
        {"type": "setNodeSettings", "nodeName": "Ask to Confirm", "settings": {"onError": "continueRegularOutput"}},
        {"type": "addConnection", "source": "What to Do", "sourceIndex": 2, "target": "Ask to Confirm"},
        {"type": "addConnection", "source": "What to Do", "sourceIndex": 3, "target": "Send"},
        _add("Is It a Button?", "n8n-nodes-base.if", 2.2, [480, 320], {"conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
            "conditions": [{"leftValue": "={{ $json.kind }}", "rightValue": "button", "operator": {"type": "string", "operation": "equals"}}],
            "combinator": "and"}}),
        {"type": "addConnection", "source": "Read the Message", "target": "Is It a Button?"},
        _add("Answer the Button", "n8n-nodes-base.telegram", 1.2, [720, 320], {
            "resource": "callback", "operation": "answerQuery", "queryId": "={{ $json.callback_id }}", "additionalFields": {}}),
        {"type": "setNodeSettings", "nodeName": "Answer the Button", "settings": {"onError": "continueRegularOutput"}},
        {"type": "addConnection", "source": "Is It a Button?", "sourceIndex": 0, "target": "Answer the Button"},
        {"type": "setNodePosition", "nodeName": "Send", "position": [2040, 120]},
    ]
    if telegram_id:
        ops += [{"type": "setNodeCredential", "nodeName": n, "credentialKey": "telegramApi", "credentialId": telegram_id, "credentialName": CREDENTIAL}
                for n in ("Ask to Confirm", "Answer the Button")]
    return ops


def _catcher_call(name: str, pos: list[int], body: str) -> dict:
    return _add(name, "n8n-nodes-base.httpRequest", 4.2, pos, {
        "method": "POST", "url": CATCHER, "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
        "sendHeaders": True, "headerParameters": {"parameters": [{"name": "User-Agent", "value": "dtj-n8n-bot/1"}]},
        "sendBody": True, "contentType": "json", "specifyBody": "json", "jsonBody": body,
        "options": {"response": {"response": {"fullResponse": True, "neverError": True}}, "timeout": 60000}})


def directory_ops(switch_key: str | None) -> list[dict]:
    """The switch's directory (12 Oct 2026, Harsh: "on every store we work on the switch must work"): an admin command first asks
    the install catcher which shops it reaches, then "Pick the Shop" finds the one named. Client copies, app-only clients and DTJ's
    own apps on organization stores are all on that list, so dtj_stores no longer limits the switch."""
    ops: list[dict] = [
        {"type": "updateNodeParameters", "nodeName": "Who Is It", "parameters": {"jsCode": code("bot_route.js")}},
        {"type": "setNodeParameter", "nodeName": "What to Do", "path": "/rules/values",
         "value": [{"conditions": _action_is(v), "renameOutput": True, "outputKey": v} for v in ("design", "switch")]},
        {"type": "removeConnection", "source": "What to Do", "sourceIndex": 1, "target": "Licence Calls"},
        {"type": "removeConnection", "source": "What to Do", "sourceIndex": 2, "target": "Ask to Confirm"},
        {"type": "removeConnection", "source": "What to Do", "sourceIndex": 3, "target": "Send"},
        _catcher_call("Ask for the Shop List", [1320, 240], "={{ JSON.stringify({ state: 'list', ts: Math.floor(Date.now() / 1000) }) }}"),
        {"type": "setNodeSettings", "nodeName": "Ask for the Shop List", "settings": {"onError": "continueRegularOutput"}},
        {"type": "addConnection", "source": "What to Do", "sourceIndex": 1, "target": "Ask for the Shop List"},
        {"type": "addConnection", "source": "What to Do", "sourceIndex": 2, "target": "Send"},
        _add("Pick the Shop", "n8n-nodes-base.code", 2, [1560, 240], {"mode": "runOnceForAllItems", "language": "javaScript",
                                                                       "jsCode": code("bot_switch.js")}),
        {"type": "addConnection", "source": "Ask for the Shop List", "target": "Pick the Shop"},
        _add("What Next", "n8n-nodes-base.switch", 3.2, [1800, 240], {
            "rules": {"values": [{"conditions": _action_is(v), "renameOutput": True, "outputKey": v} for v in ("licence", "confirm")]},
            "options": {"fallbackOutput": "extra", "renameFallbackOutput": "reply"}}),
        {"type": "addConnection", "source": "Pick the Shop", "target": "What Next"},
        {"type": "addConnection", "source": "What Next", "sourceIndex": 0, "target": "Licence Calls"},
        {"type": "addConnection", "source": "What Next", "sourceIndex": 1, "target": "Ask to Confirm"},
        {"type": "addConnection", "source": "What Next", "sourceIndex": 2, "target": "Send"},
        {"type": "updateNodeParameters", "nodeName": "Licence Calls", "parameters": {"jsCode": code("licence_calls.js")}},
        {"type": "updateNodeParameters", "nodeName": "Licence Report", "parameters": {"jsCode": code("licence_report.js")}},
        {"type": "setNodePosition", "nodeName": "Licence Calls", "position": [2040, 240]},
        {"type": "setNodePosition", "nodeName": "Ask the Switch", "position": [2280, 240]},
        {"type": "setNodePosition", "nodeName": "Licence Report", "position": [2520, 240]},
        {"type": "setNodePosition", "nodeName": "Ask to Confirm", "position": [2040, 420]},
        {"type": "setNodePosition", "nodeName": "Send", "position": [2760, 120]},
    ]
    if switch_key:
        ops.append({"type": "setNodeCredential", "nodeName": "Ask for the Shop List", "credentialKey": "httpHeaderAuth",
                    "credentialId": switch_key, "credentialName": SWITCH_CREDENTIAL})
    return ops


def page_design_ops(live: dict) -> list[dict]:
    notify = code(NOTIFY_JS)
    if "Tell the Requester" in live:
        return [{"type": "updateNodeParameters", "nodeName": "Tell the Requester", "parameters": {"jsCode": notify}}]
    return [
        _add("Tell the Requester", "n8n-nodes-base.code", 2, [1200, 240], {"mode": "runOnceForAllItems", "language": "javaScript", "jsCode": notify}),
        _add("Send Result", "n8n-nodes-base.telegram", 1.2, [1440, 240], {"resource": "message", "operation": "sendMessage",
                                                                         "chatId": "={{ $json.chat_id }}", "text": "={{ $json.text }}",
                                                                         "additionalFields": SEND_FIELDS}),
        {"type": "setNodeSettings", "nodeName": "Send Result", "settings": {"onError": "continueRegularOutput"}},
        {"type": "addConnection", "source": "Claude Code Reply: Page Design", "target": "Tell the Requester"},
        {"type": "addConnection", "source": "Tell the Requester", "target": "Send Result"},
    ]


def find_bot() -> str | None:
    found = [w for w in call("search_workflows", {"query": NAME}).get("data", []) if w.get("name") == NAME]
    return found[0]["id"] if found else None


def attach_credential() -> int:
    cid = credential_id(CREDENTIAL, "telegramApi")
    if not cid:
        print(f"no Telegram API credential named '{CREDENTIAL}' in n8n yet: Harsh creates it (Credentials > Create > Telegram API)")
        return 1
    bot = find_bot()
    if not bot:
        print("the bot workflow does not exist yet: run this script without --attach-credential first")
        return 1
    live = {n["name"] for n in call("get_workflow_details", {"workflowId": bot})["workflow"]["nodes"]}
    tg_nodes = [n for n in ("Telegram Message", "Send", "Ask to Confirm", "Answer the Button") if n in live]
    for wf, nodes in ((bot, tg_nodes), (PAGE_DESIGN, ["Send Result"])):
        ops = [{"type": "setNodeCredential", "nodeName": n, "credentialKey": "telegramApi", "credentialId": cid, "credentialName": CREDENTIAL}
               for n in nodes]
        print(wf, call("update_workflow", {"workflowId": wf, "operations": ops}).get("appliedOperations"), "Telegram credential(s) attached")
    key = credential_id(SWITCH_CREDENTIAL, "httpHeaderAuth")
    switch_nodes = [n for n in SWITCH_NODES if n in live]
    if switch_nodes and key:
        ops = [{"type": "setNodeCredential", "nodeName": n, "credentialKey": "httpHeaderAuth", "credentialId": key,
                "credentialName": SWITCH_CREDENTIAL} for n in switch_nodes]
        print(bot, call("update_workflow", {"workflowId": bot, "operations": ops}).get("appliedOperations"), "switch key attached")
    elif switch_nodes:
        print(f"no Header Auth credential named '{SWITCH_CREDENTIAL}' yet: the app switch has no key until Harsh creates it")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--attach-credential", action="store_true")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.dry_run:
        print(sdk_code())
        for label, ops in (("switch", switch_ops({"Start a Page?"}, "telegram-credential-id")), ("directory", directory_ops("key-id"))):
            for op in ops:
                print(f"{label} op: {op['type']} {op.get('nodeName') or (op.get('node') or {}).get('name') or ''} "
                      f"{op.get('source', '')} {op.get('target', '')}".rstrip())
        return 0
    try:
        if args.attach_credential:
            return attach_credential()
        bot = find_bot()
        if bot:
            live_bot = {n["name"] for n in call("get_workflow_details", {"workflowId": bot})["workflow"]["nodes"]}
            if "Licence Calls" not in live_bot:
                ops = switch_ops(live_bot, credential_id(CREDENTIAL, "telegramApi"))
                print("adding the app switch:", call("update_workflow", {"workflowId": bot, "operations": ops}).get("appliedOperations"), "operation(s)")
                live_bot = {n["name"] for n in call("get_workflow_details", {"workflowId": bot})["workflow"]["nodes"]}
            if "Pick the Shop" not in live_bot:
                ops = directory_ops(credential_id(SWITCH_CREDENTIAL, "httpHeaderAuth"))
                print("adding the switch's shop list:", call("update_workflow", {"workflowId": bot, "operations": ops,
                      "versionName": "Switch: every shop the catcher reaches"}).get("appliedOperations"), "operation(s)")
            else:
                ops = [{"type": "updateNodeParameters", "nodeName": n, "parameters": {"jsCode": code(f)}} for n, f in CODE_NODES.items() if n in live_bot]
                print("refreshing the code nodes:", call("update_workflow", {"workflowId": bot, "operations": ops}).get("appliedOperations"))
        else:
            check = call("validate_workflow", {"code": sdk_code()})
            print("validate:", json.dumps(check)[:600])
            if check.get("valid") is False or check.get("errors"):
                return 1
            made = call("create_workflow_from_code", {"code": sdk_code(), "description": DESCRIPTION, "versionName": "Telegram page bot"})
            bot = made.get("workflowId") or made.get("id")
            print("created:", bot, made.get("url"))
        live_pd = {n["name"]: n for n in call("get_workflow_details", {"workflowId": PAGE_DESIGN})["workflow"]["nodes"]}
        print("page design:", call("update_workflow", {"workflowId": PAGE_DESIGN, "operations": page_design_ops(live_pd)}).get("appliedOperations"),
              "operation(s)")
        after = call("get_workflow_details", {"workflowId": bot})["workflow"]
        pd = call("get_workflow_details", {"workflowId": PAGE_DESIGN})["workflow"]
    except (urllib.error.URLError, RuntimeError, OSError) as exc:
        print(f"not deployed: {exc}", file=sys.stderr)
        return 1
    live = {n["name"]: n for n in after["nodes"]}
    pd_live = {n["name"]: n for n in pd["nodes"]}
    mismatched = [n for n, f in CODE_NODES.items() if n in live and live[n].get("parameters", {}).get("jsCode") != code(f)]
    if pd_live.get("Tell the Requester", {}).get("parameters", {}).get("jsCode") != code(NOTIFY_JS):
        mismatched.append("Page Design / Tell the Requester")
    for wf, file in ((after, "telegram_bot.workflow.json"), (pd, "page_design.workflow.json")):
        export = {k: wf.get(k) for k in ("id", "name", "description", "nodes", "connections", "settings") if k in wf}
        (HERE / file).write_text(json.dumps(export, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"bot {bot}: {len(live)} nodes, active {after.get('active')}; page design: {len(pd_live)} nodes; "
          f"code identical to the files: {not mismatched} {mismatched or ''}; exports saved")
    return 0 if not mismatched else 1


if __name__ == "__main__":
    raise SystemExit(main())
