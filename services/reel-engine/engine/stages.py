"""The reel stages, one per n8n node ("1 [GEMINI] Style card", ...). Each takes (run, brand, body) and returns a JSON dict.

    take        request, style, language, chat (Telegram), watcher -> the run's request + a reel-factory job folder (run/job/)
    style_card  [GEMINI] the brand's references of this style -> brand/style-cards/<style>.json (rebuilt only when refs change)
    script      [GEMINI] brief + facts + card + idea -> run/job/script.json (reel-factory's shape), checked by its lint
    pictures    [CHATGPT + CLAUDE] one start picture per scene (Codex), Claude scores it, redraws below 7/10 (max 2 redraws)
    review      [PERSON] gate "pictures" (script + album) or "final" (the reel) through reel_job.py; polled by n8n every minute
    clips       [FLOW + CLAUDE] flow_cli per scene, reel-factory's check (words, product, sheets), Claude looks at the sheet;
                a bad scene is made again, at most 3 rounds, then it is listed in needs_look
    edit        reel-factory's edit (trims, beats, captions, -14 LUFS) -> run/final/reel.mp4
    result      the answer for n8n (reel_status, final_path, ...) and the Telegram finish

The person's change note decides what is redone ("next"): scene numbers -> only those scenes; words about the line/script ->
the script; anything else on the final -> the edit. Nothing is deleted: every picture, take and script version stays.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import models
from .brands import Brand
from .runs import Run

ENGINE = Path(__file__).resolve().parents[1]
REPO = ENGINE.parents[1]
FACTORY = REPO / "services" / "reel-factory"
REEL_JOB = REPO / "n8n" / "reel-factory" / "reel_job.py"
sys.path.insert(0, str(FACTORY))
from reel_factory.job import lint_script  # noqa: E402

PASS_SCORE = 7
MAX_REDRAWS = 2
CLIP_ROUNDS = 3
WORD_NOTE = re.compile(r"\b(line|lines|script|say|says|said|word|words|caption|captions|voice|dialogue|hook|speak)\b", re.I)


def _run_json(cmd: list[str], cwd: Path | None = None) -> tuple[int, dict]:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=1800, stdin=subprocess.DEVNULL)
    last = next((ln for ln in reversed((p.stdout or "").strip().splitlines()) if ln.startswith("{")), "{}")
    try:
        return p.returncode, json.loads(last)
    except json.JSONDecodeError:
        return p.returncode, {"ok": False, "error": (p.stderr or p.stdout or "")[-300:]}


def _person(args: list[str]) -> tuple[int, dict]:
    return _run_json([sys.executable, str(REEL_JOB), *args], cwd=REPO)


def _factory(stage: str, job_dir: Path, shots: str | None = None) -> int:
    cmd = [sys.executable, "-m", "reel_factory.job", stage, "--job", str(job_dir)] + (["--shots", shots] if shots else [])
    return subprocess.run(cmd, cwd=FACTORY, timeout=3600, stdin=subprocess.DEVNULL).returncode


def _flow_clip(image, prompt_file, out_dir, products=(), seconds=8, **kw):
    from reel_factory.flow_cli import clip  # noqa: PLC0415 - Playwright only when a clip is made
    return clip(image, prompt_file, out_dir, products, seconds, **kw)


@dataclass
class Deps:
    gemini_json: Callable = models.gemini_json
    claude_json: Callable = models.claude_json
    codex_image: Callable = models.codex_image
    flow_clip: Callable = _flow_clip
    person: Callable = _person
    factory: Callable = _factory
    niche_root: Path = field(default_factory=lambda: Path("/home/ai/reel-engine/Niches"))


def _deps(deps: Deps | None) -> Deps:
    return deps or Deps()


def _job(run: Run) -> Path:
    return run.dir / "job"


def _jid(run: Run) -> str:
    return f"re-{run.brand}-{run.run}"[:48]


def _load(p: Path, default=None):
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else default


def _save(p: Path, data) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return p


def _playbook(style: str) -> str:
    p = ENGINE / "playbooks" / f"{style}.md"
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def _version(folder: Path, stem: str, ext: str) -> Path:
    n = 1
    while (folder / f"{stem}_v{n}{ext}").exists():
        n += 1
    return folder / f"{stem}_v{n}{ext}"


def _script(run: Run) -> dict:
    return _load(_job(run) / "script.json", {})


def _change(run: Run, body: dict, stage: str) -> tuple[list[str] | None, str]:
    """(only, note) for this call: given in the body, or the person's last change when n8n passes its loop counter."""
    if body.get("only") or body.get("note"):
        return body.get("only"), str(body.get("note") or "").strip()
    p = run.state.get("pending") or {}
    if int(body.get("loop") or 0) > 0 and p.get("next") == stage and p.get("loop") == int(body["loop"]):
        return p.get("only"), str(p.get("note") or "")
    return None, ""


