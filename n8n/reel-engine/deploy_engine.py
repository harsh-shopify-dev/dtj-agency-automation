"""Deploy the multi-brand reel engine to DTJ's n8n (Harsh, 30 Oct 2026; spec docs/superpowers/specs/2026-10-30-multi-brand-reel-engine-design.md):

    python n8n/reel-engine/deploy_engine.py --dry-run                       print both workflows' code, change nothing
    python n8n/reel-engine/deploy_engine.py                                 create or refresh "Reel Engine"
    python n8n/reel-engine/deploy_engine.py --brand branda --name "Brand A" [--style cinematic]
                                                                            create "Reel: Brand A" (one per brand)

"Reel Engine" (shared by every brand), each stage one HTTP call to the engine on the VPS host (services/reel-engine), like
Champfuel's brand-engine /onepass:
  When called by a brand -> Start run -> 0 [NO AI] Take request -> 1 [GEMINI] Style card -> 2 [GEMINI] Script + scenes
  -> 3 [CHATGPT + CLAUDE] Scene pictures -> 4 [PERSON] Approve script + pictures -> Pictures answer?
       waiting -> Wait 1 min -> 4 | clips -> 5 [FLOW + CLAUDE] Clips -> 6 [NO AI] Edit -> 7 [PERSON] Approve final reel -> Final answer?
       pictures -> 3 | script -> 2                                waiting -> Wait 1 min -> 7 | done -> 8 [NO AI] Result | clips -> 5
The engine keeps the person's change (which scenes, the note); n8n only passes the loop counter it answers with.
A stage that fails answers 422: the run stops at that node and the person is told in Telegram; fix, then Retry the node.
"Reel: <Brand>": Run now / When called by Hermes -> Run settings (brand fixed) -> Reel Engine (waits for the reel).
Both are created UNPUBLISHED; publishing (and the engine service on the VPS) is a separate yes.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "store-factory"))

ENGINE = "http://172.16.1.1:8091"     # the engine on the VPS host, on n8n's Docker gateway (not public)
ENGINE_NAME = "Reel Engine"
HOURS_4 = 14400000                    # pictures and clips of a 10-scene reel on 2 vCPUs can outlast the usual hour
STICKY = ("## Reel Engine (every brand)\n"
          "Makes one reel for one brand, with a person watching. Gemini writes the script, ChatGPT draws the scenes, you approve them in "
          "Telegram, Google Flow makes the clips, Claude checks them, and the reel is edited for your final Approve. Nothing is posted.\n\n"
          "If a step stops, Telegram says why. Fix it, then click Retry on that step here.")


def _body(stage: str, extra: str = "", loop: bool = True) -> str:
    s = "$('Start run').first().json"
    return (f"={{{{ JSON.stringify({{ brand: {s}.brand, run: {s}.run, stage: '{stage}', {extra}"
            + ("loop: $json.loop || 0 " if loop else "") + "}) }}")


# What each node does, in the simplest words: shown on the node in n8n (Harsh, 30 Oct 2026).
NOTES = {
    "When called by a brand": "The reel starts here. A brand's workflow sends the brand name, the idea and who is watching.",
    "Start run": "Checks we have a brand, an idea and a person watching. Gives this reel its own run number.",
    "0 [NO AI] Take request": "Checks the brand has product photos and reference videos. Opens the Telegram chat for this reel. Stops if another reel is still running.",
    "1 [GEMINI] Style card": "Gemini watches the brand's reference videos and writes down their style. It does this once, and again only when new videos are added.",
    "2 [GEMINI] Script + scenes": "Gemini writes the script and splits it into scenes, from the brand brief, the style and your idea. Any claim not in the brand's facts is refused.",
    "3 [CHATGPT + CLAUDE] Scene pictures": "ChatGPT draws one picture for each scene. Claude scores each picture and asks for a new one if it is weak.",
    "4 [PERSON] Approve script + pictures": "Sends the script and pictures to Telegram. You tap Approve, or name the scenes to change, like: 3, 5: the diya is too small.",
    "Pictures answer?": "Reads your reply. No reply yet: wait. Approved: make the clips. Scenes named: redraw only those. About the words: rewrite the script.",
    "Wait 1 min (pictures)": "No reply yet, so it waits 1 minute and looks again. After 2 days with no reply the reel stops.",
    "5 [FLOW + CLAUDE] Clips": "Google Flow turns each approved picture into a video clip. Claude watches each clip and has bad ones made again. This step uses Flow credits.",
    "6 [NO AI] Edit": "Joins the clips into the final reel: cuts, music, captions and sound level.",
    "7 [PERSON] Approve final reel": "Sends the finished reel to Telegram. You tap Approve, or name the scenes to remake, like: 2: the pack wobbles.",
    "Final answer?": "Reads your reply. No reply yet: wait. Approved or a general note: finish. Scenes named: remake only those clips.",
    "Wait 1 min (final)": "No reply yet, so it waits 1 minute and looks again. After 2 days with no reply the reel stops.",
    "8 [NO AI] Result": "Finishes the reel. Says if it is ready or needs a look, where the file is and how many Flow credits it used. Nothing is posted.",
}


def _http(var: str, name: str, stage: str, pos: str, extra: str = "", loop: bool = True, timeout: int = 3600000) -> str:
    return (f"const {var} = node({{ type: 'n8n-nodes-base.httpRequest', version: 4.2, config: {{ name: {json.dumps(name)}, "
            f"position: {pos}, notes: {json.dumps(NOTES[name])}, notesInFlow: true, parameters: {{ method: 'POST', url: '{ENGINE}/stage', "
            f"sendBody: true, specifyBody: 'json', jsonBody: {json.dumps(_body(stage, extra, loop))}, "
            f"options: {{ timeout: {timeout} }} }} }} }});\n")


def _rule(key: str, left: str, values: tuple[str, ...]) -> dict:
    return {"outputKey": key, "conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
            "conditions": [{"leftValue": left, "operator": {"type": "string", "operation": "equals"}, "rightValue": v} for v in values],
            "combinator": "or"}}


def _switch(var: str, name: str, pos: str, rules: list[dict]) -> str:
    return (f"const {var} = switchCase({{ version: 3.2, config: {{ name: {json.dumps(name)}, position: {pos}, "
            f"notes: {json.dumps(NOTES[name])}, notesInFlow: true, "
            f"parameters: {{ rules: {{ values: {json.dumps(rules)} }}, options: {{}} }} }} }});\n")


def _wait(var: str, name: str, pos: str) -> str:
    return (f"const {var} = node({{ type: 'n8n-nodes-base.wait', version: 1.1, config: {{ name: {json.dumps(name)}, position: {pos}, "
            f"notes: {json.dumps(NOTES[name])}, notesInFlow: true, "
            "parameters: { resume: 'timeInterval', amount: 1, unit: 'minutes' } } });\n")


def engine_code() -> str:
    js = json.dumps((HERE / "start_run.js").read_text(encoding="utf-8"))
    waiting = "={{ String($json.waiting) }}"
    nxt = "={{ $json.next }}"
    start_fields = ("style: $('Start run').first().json.style, request: $('Start run').first().json.request, "
                    "language: $('Start run').first().json.language, chat: $('Start run').first().json.chat, "
                    "watcher: $('Start run').first().json.watcher, requested_by: $('Start run').first().json.requested_by, ")
    return (
        "import { workflow, node, trigger, sticky, switchCase } from '@n8n/workflow-sdk';\n\n"
        "const called = trigger({ type: 'n8n-nodes-base.executeWorkflowTrigger', version: 1.1, config: { name: 'When called by a brand', "
        f"position: [0, 200], notes: {json.dumps(NOTES['When called by a brand'])}, "
        "notesInFlow: true, parameters: { inputSource: 'passthrough' } } });\n"
        "const startRun = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Start run', position: [240, 200], "
        f"notes: {json.dumps(NOTES['Start run'])}, notesInFlow: true, "
        f"parameters: {{ mode: 'runOnceForAllItems', language: 'javaScript', jsCode: {js} }} }} }});\n"
        + _http("take", "0 [NO AI] Take request", "take", "[480, 200]", start_fields, loop=False)
        + _http("card", "1 [GEMINI] Style card", "style_card", "[720, 200]", loop=False)
        + _http("script", "2 [GEMINI] Script + scenes", "script", "[960, 200]")
        + _http("pictures", "3 [CHATGPT + CLAUDE] Scene pictures", "pictures", "[1200, 200]", timeout=HOURS_4)
        + _http("reviewPics", "4 [PERSON] Approve script + pictures", "review", "[1440, 200]", "gate: 'pictures', ")
        + _switch("picAnswer", "Pictures answer?", "[1680, 200]",
                  [_rule("waiting", waiting, ("true",)), _rule("approved", nxt, ("clips",)), _rule("redraw", nxt, ("pictures",)),
                   _rule("rewrite", nxt, ("script",))])
        + _wait("waitPics", "Wait 1 min (pictures)", "[1680, 420]")
        + _http("clips", "5 [FLOW + CLAUDE] Clips", "clips", "[1920, 200]", timeout=HOURS_4)
        + _http("edit", "6 [NO AI] Edit", "edit", "[2160, 200]")
        + _http("reviewFinal", "7 [PERSON] Approve final reel", "review", "[2400, 200]", "gate: 'final', ")
        + _switch("finalAnswer", "Final answer?", "[2640, 200]",
                  [_rule("waiting", waiting, ("true",)), _rule("done", nxt, ("save", "result")), _rule("clips", nxt, ("clips",))])
        + _wait("waitFinal", "Wait 1 min (final)", "[2640, 420]")
        + _http("result", "8 [NO AI] Result", "result", "[2880, 200]")
        + f"const about = sticky({json.dumps(STICKY)}, [called, startRun, take], {{ color: 5, position: [-40, -260], width: 900, height: 220 }});\n\n"
        "export default workflow('reel-engine', " + json.dumps(ENGINE_NAME) + ")\n"
        "  .add(called).to(startRun).to(take).to(card).to(script).to(pictures).to(reviewPics).to(picAnswer\n"
        "    .onCase(0, waitPics.to(reviewPics))\n"
        "    .onCase(1, clips.to(edit).to(reviewFinal).to(finalAnswer\n"
        "      .onCase(0, waitFinal.to(reviewFinal))\n"
        "      .onCase(1, result)\n"
        "      .onCase(2, clips)))\n"
        "    .onCase(2, pictures)\n"
        "    .onCase(3, script))\n"
        "  .add(about);\n"
    )


def _form_fields() -> list[dict]:
    spec = [("style", "Style (ugc, cinematic, founder)", False), ("request", "What is the reel about?", True),
            ("language", "Language (en, hi, hinglish, gu)", False), ("watcher", "Who is watching this run?", True),
            ("chat", "Telegram chat id (for approvals)", False), ("requested_by", "Asked by", False)]
    return [{"fieldName": n, "fieldLabel": label, "fieldType": "text", "requiredField": req} for n, label, req in spec]


def brand_code(slug: str, name: str, style: str, engine_id: str) -> str:
    def field(n: str, value: str) -> dict:
        return {"id": f"f-{n}", "name": n, "value": value, "type": "string"}
    fields = [field("brand", slug), field("style", f"={{{{ $json.style || '{style}' }}}}"),
              field("request", "={{ $json.request || '' }}"), field("language", "={{ $json.language || 'en' }}"),
              field("chat", "={{ $json.chat || '' }}"), field("watcher", "={{ $json.watcher || 'n8n editor (clicked Run now)' }}"),
              field("requested_by", "={{ $json.requested_by || $json.watcher || 'n8n editor' }}")]
    wf_name = f"Reel: {name}"
    note = f"Holds this brand's name ({name}) and its usual style ({style}). A new brand changes only this."
    return (
        "import { workflow, node, trigger } from '@n8n/workflow-sdk';\n\n"
        "const runNow = trigger({ type: 'n8n-nodes-base.manualTrigger', version: 1, config: { name: 'Run now', position: [0, 0], "
        "notes: 'To start by hand: type the idea and your Telegram number in Run settings, then click Execute.', notesInFlow: true } });\n"
        "const hermes = trigger({ type: 'n8n-nodes-base.formTrigger', version: 2.6, config: { name: 'When called by Hermes', "
        "position: [0, 200], notes: 'Starts the reel when someone asks in Telegram. The bot fills in this form with the style, the idea and who asked.', "
        "notesInFlow: true, parameters: { authentication: 'n8nUserAuth', formTitle: " + json.dumps(f"New reel: {name}") + ", "
        f"formFields: {{ values: {json.dumps(_form_fields())} }}, responseMode: 'onReceived', "
        f"options: {{ appendAttribution: false, path: {json.dumps('dtj-reel-' + slug)}, respondWithOptions: {{ values: {{ respondWith: 'text', "
        "formSubmittedText: 'Started. The person on duty approves the script, pictures and reel in Telegram.' } } } } } });\n"
        "const settings = node({ type: 'n8n-nodes-base.set', version: 3.4, config: { name: 'Run settings', position: [240, 100], "
        f"notes: {json.dumps(note)}, notesInFlow: true, "
        f"parameters: {{ mode: 'manual', includeOtherFields: false, assignments: {{ assignments: {json.dumps(fields)} }} }} }} }});\n"
        "const engine = node({ type: 'n8n-nodes-base.executeWorkflow', version: 1.2, config: { name: 'Reel Engine', position: [480, 100], "
        "notes: 'Runs the shared Reel Engine for this brand and waits until the reel is finished.', notesInFlow: true, "
        f"parameters: {{ workflowId: {{ __rl: true, mode: 'id', value: {json.dumps(engine_id)} }}, options: {{ waitForSubWorkflow: true }} }} }} }});\n\n"
        f"export default workflow({json.dumps('reel-' + slug)}, {json.dumps(wf_name)})\n"
        "  .add(runNow).to(settings).to(engine)\n"
        "  .add(hermes).to(settings);\n"
    )


def _find(call, name: str) -> str | None:
    hits = [w for w in call("search_workflows", {"query": name}).get("data", []) if w.get("name") == name]
    return hits[0]["id"] if hits else None


def deploy(call, project: str, name: str, code: str, description: str) -> str:
    wf_id = _find(call, name)
    if wf_id:
        call("update_workflow", {"workflowId": wf_id, "code": code})
        print(f"{name}: refreshed ({wf_id})")
        return wf_id
    made = call("create_workflow_from_code", {"code": code, "description": description, "projectId": project})
    wf_id = made.get("workflowId") or made.get("id")
    print(f"{name}: created ({wf_id}), unpublished")
    return wf_id


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--brand", help="brand slug (folder name on the engine host), e.g. branda")
    ap.add_argument("--name", help="the brand's name as people say it, e.g. 'Brand A'")
    ap.add_argument("--style", default="ugc", help="default reel style for this brand")
    a = ap.parse_args(argv)
    if a.dry_run:
        print(engine_code())
        if a.brand:
            print(brand_code(a.brand, a.name or a.brand, a.style, "<Reel Engine id>"))
        return 0
    from n8n_mcp import PROJECT, call  # noqa: PLC0415 - needs the n8n token; --dry-run does not
    try:
        engine_id = _find(call, ENGINE_NAME) if a.brand else None
        if not engine_id:
            engine_id = deploy(call, PROJECT, ENGINE_NAME, engine_code(),
                               "Reel engine shared by every brand: Gemini script, Codex pictures, the person's changes, Flow clips, Claude QC and edit.")
        if a.brand:
            deploy(call, PROJECT, f"Reel: {a.name or a.brand}", brand_code(a.brand, a.name or a.brand, a.style, engine_id),
                   f"Starts the Reel Engine for {a.name or a.brand}; Telegram /reel through Hermes or Run now.")
    except (urllib.error.URLError, RuntimeError, OSError) as exc:
        print(f"not deployed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
