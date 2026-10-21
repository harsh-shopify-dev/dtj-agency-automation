"""Deploy "Store Factory: Brand Copy" to DTJ's n8n: the Approve tap on a store job's brand copy runs the copy, with no laptop step
(Harsh, 21 Oct 2026: "all this steps must be done in the telegram bot").

    python n8n/store-factory/deploy_brand_copy.py --dry-run     print the generated workflow code, change nothing
    python n8n/store-factory/deploy_brand_copy.py               create it (or refresh its code nodes when it exists)

From the Telegram Bot (job, approved_by, chat_id) -> Copy Step Body -> Copy Step (install service POST /copy, op "step", the bot's
key) -> Copy Progress -> Copy Finished?
    yes -> Send Result (Telegram "DTJ Page Bot")
    no  -> Pause (2 s) -> Copy Step Body (the next items)
The install service (services/install-catcher/src/copy.js) does every store write through DTJ Store Builder, from the plan the
store job kept there; the Approve tap's name goes with every step. The code nodes are brand_copy_step.js and brand_copy_progress.js
(run in Node by test_bot_nodes.py), sent byte for byte; the export is brand_copy.workflow.json. Created UNPUBLISHED.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy_add_shop import CREDENTIAL, SEND_FIELDS, code  # noqa: E402
from n8n_mcp import call  # noqa: E402

HERE = Path(__file__).resolve().parent
NAME = "Store Factory: Brand Copy"
KEY_CREDENTIAL = "DTJ Catcher Bot Key"  # Header Auth X-DTJ-Bot-Key (the catcher's BOT_KEY), already used by the bot's app switch
COPY_URL = "https://dtj-install-catcher.ultimateecomwithharsh.workers.dev/copy"
CODE_NODES = {"Copy Step Body": "brand_copy_step.js", "Copy Progress": "brand_copy_progress.js"}
DESCRIPTION = ("Store factory: a brand copy's Approve tap in Telegram runs the copy through the install service (DTJ Store Builder), "
               "step by step, then tells the person who tapped.")
STICKY = ("## Brand copy (one Approve tap per import)\n"
          "Started by the Telegram bot when someone taps **Approve** under a store job's brand copy. Every step asks the install "
          "service to copy the next few products, collections or policy pages from the plan the store job kept there; the person's "
          "name goes with every step. Nothing the store has is changed or deleted (src/copy.js). Source in git: `n8n/store-factory/`.")


def sdk_code() -> str:
    code_node = lambda var, name, pos: (  # noqa: E731
        f"const {var} = node({{ type: 'n8n-nodes-base.code', version: 2, config: {{ name: {json.dumps(name)}, position: {pos}, "
        f"parameters: {{ mode: 'runOnceForAllItems', language: 'javaScript', jsCode: {json.dumps(code(CODE_NODES[name]))} }} }} }});\n")
    return (
        "import { workflow, node, trigger, sticky, ifElse, expr, newCredential } from '@n8n/workflow-sdk';\n\n"
        "const fromBot = trigger({ type: 'n8n-nodes-base.executeWorkflowTrigger', version: 1.2, config: { name: 'From the Telegram Bot', "
        "position: [0, 0], parameters: { inputSource: 'workflowInputs', workflowInputs: { values: "
        + json.dumps([{"name": k, "type": "string"} for k in ("job", "approved_by", "chat_id")]) + " } } } });\n"
        + code_node("stepBody", "Copy Step Body", "[240, 0]")
        + "const copyStep = node({ type: 'n8n-nodes-base.httpRequest', version: 4.2, config: { name: 'Copy Step', position: [480, 0], "
          f"parameters: {{ method: 'POST', url: {json.dumps(COPY_URL)}, authentication: 'genericCredentialType', genericAuthType: 'httpHeaderAuth', "
          "sendHeaders: true, headerParameters: { parameters: [{ name: 'User-Agent', value: 'dtj-n8n-bot/1' }] }, "
          "sendBody: true, contentType: 'json', specifyBody: 'json', jsonBody: '={{ JSON.stringify($json.body) }}', "
          "options: { response: { response: { fullResponse: true, neverError: true } }, timeout: 60000 } }, "
          f"credentials: {{ httpHeaderAuth: newCredential({json.dumps(KEY_CREDENTIAL)}) }} }} }});\n"
        + code_node("progress", "Copy Progress", "[720, 0]")
        + "const finished = ifElse({ version: 2.2, config: { name: 'Copy Finished?', position: [960, 0], parameters: { conditions: { "
          "options: { caseSensitive: true, leftValue: '', typeValidation: 'loose' }, conditions: [{ leftValue: expr('{{ $json.finished }}'), "
          "rightValue: '', operator: { type: 'boolean', operation: 'true', singleValue: true } }], combinator: 'and' } } } });\n"
        + "const send = node({ type: 'n8n-nodes-base.telegram', version: 1.2, config: { name: 'Send Result', position: [1200, -120], "
          "onError: 'continueRegularOutput', parameters: { resource: 'message', operation: 'sendMessage', chatId: expr('{{ $json.chat_id }}'), "
          f"text: expr('{{{{ $json.text }}}}'), additionalFields: {json.dumps(SEND_FIELDS)} }}, "
          f"credentials: {{ telegramApi: newCredential({json.dumps(CREDENTIAL)}) }} }} }});\n"
        + "const pause = node({ type: 'n8n-nodes-base.wait', version: 1.1, config: { name: 'Pause', position: [1200, 120], "
          "parameters: { resume: 'timeInterval', amount: 2, unit: 'seconds' } } });\n"
        + f"const about = sticky({json.dumps(STICKY)}, [fromBot, stepBody, copyStep], {{ color: 5, position: [-40, -360], width: 760, height: 300 }});\n\n"
        "export default workflow('store-factory-brand-copy', " + json.dumps(NAME) + ")\n"
        "  .add(fromBot).to(stepBody).to(copyStep).to(progress).to(finished.onTrue(send).onFalse(pause.to(stepBody)))\n"
        "  .add(about);\n"
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sdk = sdk_code()
    if args.dry_run:
        print(sdk)
        return 0
    try:
        found = [w for w in call("search_workflows", {"query": NAME}).get("data", []) if w.get("name") == NAME]
        if found:
            wf_id = found[0]["id"]
            ops = [{"type": "updateNodeParameters", "nodeName": n, "parameters": {"jsCode": code(f)}} for n, f in CODE_NODES.items()]
            print("exists: refreshing its code nodes", call("update_workflow", {"workflowId": wf_id, "operations": ops}).get("appliedOperations"))
        else:
            check = call("validate_workflow", {"code": sdk})
            print("validate:", json.dumps(check)[:800])
            if check.get("valid") is False or check.get("errors"):
                return 1
            made = call("create_workflow_from_code", {"code": sdk, "description": DESCRIPTION, "versionName": "Brand copy from the Approve tap"})
            print("created:", json.dumps(made)[:400])
            wf_id = made.get("workflowId") or made.get("id")
        creds = {(c.get("name"), c.get("type")): c["id"] for c in call("list_credentials", {}).get("data", [])}
        ops = []
        if (CREDENTIAL, "telegramApi") in creds:
            ops.append({"type": "setNodeCredential", "nodeName": "Send Result", "credentialKey": "telegramApi",
                        "credentialId": creds[(CREDENTIAL, "telegramApi")], "credentialName": CREDENTIAL})
        if (KEY_CREDENTIAL, "httpHeaderAuth") in creds:
            ops.append({"type": "setNodeCredential", "nodeName": "Copy Step", "credentialKey": "httpHeaderAuth",
                        "credentialId": creds[(KEY_CREDENTIAL, "httpHeaderAuth")], "credentialName": KEY_CREDENTIAL})
        if ops:
            print("credentials:", call("update_workflow", {"workflowId": wf_id, "operations": ops}).get("appliedOperations"))
        after = call("get_workflow_details", {"workflowId": wf_id})["workflow"]
    except (urllib.error.URLError, RuntimeError, OSError) as exc:
        print(f"not deployed: {exc}", file=sys.stderr)
        return 1
    live = {n["name"]: n for n in after["nodes"]}
    mismatched = [n for n, f in CODE_NODES.items() if live.get(n, {}).get("parameters", {}).get("jsCode") != code(f)]
    export = {k: after.get(k) for k in ("id", "name", "description", "nodes", "connections", "settings") if k in after}
    (HERE / "brand_copy.workflow.json").write_text(json.dumps(export, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"workflow {wf_id}: {len(live)} nodes; code identical to the files: {not mismatched} {mismatched or ''}; "
          f"active: {after.get('active')}; export saved: brand_copy.workflow.json")
    return 0 if not mismatched else 1


if __name__ == "__main__":
    raise SystemExit(main())
