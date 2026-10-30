"""Deploy "Reel: Find Diwali Campaigns" to DTJ's n8n (Harsh, 30 Oct 2026: an Apify node finds 2-3 Diwali campaigns on Instagram, a person
checks them and gives the go-ahead to make a similar video for the brand):

    python n8n/reel-engine/deploy_find_campaigns.py --dry-run     print the generated code, change nothing
    python n8n/reel-engine/deploy_find_campaigns.py               create it (unpublished), attach the "DTJ Apify" credential

Find Diwali Campaigns (form) -> Plan the Search -> Find on Instagram (Apify) -> Pick the Best -> Show the Results (the form's last page).
The token lives only in n8n's credential "DTJ Apify". Each search is capped at 100 results and $0.30. Nothing is posted or downloaded.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "store-factory"))

NAME = "Reel: Find Diwali Campaigns"
APIFY = "DTJ Apify"
NOTES = {
    "Find Diwali Campaigns": "You type what the brand sells, like watches, and how many results you want.",
    "Plan the Search": "Turns your word into Diwali hashtags to search on Instagram.",
    "Find on Instagram (Apify)": "Apify searches those hashtags on Instagram and brings back Reels. Costs a few cents, never more than 30 cents a search.",
    "Pick the Best": "Keeps Diwali Reels and removes comedy and memes, one per account. Reels about your product come first, then brand campaigns, then the most viewed.",
    "Show the Results": "Shows you the best results (10 unless you ask for fewer) with links. You check them and tell Claude which one to make.",
}


def workflow_code() -> str:
    plan, read = (json.dumps((HERE / f).read_text(encoding="utf-8")) for f in ("find_plan.js", "find_read.js"))
    fields = [{"fieldName": "niche", "fieldLabel": "What does the brand sell?", "fieldType": "text", "requiredField": True, "placeholder": "watches"},
              {"fieldName": "count", "fieldLabel": "How many results? (default 10)", "fieldType": "text", "requiredField": False}]
    url = ("={{ 'https://api.apify.com/v2/acts/' + $json.actor.replace('/', '~') + '/run-sync-get-dataset-items?timeout=' "
           "+ $json.timeout_s + '&maxItems=' + $json.max_items + '&maxTotalChargeUsd=' + $json.max_usd }}")

    def note(n: str) -> str:
        return f"notes: {json.dumps(NOTES[n])}, notesInFlow: true"

    return (
        "import { workflow, node, trigger, expr, newCredential } from '@n8n/workflow-sdk';\n\n"
        "const form = trigger({ type: 'n8n-nodes-base.formTrigger', version: 2.6, config: { name: \"Find Diwali Campaigns\", position: [0, 0], "
        f"{note('Find Diwali Campaigns')}, parameters: {{ authentication: 'n8nUserAuth', formTitle: 'Find Diwali campaigns on Instagram', "
        f"formFields: {{ values: {json.dumps(fields)} }}, responseMode: 'lastNode', options: {{ appendAttribution: false, path: 'dtj-find-diwali' }} }} }} }});\n"
        "const plan = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: \"Plan the Search\", position: [240, 0], "
        f"{note('Plan the Search')}, parameters: {{ mode: 'runOnceForAllItems', language: 'javaScript', jsCode: {plan} }} }} }});\n"
        "const apify = node({ type: 'n8n-nodes-base.httpRequest', version: 4.2, config: { name: \"Find on Instagram (Apify)\", position: [480, 0], "
        f"{note('Find on Instagram (Apify)')}, onError: 'continueRegularOutput', parameters: {{ method: 'POST', url: {json.dumps(url)}, "
        "authentication: 'genericCredentialType', genericAuthType: 'httpHeaderAuth', sendBody: true, contentType: 'json', specifyBody: 'json', "
        "jsonBody: '={{ JSON.stringify($json.input) }}', options: { response: { response: { fullResponse: true, neverError: true } }, timeout: 300000 } }, "
        f"credentials: {{ httpHeaderAuth: newCredential({json.dumps(APIFY)}) }} }} }});\n"
        "const read = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: \"Pick the Best\", position: [720, 0], "
        f"{note('Pick the Best')}, parameters: {{ mode: 'runOnceForAllItems', language: 'javaScript', jsCode: {read} }} }} }});\n"
        "const show = node({ type: 'n8n-nodes-base.form', version: 2.3, config: { name: \"Show the Results\", position: [960, 0], "
        f"{note('Show the Results')}, parameters: {{ operation: 'completion', respondWith: 'showText', responseText: expr('{{{{ $json.html }}}}') }} }} }});\n\n"
        f"export default workflow('reel-find-diwali', {json.dumps(NAME)})\n"
        "  .add(form).to(plan).to(apify).to(read).to(show);\n"
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    code = workflow_code()
    if a.dry_run:
        print(code)
        return 0
    from n8n_mcp import PROJECT, call  # noqa: PLC0415 - needs the n8n token; --dry-run does not
    try:
        print("valid:", json.dumps(call("validate_workflow", {"code": code}))[:400])
        hits = [w for w in call("search_workflows", {"query": NAME}).get("data", []) if w.get("name") == NAME and not w.get("isArchived")]
        if hits:
            wf_id = hits[0]["id"]
            print(f"{NAME}: already there ({wf_id}); delete or update it by hand")
        else:
            made = call("create_workflow_from_code", {"code": code, "description": "An Apify node finds Diwali Reels on Instagram; a person checks them.", "projectId": PROJECT})
            wf_id = made.get("workflowId") or made.get("id")
            print(f"{NAME}: created ({wf_id}), unpublished")
        cred = [c for c in call("list_credentials", {}).get("data", []) if c.get("name") == APIFY]
        if not cred:
            print(f"no credential named {APIFY}")
            return 1
        call("update_workflow", {"workflowId": wf_id, "operations": [{"type": "setNodeCredential", "nodeName": "Find on Instagram (Apify)",
             "credentialKey": "httpHeaderAuth", "credentialId": cred[0]["id"], "credentialName": APIFY}]})
        print("credential attached")
    except (urllib.error.URLError, RuntimeError, OSError) as exc:
        print(f"not deployed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
