"""Deploy the Telegram bot: "Store Factory: Telegram Bot" + the result message at the end of "Store Factory: Page Design".

    python n8n/store-factory/deploy_telegram_bot.py --dry-run             print the generated bot workflow code, change nothing
    python n8n/store-factory/deploy_telegram_bot.py                       create the bot workflow (or refresh its code) and add the
                                                                           "Tell the Requester" + "Send Result" steps to Page Design
    python n8n/store-factory/deploy_telegram_bot.py --attach-credential   after Harsh saved the bot token in n8n as the Telegram API
                                                                           credential "DTJ Page Bot": put it on the 3 Telegram nodes

Telegram Message -> Read the Message -> Load Bot Users (dtj_bot_users) -> Who Is It -> Start a Page?
    yes -> Ask New Page (Store Factory: New Page, waits for its answer) -> Write the Answers -> Send
    no  -> Send   (help, "send a product link", "this bot is only for the DTJ team: your number is ...", "delete that password")
Page Design: Claude Code Reply -> Tell the Requester -> Send Result (only for briefs that came from Telegram).
The bot token never passes through this script or git: Harsh pastes it into n8n's credential screen himself. Everything stays
UNPUBLISHED; Telegram only delivers messages after Harsh publishes the bot workflow.
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
CREDENTIAL = "DTJ Page Bot"
CODE_NODES = {"Read the Message": "bot_read.js", "Who Is It": "bot_route.js", "Write the Answers": "bot_answer.js"}
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


def _code(var: str, name: str, file: str, pos: str) -> str:
    js = json.dumps((HERE / file).read_text(encoding="utf-8"))
    return (f"const {var} = node({{ type: 'n8n-nodes-base.code', version: 2, config: {{ name: {json.dumps(name)}, position: {pos}, "
            f"parameters: {{ mode: 'runOnceForAllItems', language: 'javaScript', jsCode: {js} }} }} }});\n")


def sdk_code() -> str:
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


def page_design_ops(live: dict) -> list[dict]:
    notify = (HERE / NOTIFY_JS).read_text(encoding="utf-8")
    ops: list[dict] = []
    if "Tell the Requester" not in live:
        ops += [
            {"type": "addNode", "node": {"name": "Tell the Requester", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [1200, 240],
                                         "parameters": {"mode": "runOnceForAllItems", "language": "javaScript", "jsCode": notify}}},
            {"type": "addNode", "node": {"name": "Send Result", "type": "n8n-nodes-base.telegram", "typeVersion": 1.2, "position": [1440, 240],
                                         "parameters": {"resource": "message", "operation": "sendMessage", "chatId": "={{ $json.chat_id }}",
                                                        "text": "={{ $json.text }}", "additionalFields": SEND_FIELDS}}},
            {"type": "setNodeSettings", "nodeName": "Send Result", "settings": {"onError": "continueRegularOutput"}},
            {"type": "addConnection", "source": "Claude Code Reply: Page Design", "target": "Tell the Requester"},
            {"type": "addConnection", "source": "Tell the Requester", "target": "Send Result"},
        ]
    else:
        ops.append({"type": "updateNodeParameters", "nodeName": "Tell the Requester", "parameters": {"jsCode": notify}})
    return ops


def find_bot() -> str | None:
    found = [w for w in call("search_workflows", {"query": NAME}).get("data", []) if w.get("name") == NAME]
    return found[0]["id"] if found else None


def attach_credential() -> int:
    creds = [c for c in call("list_credentials", {}).get("data", []) if c.get("name") == CREDENTIAL and c.get("type") == "telegramApi"]
    if not creds:
        print(f"no Telegram API credential named '{CREDENTIAL}' in n8n yet: Harsh creates it (Credentials > Create > Telegram API)")
        return 1
    cid = creds[0]["id"]
    bot = find_bot()
    if not bot:
        print("the bot workflow does not exist yet: run this script without --attach-credential first")
        return 1
    for wf, nodes in ((bot, ["Telegram Message", "Send"]), (PAGE_DESIGN, ["Send Result"])):
        ops = [{"type": "setNodeCredential", "nodeName": n, "credentialKey": "telegramApi", "credentialId": cid, "credentialName": CREDENTIAL}
               for n in nodes]
        print(wf, call("update_workflow", {"workflowId": wf, "operations": ops}).get("appliedOperations"), "credential(s) attached")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--attach-credential", action="store_true")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    code = sdk_code()
    if args.dry_run:
        print(code)
        return 0
    try:
        if args.attach_credential:
            return attach_credential()
        bot = find_bot()
        if bot:
            ops = [{"type": "updateNodeParameters", "nodeName": n, "parameters": {"jsCode": (HERE / f).read_text(encoding="utf-8")}}
                   for n, f in CODE_NODES.items()]
            print("bot exists: refreshing its code nodes", call("update_workflow", {"workflowId": bot, "operations": ops}).get("appliedOperations"))
        else:
            check = call("validate_workflow", {"code": code})
            print("validate:", json.dumps(check)[:600])
            if check.get("valid") is False or check.get("errors"):
                return 1
            made = call("create_workflow_from_code", {"code": code, "description": DESCRIPTION, "versionName": "Telegram page bot"})
            bot = made.get("workflowId") or made.get("id")
            print("created:", bot, made.get("url"))
        live_pd = {n["name"]: n for n in call("get_workflow_details", {"workflowId": PAGE_DESIGN})["workflow"]["nodes"]}
        ops = page_design_ops(live_pd)
        print("page design:", call("update_workflow", {"workflowId": PAGE_DESIGN, "operations": ops}).get("appliedOperations"), "operation(s)")
        after = call("get_workflow_details", {"workflowId": bot})["workflow"]
        pd = call("get_workflow_details", {"workflowId": PAGE_DESIGN})["workflow"]
    except (urllib.error.URLError, RuntimeError, OSError) as exc:
        print(f"not deployed: {exc}", file=sys.stderr)
        return 1
    live = {n["name"]: n for n in after["nodes"]}
    pd_live = {n["name"]: n for n in pd["nodes"]}
    mismatched = [n for n, f in CODE_NODES.items() if live.get(n, {}).get("parameters", {}).get("jsCode") != (HERE / f).read_text(encoding="utf-8")]
    if pd_live.get("Tell the Requester", {}).get("parameters", {}).get("jsCode") != (HERE / NOTIFY_JS).read_text(encoding="utf-8"):
        mismatched.append("Page Design / Tell the Requester")
    for wf, file in ((after, "telegram_bot.workflow.json"), (pd, "page_design.workflow.json")):
        export = {k: wf.get(k) for k in ("id", "name", "description", "nodes", "connections", "settings") if k in wf}
        (HERE / file).write_text(json.dumps(export, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"bot {bot}: {len(live)} nodes, active {after.get('active')}; page design: {len(pd_live)} nodes; "
          f"code identical to the files: {not mismatched} {mismatched or ''}; exports saved")
    return 0 if not mismatched else 1


if __name__ == "__main__":
    raise SystemExit(main())