def _set_job_state(run: Run, **kv) -> None:
    p = _job(run) / "state.json"
    st = _load(p, {})
    st.update(kv)
    _save(p, st)


# ---------------- stages ----------------
def take(run: Run, brand: Brand, body: dict, deps: Deps | None = None) -> dict:
    d = _deps(deps)
    style = str(body.get("style") or brand.info.get("default_style") or "ugc")
    req = {"idea": str(body.get("request") or "").strip(), "style": style, "language": body.get("language") or "en",
           "chat": str(body.get("chat") or ""), "requested_by": body.get("requested_by") or body.get("watcher")}
    if not req["idea"]:
        return {"ok": False, "error": "no request: say what the reel is about (e.g. 'Diwali reel, the family shares the pack')"}
    if not brand.products:
        return {"ok": False, "error": f"{brand.name} has no product photos in products/: add the real pack pictures to its Drive folder"}
    refs = brand.references(style, d.niche_root)
    music = sorted((brand.dir / "music").glob("*")) if (brand.dir / "music").is_dir() else []
    products = [str(p) for p in brand.products]
    _save(_job(run) / "request.json", {
        "product_name": brand.info.get("product_name") or brand.info.get("name") or brand.name, "language": req["language"],
        "product_images": products, "reference_reels": [str(r) for r in refs],
        "local": {"product_images": products, "music": [str(m) for m in music[:1]]}})
    run.state["request"] = req
    run.save()
    if req["chat"]:
        d.person(["start", "--job", _jid(run), "--chat", req["chat"], "--title", f"Reel: {brand.info.get('name', brand.name)} ({style})"])
    return {"ok": True, "run": run.run, "style": style, "references": len(refs)}


STYLE_CARD = """STYLE CARD. You are a senior short-form video director. Watch every attached reference reel ({style} reels for the
{niche} niche). Write the shared recipe a new reel must copy: hook (first 2 s), shot list pattern (framing, lens feel, camera
movement, duration), pace (cuts per 10 s, words per second), light and colour, sound and music, on-screen text placement, how the
product is shown, what the people do. Note what makes them work. JSON keys: hook, shots, pace, light, sound, text, product, people,
why_it_works, avoid. Style playbook:
{playbook}"""


def style_card(run: Run, brand: Brand, body: dict, deps: Deps | None = None) -> dict:
    d = _deps(deps)
    style = run.state.get("request", {}).get("style") or body.get("style")
    refs = brand.references(style, d.niche_root)
    card = brand.style_card_path(style)
    if card.is_file() and card.stat().st_mtime >= max(r.stat().st_mtime for r in refs) and not body.get("redo"):
        return {"ok": True, "card": str(card), "cached": True}
    data = d.gemini_json(STYLE_CARD.format(style=style, niche=brand.niche or "brand's", playbook=_playbook(style)), refs,
                         run.dir / "gemini")
    _save(card, {**data, "style": style, "references": [r.name for r in refs]})
    return {"ok": True, "card": str(card), "cached": False}


SCRIPT = """REEL SCRIPT. Write a {style} reel for this brand, copying the style card closely (same hook pattern, shot pattern, pace).
Idea from the team: {idea}
Language: {language}. Brand brief:
{brief}
APPROVED FACTS (the ONLY claims, numbers or results the reel may say or show; never invent offers, prices, reviews or results):
{facts}
Style card:
{card}
Style playbook:
{playbook}
The attached pictures are the real product: describe it exactly (shape, colour, label) in every picture prompt.
Return JSON: {{"language": "{language}", "product_name": "...", "phrases": ["product name"], "keywords": [...], "music_db": -13,
"style": "{style}", "shots": [{{"id": "s1", "line": "spoken words or empty", "caption": "", "seconds": 4|6|8|10,
"image_prompt": "the start picture of this scene, 9:16, photographic", "video_prompt": "what moves; the product stays still
and the same", "product": true|false}}]}}. 3 to 10 shots, under 60 s, at most 3 spoken words per second.
{fix}"""


