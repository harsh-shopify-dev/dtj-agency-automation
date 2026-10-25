"""Deploy "Reel Factory: Find References" to DTJ's n8n: reference videos for the reel factory, found with Apify (Instagram reels,
Pinterest videos, Meta Ad Library video ads), saved in dtj_reel_library without duplicates, and sent to Telegram with Keep / Skip.

    python n8n/reel-factory/deploy_find_refs.py --dry-run     print the generated workflow code, change nothing
    python n8n/reel-factory/deploy_find_refs.py               create the data tables and the workflow (or refresh its code nodes)
    python n8n/reel-factory/deploy_find_refs.py --publish     the same, then publish it (turns on both schedules; only after a
                                                              manual test passed)

From the Telegram Bot (query, sources, limit, requested_by, chat_id: the reel bot's /refs; for an audience scan
    mode "audience", audience, hashtags, creators, limit) ─┐
Every Monday 9:00 (the active rows of dtj_reel_watchlist and dtj_reel_audiences) ─┴> Load Watchlist -> Load Bot Users
    -> Load Audiences -> Plan the Searches -> Anything to Search?
        yes -> Ask Apify (HTTP, credential "DTJ Apify") -> Read the Results -> Only New Links (link_key not yet in dtj_reel_library)
               -> Pick the New Ones -> Anything New? -> yes: Save New References -> Write the Digest / no: Write the Digest
               -> Is It the Summary? -> Send the Summary / Send a Reference (Keep / Skip, "a:refs-<row id>:keep:<n>")
        no  -> Is It the Summary? -> Send the Summary (what could not be searched)
An audience scan (Harsh, 25 Oct 2026) saves the top reels of the audience's hashtags and creators (source "audience": views,
likes, comments, the creator's followers, views per follower, comments per view, audio name) and India's trending Reels audio
(source "trending_audio") with the audience on every row, and sends one short summary without buttons.
Every 15 Minutes -> Load the Taps (dtj_bot_answers, job refs-*) -> Match the Taps -> Record the Choice (keep yes / no, kept_by)
The reel factory has its own Telegram bot (Harsh, 25 Oct 2026): the digest goes out through the n8n credential "DTJ Reel Bot",
and that bot's workflow "Reel Factory: Telegram Bot" saves the taps in dtj_bot_answers (n8n/store-factory/bot_ask.py format, job
refs-<row id>, key keep); this workflow never touches a bot workflow.
The Apify token lives only in the n8n credential "DTJ Apify" (Header Auth, Authorization: Bearer <token>) that Harsh makes in the
n8n UI; this script attaches it when it exists. The code nodes are the refs_*.js files next to this script (run in Node by
test_find_refs_nodes.py), sent byte for byte; the live workflow is read back, compared and exported to find_refs.workflow.json.
Created UNPUBLISHED (the bot's /refs works through "Execute Workflow" either way; the schedules run only once published).
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

NAME = "Reel Factory: Find References"
WATCHLIST, LIBRARY, AUDIENCES = "dtj_reel_watchlist", "dtj_reel_library", "dtj_reel_audiences"
USERS, ANSWERS = "dtj_bot_users", "dtj_bot_answers"   # made by the store factory (setup_n8n.py)
CREDENTIAL = "DTJ Reel Bot"   # the reel factory's own Telegram bot (token pasted by Harsh in n8n), not the store bot
APIFY = "DTJ Apify"           # Header Auth: Authorization = Bearer <Apify token>; made by Harsh in the n8n UI, never in a file
TABLES = json.loads((HERE / "find_refs_tables.json").read_text(encoding="utf-8"))
CODE_NODES = {"Plan the Searches": "refs_plan.js", "Read the Results": "refs_read.js", "Pick the New Ones": "refs_pick_new.js",
              "Write the Digest": "refs_digest.js", "Match the Taps": "refs_taps.js"}
INPUTS = ("query", "sources", "limit", "requested_by", "chat_id", "mode", "audience", "hashtags", "creators")
SEND_FIELDS = {"appendAttribution": False, "parse_mode": "HTML", "disable_web_page_preview": True}
DESCRIPTION = ("Reel factory: reference videos via Apify (Instagram reels, Pinterest videos, Meta Ad Library video ads) for /refs and "
               "a weekly watchlist scan -> dtj_reel_library (no duplicates) -> Telegram Keep / Skip; taps set keep.")
STICKY = ("## Reel factory: find references\n"
          "**/refs** in the Telegram bot (or the weekly scan of **dtj_reel_watchlist**, Mondays 9:00) asks Apify for reference "
          "videos: Instagram reels of a handle or hashtag, Pinterest videos for a search, Meta Ad Library video ads (India, active, "
          "longest running first). New ones go to **dtj_reel_library** and to Telegram with Keep / Skip; a tap sets keep = yes / no "
          "(every 15 minutes).\n\n"
          "Apify token: only in the credential **DTJ Apify** (Header Auth, name `Authorization`, value `Bearer <token>`). "
          "Costs: at most `limit` results per source (10 max) and a charge cap per call. Source in git: `n8n/reel-factory/`.")


def table_ids() -> dict[str, str]:
    """Every table this workflow reads or writes: the two reel tables are made (or completed) here, the bot's two must exist."""
    have = {t["name"]: t for t in call("search_data_tables", {"query": "dtj_", "limit": 100}).get("data", [])}
    ids = {}
    for name, spec in TABLES.items():
        cols = spec["columns"]
        if name in have:
            live = {c["name"] for c in have[name].get("columns", [])}
            missing = [c for c in cols if c["name"] not in live]
            for c in missing:
                call("add_data_table_column", {"dataTableId": have[name]["id"], "projectId": PROJECT, "name": c["name"], "type": c["type"]})
            print(f"table {name}: exists ({have[name]['id']}){'; added ' + str([c['name'] for c in missing]) if missing else ''}")
            ids[name] = have[name]["id"]
            continue
        made = call("create_data_table", {"projectId": PROJECT, "name": name, "columns": cols})
        ids[name] = made.get("id") or (made.get("dataTable") or {}).get("id")
        if not ids[name]:
            raise RuntimeError(f"create_data_table gave no id: {json.dumps(made)[:300]}")
        print(f"table {name}: created ({ids[name]})")
    for name in (USERS, ANSWERS):
        if name not in have:
            raise RuntimeError(f"table {name} is missing: run n8n/store-factory/setup_n8n.py --apply first")
        ids[name] = have[name]["id"]
    return ids


