"""Deploy "Store Factory: Add Shop" to DTJ's n8n: an admin's /addshop in Telegram becomes one Claude Code hand-off on a DTJ laptop.

    python n8n/store-factory/deploy_add_shop.py --dry-run     print the generated workflow code, change nothing
    python n8n/store-factory/deploy_add_shop.py               create it (or refresh its code nodes when it exists)

From the Telegram Bot (shop, label, requested_by, chat_id) -> Request for Claude Code: Add Shop -> Wait for Claude Code: Add Shop
    -> Claude Code Reply: Add Shop -> Tell the Requester -> Send Result (Telegram "DTJ Page Bot")
The laptop's Claude Code runs services/install-catcher/tools/add_shop.py (the seven app copies made, linked and released, the install
service deployed, seven Install buttons in Telegram) and answers through reply.py. The code nodes are the add_shop_*.js files next to
this script (run in Node by test_bot_nodes.py), sent byte for byte; afterwards the live workflow is read back, compared and exported to
add_shop.workflow.json. The workflow is created UNPUBLISHED. Undo: n8n keeps every version.
`handoff_code` and `deploy` build any such hand-off workflow (deploy_new_store.py uses them too).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from n8n_mcp import call  # noqa: E402

HERE = Path(__file__).resolve().parent
CREDENTIAL = "DTJ Page Bot"  # n8n Telegram API credential (the bot token, pasted by Harsh in n8n)
SEND_FIELDS = {"appendAttribution": False, "parse_mode": "HTML", "disable_web_page_preview": True}
ADD_SHOP = {
    "name": "Store Factory: Add Shop", "slug": "store-factory-add-shop", "step": "Add Shop", "days": 3,
    "inputs": ["shop", "label", "requested_by", "chat_id"],
    "code": {"request": "add_shop_request.js", "reply": "add_shop_reply.js", "tell": "add_shop_notify.js"},
    "export": "add_shop.workflow.json", "version": "Add a client shop (/addshop)",
    "description": ("Store factory: an admin's /addshop (a client's .myshopify.com address and name) goes to Claude Code on a DTJ laptop, "
                    "which makes, links and releases the seven DTJ app copies and sends seven Install buttons in Telegram."),
    "sticky": ("## Add a client shop (/addshop)\n"
               "Started by the Telegram bot when an admin sends **/addshop name.myshopify.com Client Name**.\n\n"
               "The run pauses at **Wait for Claude Code: Add Shop**. A Claude Code session in the dtj-agency-automation folder (listening, or "
               "told \"handle the Claude Code trigger in n8n\") reads **Request for Claude Code: Add Shop**, runs add_shop.py (the seven app "
               "copies, the install service, the Install buttons in Telegram) and answers here. No theme or store change happens in this "
               "workflow: each install is a tap by someone logged in to that shop.\n\n"
               "Source in git: `n8n/store-factory/` and `services/install-catcher/tools/add_shop.py`."),
}


def code(file: str) -> str:
    return (HERE / file).read_text(encoding="utf-8")


def code_nodes(cfg: dict) -> dict[str, str]:
    """node name -> its .js file"""
    return {f"Request for Claude Code: {cfg['step']}": cfg["code"]["request"], f"Claude Code Reply: {cfg['step']}": cfg["code"]["reply"],
            "Tell the Requester": cfg["code"]["tell"]}


def handoff_code(cfg: dict) -> str:
    """From the Telegram Bot -> Request for Claude Code -> Wait (resume webhook) -> Claude Code Reply -> Tell the Requester -> Send Result."""
    names = code_nodes(cfg)
    request, reply = (n for n in names if n.startswith("Request")), (n for n in names if n.startswith("Claude Code Reply"))
    code_node = lambda var, name, pos: (  # noqa: E731
        f"const {var} = node({{ type: 'n8n-nodes-base.code', version: 2, config: {{ name: {json.dumps(name)}, position: {pos}, "
        f"parameters: {{ mode: 'runOnceForAllItems', language: 'javaScript', jsCode: {json.dumps(code(names[name]))} }} }} }});\n")
    return (
        "import { workflow, node, trigger, sticky, expr, newCredential } from '@n8n/workflow-sdk';\n\n"
        "const fromBot = trigger({ type: 'n8n-nodes-base.executeWorkflowTrigger', version: 1.2, config: { name: 'From the Telegram Bot', "
        "position: [0, 0], parameters: { inputSource: 'workflowInputs', workflowInputs: { values: "
        + json.dumps([{"name": k, "type": "string"} for k in cfg["inputs"]]) + " } } } });\n"
        + code_node("request", next(request), "[240, 0]")
        + f"const wait = node({{ type: 'n8n-nodes-base.wait', version: 1.1, config: {{ name: {json.dumps('Wait for Claude Code: ' + cfg['step'])}, "
          f"position: [480, 0], parameters: {{ resume: 'webhook', httpMethod: 'POST', limitWaitTime: true, resumeAmount: {int(cfg['days'])}, "
          "resumeUnit: 'days', options: {} } } });\n"
        + code_node("reply", next(reply), "[720, 0]")
        + code_node("tell", "Tell the Requester", "[960, 0]")
        + "const send = node({ type: 'n8n-nodes-base.telegram', version: 1.2, config: { name: 'Send Result', position: [1200, 0], "
          "onError: 'continueRegularOutput', parameters: { resource: 'message', operation: 'sendMessage', chatId: expr('{{ $json.chat_id }}'), "
          f"text: expr('{{{{ $json.text }}}}'), additionalFields: {json.dumps(SEND_FIELDS)} }}, "
          f"credentials: {{ telegramApi: newCredential({json.dumps(CREDENTIAL)}) }} }} }});\n"
        + f"const about = sticky({json.dumps(cfg['sticky'])}, [fromBot, request, wait], {{ color: 5, position: [-40, -360], width: 760, height: 320 }});\n\n"
        f"export default workflow({json.dumps(cfg['slug'])}, {json.dumps(cfg['name'])})\n"
        "  .add(fromBot).to(request).to(wait).to(reply).to(tell).to(send)\n"
        "  .add(about);\n"
    )


def sdk_code() -> str:
    return handoff_code(ADD_SHOP)


def deploy(cfg: dict, argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sdk, nodes, name = handoff_code(cfg), code_nodes(cfg), cfg["name"]
    if args.dry_run:
        print(sdk)
        return 0
    try:
        found = [w for w in call("search_workflows", {"query": name}).get("data", []) if w.get("name") == name]
        if found:
            wf_id = found[0]["id"]
            ops = [{"type": "updateNodeParameters", "nodeName": n, "parameters": {"jsCode": code(f)}} for n, f in nodes.items()]
            print("exists: refreshing its code nodes", call("update_workflow", {"workflowId": wf_id, "operations": ops}).get("appliedOperations"))
        else:
            check = call("validate_workflow", {"code": sdk})
            print("validate:", json.dumps(check)[:800])
            if check.get("valid") is False or check.get("errors"):
                return 1
            made = call("create_workflow_from_code", {"code": sdk, "description": cfg["description"], "versionName": cfg["version"]})
            print("created:", json.dumps(made)[:600])
            wf_id = made.get("workflowId") or made.get("id")
        creds = [c for c in call("list_credentials", {}).get("data", []) if c.get("name") == CREDENTIAL and c.get("type") == "telegramApi"]
        if creds:
            print("Telegram credential:", call("update_workflow", {"workflowId": wf_id, "operations": [
                {"type": "setNodeCredential", "nodeName": "Send Result", "credentialKey": "telegramApi", "credentialId": creds[0]["id"],
                 "credentialName": CREDENTIAL}]}).get("appliedOperations"))
        else:
            print(f"no Telegram API credential named '{CREDENTIAL}' yet: Send Result has none until it exists (setup_n8n.py --apply)")
        after = call("get_workflow_details", {"workflowId": wf_id})["workflow"]
    except (urllib.error.URLError, RuntimeError, OSError) as exc:
        print(f"not deployed: {exc}", file=sys.stderr)
        return 1
    live = {n["name"]: n for n in after["nodes"]}
    mismatched = [n for n, f in nodes.items() if live.get(n, {}).get("parameters", {}).get("jsCode") != code(f)]
    export = {k: after.get(k) for k in ("id", "name", "description", "nodes", "connections", "settings") if k in after}
    (HERE / cfg["export"]).write_text(json.dumps(export, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"workflow {wf_id}: {len(live)} nodes; code identical to the files: {not mismatched} {mismatched or ''}; "
          f"active: {after.get('active')}; export saved: {cfg['export']}")
    return 0 if not mismatched else 1


def main(argv=None) -> int:
    return deploy(ADD_SHOP, argv)


if __name__ == "__main__":
    raise SystemExit(main())