def _lint(script: dict, facts: str, style: str) -> list[str]:
    bad = lint_script(script, facts)
    return [b for b in bad if style == "ugc" or "how the phone films it" not in b]


def script(run: Run, brand: Brand, body: dict, deps: Deps | None = None) -> dict:
    d = _deps(deps)
    req = run.state["request"]
    card = _load(brand.style_card_path(req["style"]), {})
    _, note = _change(run, body, "script")
    fix = f"The person asked for this change to the last version: {note}\nLast version:\n{json.dumps(_script(run))}" if note else ""
    errors: list[str] = []
    for attempt in (1, 2):
        prompt = SCRIPT.format(style=req["style"], idea=req["idea"], language=req["language"], brief=brand.brief, facts=brand.facts,
                               card=json.dumps(card, ensure_ascii=False), playbook=_playbook(req["style"]),
                               fix=fix + ("\nFIX THESE PROBLEMS:\n- " + "\n- ".join(errors) if errors else ""))
        data = d.gemini_json(prompt, brand.products, run.dir / "gemini")
        for i, s in enumerate(data.get("shots") or []):
            s["id"] = f"s{i + 1}"
        data.setdefault("language", req["language"])
        _save(_version(_job(run), "script", ".json"), data)
        errors = _lint(data, brand.facts, req["style"])
        if not errors:
            _save(_job(run) / "script.json", data)
            return {"ok": True, "scenes": len(data["shots"]), "script": str(_job(run) / "script.json")}
    return {"ok": False, "errors": errors, "error": "the script broke the rules twice: " + "; ".join(errors[:3])}


PIC_CHECK = """PICTURE CHECK. The first file is a start picture for scene {sid} of a {style} reel; the others are the REAL product.
The scene: {prompt}
Style card (the quality bar): {card}
Score 1-10 for: the product matches the real pack exactly (shape, label, colour), looks like a real camera photo (no plastic
skin, no melted hands, hands joined to wrists, no extra fingers), matches the scene and the style card's look. Below 7 = redraw.
JSON: {{"score": n, "problems": ["..."]}}"""


def pictures(run: Run, brand: Brand, body: dict, deps: Deps | None = None) -> dict:
    d = _deps(deps)
    sc, style = _script(run), run.state["request"]["style"]
    card = json.dumps(_load(brand.style_card_path(style), {}), ensure_ascii=False)[:3000]
    only, note = _change(run, body, "pictures")
    only = set(only or [s["id"] for s in sc["shots"]])
    current = run.state.setdefault("pictures", {})
    scores, redrawn, needs_look = {}, [], []
    folder = run.dir / "pictures"
    for s in sc["shots"]:
        if s["id"] not in only:
            continue
        prompt = s["image_prompt"] + (f"\nChange asked by the team: {note}" if note else "")
        for attempt in range(MAX_REDRAWS + 1):
            out = d.codex_image(prompt, brand.products, _version(folder, s["id"], ".png"))
            verdict = d.claude_json(PIC_CHECK.format(sid=s["id"], style=style, prompt=s["image_prompt"], card=card),
                                    [out, *brand.products], run.dir / "claude")
            scores[s["id"]] = verdict.get("score", 0)
            if scores[s["id"]] >= PASS_SCORE:
                break
            if attempt < MAX_REDRAWS:
                redrawn.append(s["id"])
                prompt += "\nFix: " + "; ".join(verdict.get("problems") or [])
        else:
            needs_look.append(s["id"])
        current[s["id"]] = str(out)
    run.save()
    picks = _load(_job(run) / "state.json", {}).get("pick", {})
    for sid, path in current.items():
        picks.setdefault(sid, {})["image"] = path
    _set_job_state(run, pick=picks)
    return {"ok": True, "pictures": current, "scores": scores, "redrawn": sorted(set(redrawn)), "needs_look": needs_look}