def sdk_code(ids: dict[str, str]) -> str:
    js = {name: json.dumps((HERE / f).read_text(encoding="utf-8")) for name, f in CODE_NODES.items()}
    rl = lambda t: f"{{ __rl: true, mode: 'list', value: '{ids[t]}', cachedResultName: '{t}' }}"  # noqa: E731
    lib_cols = TABLES[LIBRARY]["columns"]

    def schema(cols):
        return json.dumps([{"id": c["name"], "displayName": c["name"], "required": False, "defaultMatch": False, "display": True,
                            "type": c["type"], "canBeUsedToMatch": True} for c in cols])
    save_values = json.dumps({c["name"]: f"={{{{ $json.{c['name']} }}}}" for c in lib_cols})
    keep_cols = [c for c in lib_cols if c["name"] in ("keep", "kept_by", "kept_at")]
    keep_values = json.dumps({c["name"]: f"={{{{ $json.{c['name']} }}}}" for c in keep_cols})

    def code_node(var, name, pos):
        return (f"const {var} = node({{ type: 'n8n-nodes-base.code', version: 2, config: {{ name: {json.dumps(name)}, position: {pos}, "
                f"parameters: {{ mode: 'runOnceForAllItems', language: 'javaScript', jsCode: {js[name]} }} }} }});\n")

    def if_node(var, name, pos, left, op):
        return (f"const {var} = ifElse({{ version: 2.2, config: {{ name: {json.dumps(name)}, position: {pos}, parameters: {{ conditions: {{ "
                "options: { caseSensitive: true, leftValue: '', typeValidation: 'loose' }, "
                f"conditions: [{{ leftValue: expr({json.dumps(left)}), rightValue: '', operator: {op} }}], combinator: 'and' }} }} }} }});\n")
    not_empty = "{ type: 'string', operation: 'notEmpty', singleValue: true }"
    is_true = "{ type: 'boolean', operation: 'true', singleValue: true }"

    def send_node(var, name, pos, buttons):
        keyboard = ("replyMarkup: 'inlineKeyboard', inlineKeyboard: { rows: [{ row: { buttons: ["
                    "{ text: 'Keep', additionalFields: { callback_data: '={{ $json.keep_data }}' } }, "
                    "{ text: 'Skip', additionalFields: { callback_data: '={{ $json.skip_data }}' } }] } }] }, ") if buttons else ""
        fields = dict(SEND_FIELDS, disable_web_page_preview=not buttons)   # a reference shows the post's preview
        return (f"const {var} = node({{ type: 'n8n-nodes-base.telegram', version: 1.2, config: {{ name: {json.dumps(name)}, position: {pos}, "
                "onError: 'continueRegularOutput', parameters: { resource: 'message', operation: 'sendMessage', "
                f"chatId: expr('{{{{ $json.chat_id }}}}'), text: expr('{{{{ $json.text }}}}'), {keyboard}additionalFields: {json.dumps(fields)} }}, "
                f"credentials: {{ telegramApi: newCredential({json.dumps(CREDENTIAL)}) }} }} }});\n")
    apify_url = ("={{ 'https://api.apify.com/v2/acts/' + $json.actor.replace('/', '~') + '/run-sync-get-dataset-items?timeout=' "
                 "+ $json.timeout_s + '&maxItems=' + $json.max_items + '&maxTotalChargeUsd=' + $json.max_usd }}")
    inputs = ", ".join(f"{{ name: '{n}', type: 'string' }}" for n in INPUTS)
    return (
        "import { workflow, node, trigger, sticky, ifElse, expr, newCredential } from '@n8n/workflow-sdk';\n\n"
        "const fromBot = trigger({ type: 'n8n-nodes-base.executeWorkflowTrigger', version: 1.2, config: { name: 'From the Telegram Bot', "
        f"position: [0, 0], parameters: {{ inputSource: 'workflowInputs', workflowInputs: {{ values: [{inputs}] }} }} }} }});\n"
        "const weekly = trigger({ type: 'n8n-nodes-base.scheduleTrigger', version: 1.2, config: { name: 'Every Monday 9:00', "
        "position: [0, 200], parameters: { rule: { interval: [{ field: 'weeks', weeksInterval: 1, triggerAtDay: [1], triggerAtHour: 9, "
        "triggerAtMinute: 0 }] } } } });\n"
        "const loadWatch = node({ type: 'n8n-nodes-base.dataTable', version: 1.1, config: { name: 'Load Watchlist', position: [240, 100], "
        "executeOnce: true, alwaysOutputData: true, "
        f"parameters: {{ resource: 'row', operation: 'get', dataTableId: {rl(WATCHLIST)}, returnAll: true }} }} }});\n"
        "const loadUsers = node({ type: 'n8n-nodes-base.dataTable', version: 1.1, config: { name: 'Load Bot Users', position: [480, 100], "
        "executeOnce: true, alwaysOutputData: true, "
        f"parameters: {{ resource: 'row', operation: 'get', dataTableId: {rl(USERS)}, returnAll: true }} }} }});\n"
        + "const loadAud = node({ type: 'n8n-nodes-base.dataTable', version: 1.1, config: { name: 'Load Audiences', position: [600, 260], "
          "executeOnce: true, alwaysOutputData: true, "
          f"parameters: {{ resource: 'row', operation: 'get', dataTableId: {rl(AUDIENCES)}, returnAll: true }} }} }});\n"
        + code_node("plan", "Plan the Searches", "[720, 100]")
        + if_node("toSearch", "Anything to Search?", "[960, 100]", "{{ $json.actor }}", not_empty)
        + "const apify = node({ type: 'n8n-nodes-base.httpRequest', version: 4.2, config: { name: 'Ask Apify', position: [1200, 0], "
          "onError: 'continueRegularOutput', "
          f"parameters: {{ method: 'POST', url: {json.dumps(apify_url)}, authentication: 'genericCredentialType', genericAuthType: 'httpHeaderAuth', "
          "sendBody: true, contentType: 'json', specifyBody: 'json', jsonBody: '={{ JSON.stringify($json.input) }}', "
          "options: { response: { response: { fullResponse: true, neverError: true } }, timeout: 300000, "
          "batching: { batch: { batchSize: 1, batchInterval: 1000 } } } }, "
          f"credentials: {{ httpHeaderAuth: newCredential({json.dumps(APIFY)}) }} }} }});\n"
        + code_node("read", "Read the Results", "[1440, 0]")
        + "const onlyNew = node({ type: 'n8n-nodes-base.dataTable', version: 1.1, config: { name: 'Only New Links', position: [1680, 0], "
          "alwaysOutputData: true, "
          f"parameters: {{ resource: 'row', operation: 'rowNotExists', dataTableId: {rl(LIBRARY)}, matchType: 'allConditions', "
          f"filters: {{ conditions: {json.dumps(ONLY_NEW)} }} }} }} }});\n"
        + code_node("pick", "Pick the New Ones", "[1920, 0]")
        + if_node("anyNew", "Anything New?", "[2160, 0]", "{{ $json.url }}", not_empty)
        + "const save = node({ type: 'n8n-nodes-base.dataTable', version: 1.1, config: { name: 'Save New References', position: [2400, -100], "
          f"parameters: {{ resource: 'row', operation: 'insert', dataTableId: {rl(LIBRARY)}, "
          f"columns: {{ mappingMode: 'defineBelow', value: {save_values}, matchingColumns: [], schema: {schema(lib_cols)} }}, options: {{}} }} }} }});\n"
        + code_node("digest", "Write the Digest", "[2640, 0]")
        + if_node("isSummary", "Is It the Summary?", "[2880, 100]", "{{ $json.summary }}", is_true)
        + send_node("sendSummary", "Send the Summary", "[3120, 0]", False)
        + send_node("sendRef", "Send a Reference", "[3120, 200]", True)
        + "const every15 = trigger({ type: 'n8n-nodes-base.scheduleTrigger', version: 1.2, config: { name: 'Every 15 Minutes', "
          "position: [0, 500], parameters: { rule: { interval: [{ field: 'minutes', minutesInterval: 15 }] } } } });\n"
        + "const loadTaps = node({ type: 'n8n-nodes-base.dataTable', version: 1.1, config: { name: 'Load the Taps', position: [240, 500], "
          f"parameters: {{ resource: 'row', operation: 'get', dataTableId: {rl(ANSWERS)}, matchType: 'allConditions', "
          "filters: { conditions: [{ keyName: 'job', condition: 'like', keyValue: 'refs-%' }, { keyName: 'key', condition: 'eq', keyValue: 'keep' }] }, "
          "returnAll: true } } });\n"
        + code_node("taps", "Match the Taps", "[480, 500]")
        + "const record = node({ type: 'n8n-nodes-base.dataTable', version: 1.1, config: { name: 'Record the Choice', position: [720, 500], "
          f"parameters: {{ resource: 'row', operation: 'update', dataTableId: {rl(LIBRARY)}, matchType: 'allConditions', "
          "filters: { conditions: [{ keyName: 'id', condition: 'eq', keyValue: '={{ $json.row_id }}' }] }, "
          f"columns: {{ mappingMode: 'defineBelow', value: {keep_values}, matchingColumns: [], schema: {schema(keep_cols)} }} }} }} }});\n"
        + f"const about = sticky({json.dumps(STICKY)}, [fromBot, weekly, loadWatch], {{ color: 5, position: [-40, -420], width: 760, height: 380 }});\n\n"
        "export default workflow('reel-factory-find-references', " + json.dumps(NAME) + ")\n"
        "  .add(fromBot).to(loadWatch)\n"
        "  .add(weekly).to(loadWatch)\n"
        "  .add(loadWatch).to(loadUsers).to(loadAud).to(plan).to(toSearch.onTrue(apify.to(read.to(onlyNew.to(pick.to(anyNew.onTrue(save.to(digest)).onFalse(digest)))))).onFalse(isSummary))\n"
        "  .add(digest).to(isSummary.onTrue(sendSummary).onFalse(sendRef))\n"
        "  .add(every15).to(loadTaps).to(taps).to(record)\n"
        "  .add(about);\n"
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--publish", action="store_true", help="publish after the deploy (turns the two schedules on)")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.dry_run:
        print(sdk_code({t: f"<{t} id>" for t in (*TABLES, USERS, ANSWERS)}))
        return 0
    try:
        ids = table_ids()
        code = sdk_code(ids)
        found = [w for w in call("search_workflows", {"query": NAME}).get("data", []) if w.get("name") == NAME]
        if found:
            wf_id = found[0]["id"]
            ops = structure_ops(call("get_workflow_details", {"workflowId": wf_id})["workflow"], ids)
            ops += [{"type": "updateNodeParameters", "nodeName": n, "parameters": {"jsCode": (HERE / f).read_text(encoding="utf-8")}}
                    for n, f in CODE_NODES.items()]
            # n8n_mcp.call publishes after every update_workflow; an unpublished workflow stays unpublished unless --publish
            live_now = args.publish or found[0].get("active")
            res = call("update_workflow", {"workflowId": wf_id, "operations": ops}) if live_now else _update_unpublished(wf_id, ops)
            print("exists: refreshed its code nodes", json.dumps(res)[:300])
        else:
            check = call("validate_workflow", {"code": code})
            print("validate:", json.dumps(check)[:800])
            if check.get("valid") is False or check.get("errors"):
                return 1
            made = call("create_workflow_from_code", {"code": code, "description": DESCRIPTION, "projectId": PROJECT,
                                                      "versionName": "Find references: Apify -> library -> Keep / Skip"})
            print("created:", json.dumps(made)[:600])
            wf_id = made.get("workflowId") or made.get("id")
        creds = {(c.get("name"), c.get("type")): c["id"] for c in call("list_credentials", {}).get("data", [])}
        ops = bot_ops(call("get_workflow_details", {"workflowId": wf_id})["workflow"], creds.get((CREDENTIAL, "telegramApi")))
        if (CREDENTIAL, "telegramApi") not in creds:
            print(f"no Telegram credential named '{CREDENTIAL}' yet: make it in n8n (Credentials > Create > Telegram API; name "
                  f"'{CREDENTIAL}', the reel bot's token from BotFather), then run this script again")
        if (APIFY, "httpHeaderAuth") in creds:
            ops.append({"type": "setNodeCredential", "nodeName": "Ask Apify", "credentialKey": "httpHeaderAuth",
                        "credentialId": creds[(APIFY, "httpHeaderAuth")], "credentialName": APIFY})
        else:
            print(f"no Header Auth credential named '{APIFY}' yet: make it in n8n (Credentials > Create > Header Auth; name "
                  f"'{APIFY}', header name 'Authorization', value 'Bearer ' + the Apify token), then run this script again")
        if ops:
            live_now = args.publish or (found and found[0].get("active"))
            res = call("update_workflow", {"workflowId": wf_id, "operations": ops}) if live_now else _update_unpublished(wf_id, ops)
            print("credentials:", json.dumps(res)[:200])
        if args.publish:
            print("published:", json.dumps(call("publish_workflow", {"workflowId": wf_id}))[:200])
        after = call("get_workflow_details", {"workflowId": wf_id})["workflow"]
    except (urllib.error.URLError, RuntimeError, OSError) as exc:
        print(f"not deployed: {exc}", file=sys.stderr)
        return 1
    live = {n["name"]: n for n in after["nodes"]}
    mismatched = [n for n, f in CODE_NODES.items() if live.get(n, {}).get("parameters", {}).get("jsCode") != (HERE / f).read_text(encoding="utf-8")]
    export = {k: after.get(k) for k in ("id", "name", "description", "nodes", "connections", "settings") if k in after}
    (HERE / "find_refs.workflow.json").write_text(json.dumps(export, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"workflow {wf_id}: {len(live)} nodes; code identical to the files: {not mismatched} {mismatched or ''}; "
          f"active: {after.get('active')}; export saved: find_refs.workflow.json")
    return 0 if not mismatched else 1


SENDS = ("Send the Summary", "Send a Reference")
ONLY_NEW = [{"keyName": "link_key", "condition": "eq", "keyValue": "={{ $json.link_key }}"}]   # "<link>|<audience>" (refs_read.js)


def column_schema(cols: list[dict]) -> list[dict]:
    return [{"id": c["name"], "displayName": c["name"], "required": False, "defaultMatch": False, "display": True, "type": c["type"],
             "canBeUsedToMatch": True} for c in cols]


def structure_ops(wf: dict, ids: dict[str, str]) -> list[dict]:
    """Bring a workflow made by an earlier version of this script up to date without making a new one (its id stays, the reel bot
    calls it by id): the bot's inputs, "Load Audiences" before "Plan the Searches", the library's columns on "Save New References"
    and the link_key check on "Only New Links". Each step only when it is missing, so a second run changes nothing."""
    nodes = {n["name"]: n for n in wf.get("nodes", [])}
    ops = []
    want_inputs = [{"name": n, "type": "string"} for n in INPUTS]
    have_inputs = nodes.get("From the Telegram Bot", {}).get("parameters", {}).get("workflowInputs", {}).get("values", [])
    if [i.get("name") for i in have_inputs] != list(INPUTS):
        ops.append({"type": "setNodeParameter", "nodeName": "From the Telegram Bot", "path": "/workflowInputs/values", "value": want_inputs})
    if "Load Audiences" not in nodes:
        ops += [{"type": "addNode", "node": {"name": "Load Audiences", "type": "n8n-nodes-base.dataTable", "typeVersion": 1.1, "position": [600, 260],
                 "parameters": {"resource": "row", "operation": "get", "returnAll": True,
                                "dataTableId": {"__rl": True, "mode": "list", "value": ids[AUDIENCES], "cachedResultName": AUDIENCES}}}},
                {"type": "setNodeSettings", "nodeName": "Load Audiences", "settings": {"executeOnce": True, "alwaysOutputData": True}},
                {"type": "removeConnection", "source": "Load Bot Users", "target": "Plan the Searches"},
                {"type": "addConnection", "source": "Load Bot Users", "target": "Load Audiences"},
                {"type": "addConnection", "source": "Load Audiences", "target": "Plan the Searches"}]
    lib_cols = TABLES[LIBRARY]["columns"]
    have_cols = [c.get("id") for c in nodes.get("Save New References", {}).get("parameters", {}).get("columns", {}).get("schema", [])]
    if have_cols != [c["name"] for c in lib_cols]:
        ops.append({"type": "setNodeParameter", "nodeName": "Save New References", "path": "/columns", "value": {
            "mappingMode": "defineBelow", "value": {c["name"]: f"={{{{ $json.{c['name']} }}}}" for c in lib_cols}, "matchingColumns": [],
            "schema": column_schema(lib_cols)}})
    if nodes.get("Only New Links", {}).get("parameters", {}).get("filters", {}).get("conditions") != ONLY_NEW:
        ops.append({"type": "setNodeParameter", "nodeName": "Only New Links", "path": "/filters", "value": {"conditions": ONLY_NEW}})
    return ops


def bot_ops(wf: dict, cred_id: str | None) -> list[dict]:
    """The two Telegram nodes on the reel bot, and "Load the Taps" on its refs-* jobs. With the credential in n8n: attach it and switch
    the nodes on. Without it (Harsh has not made it yet) they are switched OFF: n8n fills an empty Telegram credential with any one it
    has (it gave them the store bot's, 25 Oct 2026), and a reference digest must never go out through the store bot."""
    nodes = {n["name"]: n for n in wf.get("nodes", [])}
    ops = []
    taps = nodes.get("Load the Taps", {}).get("parameters", {}).get("filters", {}).get("conditions", [])
    if taps and taps[0].get("keyValue") != "refs-%":
        ops.append({"type": "setNodeParameter", "nodeName": "Load the Taps", "path": "/filters/conditions/0/keyValue", "value": "refs-%"})
    for name in SENDS:
        if name not in nodes:
            continue
        if cred_id:
            ops += [{"type": "setNodeCredential", "nodeName": name, "credentialKey": "telegramApi", "credentialId": cred_id,
                     "credentialName": CREDENTIAL}, {"type": "setNodeDisabled", "nodeName": name, "disabled": False}]
        else:
            ops.append({"type": "setNodeDisabled", "nodeName": name, "disabled": True})
    return ops


def _update_unpublished(wf_id: str, ops: list[dict]) -> dict:
    """update_workflow without n8n_mcp.call's automatic publish (that is for workflows meant live): its inner call goes through the
    module's name `call`, which answers publish_workflow with a no-op for the length of this one update."""
    import n8n_mcp
    real = n8n_mcp.call

    def no_publish(tool, arguments, *a, **k):
        if tool == "publish_workflow":
            return {"activeVersionId": "not published (run with --publish after a manual test)"}
        return real(tool, arguments, *a, **k)
    n8n_mcp.call = no_publish
    try:
        return real("update_workflow", {"workflowId": wf_id, "operations": ops})
    finally:
        n8n_mcp.call = real


if __name__ == "__main__":
    raise SystemExit(main())