def _route(note: str, ids: list[str], gate: str) -> dict:
    nums = [f"s{n}" for n in re.findall(r"\b(\d{1,2})\b", note) if f"s{n}" in ids]
    only = sorted(set(nums), key=ids.index)
    if gate == "pictures":
        if WORD_NOTE.search(note) and not only:
            return {"next": "script"}
        return {"next": "pictures", "only": only or ids}
    if only:
        return {"next": "clips", "only": only}
    # "make it warmer" on the final cannot be redone by a stage: the reel ends with the note for a person to finish by hand
    return {"next": "script" if WORD_NOTE.search(note) else "result"}


def _summary(sc: dict) -> str:
    return "Script:\n" + "\n".join(f"{s['id'][1:]}. ({s['seconds']} s) {s.get('line') or '(no words)'}" for s in sc.get("shots", []))


def review(run: Run, brand: Brand, body: dict, deps: Deps | None = None) -> dict:
    d = _deps(deps)
    gate, rnd = str(body.get("gate") or "pictures"), int(run.state.get("loop", 0)) + 1
    sc = _script(run)
    ids = [s["id"] for s in sc.get("shots", [])]
    told = run.state.setdefault("told", [])
    if gate == "pictures":
        folder = run.dir / "review" / f"pictures-r{rnd}"
        if not folder.is_dir():
            folder.mkdir(parents=True)
            for sid in ids:
                shutil.copy(run.state["pictures"][sid], folder / f"{sid[1:].zfill(2)}.png")
        key = f"script-r{rnd}"
        if key not in told:
            d.person(["tell", "--job", _jid(run), "--text", _summary(sc)])
            told.append(key)
            run.save()
        code, ans = d.person(["pictures", "--job", _jid(run), "--dir", str(folder), "--round", str(rnd)])
    else:
        code, ans = d.person(["final", "--job", _jid(run), "--file", str(run.dir / "final" / "reel.mp4"), "--round", str(rnd)])
    if code == 3:
        return {"ok": True, "waiting": True}
    if code != 0:
        return {"ok": False, "error": ans.get("error") or f"reel_job.py {gate} failed (exit {code})"}
    if ans.get("ok"):
        return {"ok": True, "approved": True, "by": ans.get("by"), "next": "clips" if gate == "pictures" else "save"}
    note = str(ans.get("note") or "")
    route = _route(note, ids, gate)
    loop = int(run.state.get("loop", 0)) + 1
    run.state.update(loop=loop, pending={**route, "note": note, "loop": loop})
    run.save()
    return {"ok": True, "approved": False, "by": ans.get("by"), "note": note, **route}


CLIP_CHECK = """CLIP CHECK. These are 4 frames-per-second contact sheets of the picked take for scene {sid} of a {style} reel.
The scene: {prompt}
Reject (ok false) for: the product drops, floats, teleports, smears, melts or changes; extra or melted fingers; a hand not joined
to a wrist; a different product; a face or body that morphs; a line cut off. JSON: {{"ok": true|false, "problems": ["..."]}}"""


def clips(run: Run, brand: Brand, body: dict, deps: Deps | None = None) -> dict:
    d = _deps(deps)
    sc, style, job = _script(run), run.state["request"]["style"], _job(run)
    only, note = _change(run, body, "clips")
    only = set(only or [s["id"] for s in sc["shots"]])
    credits, needs_look, problems = 0, [], {}
    for s in sc["shots"]:
        if s["id"] not in only:
            continue
        prompt = s["video_prompt"] + (f"\nChange asked by the team: {note}" if note else "")
        for rnd in range(1, CLIP_ROUNDS + 1):
            pf = _save(job / "prompts" / f"{s['id']}_r{rnd}.txt", prompt)
            pf.write_text(prompt, encoding="utf-8")
            code, ans = d.flow_clip(run.state["pictures"][s["id"]], pf, job / "clips", brand.products[:1], s["seconds"],
                                    project=run.state.get("flow_project"))
            if ans.get("needs_person"):
                raise models.NeedsPerson(ans.get("error") or "Flow needs a person")
            if code != 0:
                problems[s["id"]] = [ans.get("error", "Flow failed")]
                continue
            credits += ans.get("credits") or 0
            if ans.get("project"):
                run.state["flow_project"] = ans["project"]
            st = _load(job / "state.json", {})
            st.setdefault("clips", {})[s["id"]] = [{"file": f, "asset": a} for f, a in zip(ans["files"], ans.get("assets") or [])]
            st.get("pick", {}).get(s["id"], {}).pop("take", None)
            _save(job / "state.json", st)
            d.factory("check", job, shots=s["id"])
            take = _load(job / "state.json", {}).get("pick", {}).get(s["id"], {}).get("take")
            sheets = sorted((job / "checks").glob(f"{s['id']}*sheet*.jpg")) if (job / "checks").is_dir() else []
            if take and sheets:
                verdict = d.claude_json(CLIP_CHECK.format(sid=s["id"], style=style, prompt=s["video_prompt"]), sheets[-2:],
                                        run.dir / "claude")
                if verdict.get("ok"):
                    problems.pop(s["id"], None)
                    break
                problems[s["id"]] = verdict.get("problems") or []
                prompt += "\nFix: " + "; ".join(problems[s["id"]])
            else:
                problems[s["id"]] = ["no take passed the automatic checks"]
        else:
            needs_look.append(s["id"])
    run.state["credits"] = run.state.get("credits", 0) + credits
    run.save()
    return {"ok": True, "credits": credits, "needs_look": needs_look, "problems": problems}


def edit(run: Run, brand: Brand, body: dict, deps: Deps | None = None) -> dict:
    d = _deps(deps)
    job = _job(run)
    code = d.factory("edit", job)
    qc = _load(job / "final" / "qc.json", {})
    src = job / "final" / "reel_final.mp4"
    if code != 0 or not src.is_file():
        return {"ok": False, "error": qc.get("note") or f"the edit failed (exit {code})"}
    final = run.dir / "final" / "reel.mp4"
    final.parent.mkdir(parents=True, exist_ok=True)
    if final.exists():
        final.replace(_version(final.parent, "reel", ".mp4"))  # the old cut is kept as reel_vN.mp4
    shutil.copy(src, final)
    run.state["qc"] = qc
    run.save()
    return {"ok": True, "final": str(final), "seconds": qc.get("duration"), "status": qc.get("status"), "note": qc.get("note", "")}


def result(run: Run, brand: Brand, body: dict, deps: Deps | None = None) -> dict:
    d = _deps(deps)
    qc = run.state.get("qc") or {}
    clip_look = (run.done("clips") or {}).get("needs_look") or []
    final = run.dir / "final" / "reel.mp4"
    status = "could not make" if not final.is_file() else ("needs a look" if clip_look or qc.get("status") != "reel ready" else "reel ready")
    note = "; ".join(filter(None, [qc.get("note"), f"scenes to watch closely: {clip_look}" if clip_look else ""]))
    if run.state.get("request", {}).get("chat"):
        d.person(["finish", "--job", _jid(run), "--ok" if status != "could not make" else "--stopped", "--note", note or status])
    return {"ok": True, "reel_status": status, "final_path": str(final) if final.is_file() else "", "duration_s": qc.get("duration"),
            "reel_note": note, "credits": run.state.get("credits", 0), "watcher": run.state.get("watcher")}


STAGES = {"take": take, "style_card": style_card, "script": script, "pictures": pictures, "review": review, "clips": clips,
          "edit": edit, "result": result}
RERUN = {"review"}


def run_stage(name: str, run: Run, brand: Brand, body: dict, deps: Deps | None = None) -> dict:
    """One stage as n8n calls it: every answer carries the loop counter; a failure is also told to the person in Telegram."""
    d = _deps(deps)
    try:
        res = STAGES[name](run, brand, body, deps=d)
    except models.NeedsPerson as exc:
        res = {"ok": False, "needs_person": True, "error": str(exc)[:500]}
    res.setdefault("loop", int(run.state.get("loop", 0)))
    if not res.get("ok") and run.state.get("request", {}).get("chat"):
        why = res.get("error") or "; ".join(res.get("errors") or []) or "unknown"
        d.person(["tell", "--job", _jid(run), "--text", f"The reel stopped at '{name}': {why[:600]}\n"
                  + ("A person must fix this (sign in / look at the window), then retry the step in n8n."
                     if res.get("needs_person") else "Retry the step in n8n after the fix.")])
    return res


SERVER_STAGES = {n: (lambda run, brand, body, n=n: run_stage(n, run, brand, body)) for n in STAGES}
