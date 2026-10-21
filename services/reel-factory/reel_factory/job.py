"""One reel job, stage by stage. Run from services/reel-factory:

    python -m reel_factory.job new       --job <dir> --request request.json   folders, inputs downloaded, request checked
    python -m reel_factory.job refs      --job <dir>                          break down every reference reel (sheets, words, cuts)
      (the Claude Code session writes <dir>/script.json from the breakdowns: see the skill dtj-ugc-reel)
    python -m reel_factory.job lint      --job <dir>                          script rules + every claim must be in the facts
    python -m reel_factory.job character --job <dir>                          ChatGPT: character (fresh chat), then product in hand
    python -m reel_factory.job images    --job <dir> [--shots s1,s3]          Flow Nano Banana: 2 start pictures per shot
    python -m reel_factory.job pick      --job <dir> --shot s1 --image <file> | --take <file> [--start s --end s]
    python -m reel_factory.job clips     --job <dir> [--shots s2]             Flow Omni Flash: 2 takes per shot, then check
    python -m reel_factory.job check     --job <dir> [--shots s2]             offline: sparkle removed (LaMa), words, product, 4 fps sheets
    python -m reel_factory.job edit      --job <dir>                          trims, music, captions, loudness, final checks
    python -m reel_factory.job result    --job <dir>                          the answer for n8n (also written to result.json)

Job folder: request.json, inputs/, refs/<n>/, script.json, state.json, images/, clips/ (raw Flow takes), clean/ (LaMa), checks/,
final/, result.json. Every stage can be run again; it only redoes what it is asked to.
Nothing here spends money except Flow credits (Omni Flash: 14 credits per 4 s x2, 24 per 8 s x2, read 20 Oct 2026); images are free.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

LANGS = ("en", "hi", "hinglish")
SECONDS = (4, 6, 8, 10)
CREDITS = {4: 14, 8: 24}                   # per x2 generation; 6 s and 10 s were not read: "not available"
MAX_WORDS_PER_S = 3.0                      # faster lines get cut off or rushed by Omni
STATUSES = ("reel ready", "needs a look", "could not make")
# Words that pull Flow / ChatGPT toward the polished "AI ad" look (studio light, glossy skin, perfect composition).
SLOP_WORDS = ("cinematic", "studio", "flawless", "perfect skin", "porcelain", "airbrushed", "8k", "4k", "ultra-detailed", "ultra detailed",
              "hyperrealistic", "hyper-realistic", "photorealistic", "masterpiece", "professional photo", "commercial", "bokeh",
              "dramatic lighting", "softbox", "ring light", "glossy", "beautiful lighting", "perfect composition", "symmetrical")
# Every clip must say what phone setup filmed it (the winners are all phone footage: selfie arm, propped phone, a friend holding it).
CAMERA_WORDS = re.compile(r"handheld|selfie|propped|phone|front camera|arm.s length|held by a friend", re.I)
# A finished reel inside these ranges reads as phone footage (realism.py; real reels and Harsh's AI winners, 21 Oct 2026).
REAL_RANGES = {"shake_px": (0.5, 1.3), "sharpness": (40, 650)}


# ---------------- files ----------------
def _load(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        if default is None:
            raise
        return default


def _save(p: Path, data) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    return p


class Job:
    def __init__(self, folder: str | Path):
        self.dir = Path(folder).resolve()

    def path(self, *parts) -> Path:
        return self.dir.joinpath(*parts)

    @property
    def request(self) -> dict:
        return _load(self.path("request.json"))

    @property
    def script(self) -> dict:
        return _load(self.path("script.json"))

    @property
    def state(self) -> dict:
        return _load(self.path("state.json"), {})

    def set_state(self, **kv):
        st = self.state; st.update(kv); _save(self.path("state.json"), st)

    def shots(self, only: str | None = None) -> list[dict]:
        want = set(only.split(",")) if only else None
        return [s for s in self.script["shots"] if not want or s["id"] in want]


# ---------------- checks that need no browser or GPU ----------------
def check_request(req: dict) -> list[str]:
    bad = []
    for k in ("product_name", "product_images", "reference_reels", "language"):
        if not req.get(k):
            bad.append(f"request has no {k}")
    if req.get("language") and req["language"] not in LANGS:
        bad.append(f"language must be one of {LANGS}")
    return bad


def animation(script: dict) -> bool:
    """A 3D-character reel (Blue Tea's ingredient characters): no phone camera, so no phone-setup words, wobble or realism gate."""
    return script.get("style") == "animation"


def lint_script(script: dict, facts: str) -> list[str]:
    """Rules from book-01 and senso-01: real numbers only, lines Omni can say in the clip, one product state per clip."""
    from .checks import claims_in
    bad, f = [], (facts or "").lower()
    shots = script.get("shots") or []
    if not 3 <= len(shots) <= 10:
        bad.append(f"{len(shots)} shots: a reel has 3 to 10")
    if script.get("language") not in LANGS:
        bad.append(f"script language must be one of {LANGS}")
    total = 0
    for s in shots:
        sid = s.get("id", "?")
        for k in ("id", "line", "seconds", "image_prompt", "video_prompt"):
            if not s.get(k) and s.get(k) != "":
                bad.append(f"{sid}: no {k}")
        sec = s.get("seconds")
        if sec not in SECONDS:
            bad.append(f"{sid}: seconds must be one of {SECONDS}")
            continue
        total += sec
        n = len(str(s.get("line", "")).split())
        if n > MAX_WORDS_PER_S * sec:
            bad.append(f"{sid}: {n} words in {sec} s is too fast (at most {int(MAX_WORDS_PER_S * sec)})")
        for c in claims_in(f"{s.get('line', '')} {s.get('caption', '')}"):
            if c.lower() not in f:
                bad.append(f"{sid}: '{c}' is not in the approved facts (never invent numbers or claims)")
        for field in ("image_prompt", "video_prompt"):
            slop = [w for w in SLOP_WORDS if w in str(s.get(field, "")).lower()]
            if slop:
                bad.append(f"{sid}: {field} uses AI-ad words {slop}: describe a real phone video instead")
        if not animation(script) and not CAMERA_WORDS.search(str(s.get("video_prompt", ""))):
            bad.append(f"{sid}: video_prompt must say how the phone films it (handheld selfie, propped phone, a friend holding it)")
        if s.get("product") and not re.search(r"\b(same|steady|keeps?|holds?|still)\b", s.get("video_prompt", ""), re.I):
            bad.append(f"{sid}: a product shot's video prompt must say how the product stays (e.g. 'holds the same box steady, "
                       "label to camera, never drops it')")
    if total > 60:
        bad.append(f"{total} s of clips: keep a reel under 60 s")
    char = " ".join(str(v) for v in (script.get("character") or {}).values()).lower()
    slop = [w for w in SLOP_WORDS if w in char]
    if slop:
        bad.append(f"character prompts use AI-ad words {slop}")
    return bad


def credits(shots: list[dict], rounds: int = 1) -> int | None:
    vals = [CREDITS.get(s["seconds"]) for s in shots]
    return None if None in vals else sum(vals) * rounds


def auto_pick(takes: list[dict]) -> dict | None:
    """Best take: words all said and the product steady; then most product on screen."""
    ok = [t for t in takes if t.get("check", {}).get("ok")]
    return max(ok, key=lambda t: t["check"].get("visible_pct", 0)) if ok else None


def reply_body(job: Job) -> dict:
    res = _load(job.path("final", "qc.json"), {})
    st = job.state
    status = res.get("status") or ("could not make" if not res else "needs a look")
    body = {"reel_status": status, "job_folder": str(job.dir), "final_path": res.get("final", ""),
            "duration_s": res.get("duration"), "lufs": res.get("lufs"), "shots": len(job.script.get("shots", [])) if job.path("script.json").exists() else 0,
            "generations": st.get("generations", 0), "credits_used": st.get("credits_used"), "note": res.get("note", st.get("note", ""))[:1000]}
    if status not in STATUSES:
        body["reel_status"] = "needs a look"
    return body


def grid(files: list[str], out: Path, w: int = 270, cols: int = 4) -> Path:
    """One picture with every start image side by side, file name on each (for a quick look)."""
    import cv2
    import numpy as np
    h = int(w * 16 / 9); rows = max(1, (len(files) + cols - 1) // cols)
    canvas = np.zeros((rows * h, cols * w, 3), np.uint8)
    for i, f in enumerate(files):
        im = cv2.imread(str(f))
        if im is None:
            continue
        r, c = divmod(i, cols)
        canvas[r * h:(r + 1) * h, c * w:(c + 1) * w] = cv2.resize(im, (w, h))
        cv2.putText(canvas, Path(f).stem, (c * w + 6, r * h + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), canvas)
    return out


# ---------------- stages ----------------
def stage_new(job: Job, request: str) -> int:
    from .flow import download
    req = _load(Path(request))
    bad = check_request(req)
    if bad:
        print("request refused:\n- " + "\n- ".join(bad), file=sys.stderr); return 2
    for d in ("inputs", "refs", "images", "clips", "clean", "checks", "final"):
        job.path(d).mkdir(parents=True, exist_ok=True)
    local = {}
    for key in ("product_images", "reference_reels", "music", "product_cutout"):
        items = req.get(key) or []
        items = items if isinstance(items, list) else [items]
        out = []
        for i, it in enumerate(items):
            if re.match(r"^https?://", str(it)):
                ext = Path(str(it).split("?")[0]).suffix or (".mp4" if key == "reference_reels" else ".png")
                out.append(str(download(it, job.path("inputs", f"{key}_{i}{ext}"))))
            else:
                src = Path(it)
                if not src.exists():
                    print(f"request refused: {key} file not found: {it}", file=sys.stderr); return 2
                dst = job.path("inputs", f"{key}_{i}{src.suffix}")
                shutil.copyfile(src, dst); out.append(str(dst))
        local[key] = out
    _save(job.path("request.json"), {**req, "local": local})
    print(json.dumps({"job": str(job.dir), "inputs": {k: len(v) for k, v in local.items()}}))
    return 0


def stage_refs(job: Job) -> int:
    from .breakdown import breakdown
    req = job.request
    out = []
    for i, ref in enumerate(req["local"]["reference_reels"]):
        b = breakdown(ref, str(job.path("refs", str(i))), None if req["language"] == "hinglish" else req["language"])
        out.append({"ref": i, "duration": b["duration"], "cuts": len(b["cuts"]), "first_word_s": b["first_word_s"],
                    "words_per_s": b["words_per_s"], "transcript": b["transcript"][:300]})
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


def stage_lint(job: Job) -> int:
    script = job.script
    bad = lint_script(script, job.request.get("facts", ""))
    print(json.dumps({"ok": not bad, "problems": bad, "flow_credits_one_round": credits(script["shots"]) or "not available"}, indent=1))
    return 0 if not bad else 2


def stage_character(job: Job, cdp: str) -> int:
    from .chatgpt import ChatGPT
    c = job.script["character"]
    g = ChatGPT.attach(cdp)
    try:
        person = g.image(c["chatgpt_prompt"], job.path("images", "character.png"))
        hero = g.image(c["product_prompt"], job.path("images", "hero.png"), files=[person, job.request["local"]["product_images"][0]])
    finally:
        g.close()
    job.set_state(character=str(person), hero=str(hero))
    print(json.dumps({"character": str(person), "hero": str(hero), "next": "look at both pictures before the images stage"}))
    return 0


def _flow(job: Job, cdp: str):
    from .flow import Flow
    fl = Flow(cdp)
    url = fl.open_project(job.state.get("flow_project"))
    job.set_state(flow_project=url)
    return fl


def _asset(job: Job, fl, path: str) -> str:
    st = job.state; ups = st.get("uploads", {})
    if path not in ups:
        ups[path] = fl.upload(path); fl.clear_attached()
        job.set_state(uploads=ups)
    return ups[path]


def stage_images(job: Job, cdp: str, only: str | None) -> int:
    from .flow import download
    fl = _flow(job, cdp)
    try:
        fl.settings("Image", takes=2, model="Nano Banana")
        hero = _asset(job, fl, job.state.get("hero") or str(job.path("images", "hero.png")))
        product = _asset(job, fl, job.request["local"]["product_images"][0])
        imgs = job.state.get("images", {})
        for s in job.shots(only):
            fl.clear_attached()
            for a in (hero, product):
                fl.attach(a)
            ids = fl.generate(s["image_prompt"], expect=2, timeout_s=240)
            files = []
            for k, a in enumerate(ids):
                f = job.path("images", f"{s['id']}_{'ab'[k]}.png")
                download(fl.image_url(a), f)
                files.append({"file": str(f), "asset": a})
            imgs[s["id"]] = files
            job.set_state(images=imgs)
            print(f"{s['id']}: {[Path(x['file']).name for x in files]}", flush=True)
    finally:
        fl.close()
    grid([x["file"] for v in job.state["images"].values() for x in v], job.path("checks", "images_sheet.jpg"))
    print(json.dumps({"next": "look at checks/images_sheet.jpg, then: pick --shot <id> --image <file> for every shot"}))
    return 0


def stage_pick(job: Job, shot: str, image: str | None, take: str | None, start: float | None, end: float | None) -> int:
    picks = job.state.get("pick", {})
    p = picks.get(shot, {})
    if image:
        p["image"] = str(Path(image).resolve())
    if take:
        p["take"] = str(Path(take).resolve())
        p["by_hand"] = True        # a person watched it and chose it (e.g. Whisper misheard a word the take says right)
    if start is not None:
        p["start"] = start
    if end is not None:
        p["end"] = end
    picks[shot] = p
    job.set_state(pick=picks)
    print(json.dumps({shot: p}))
    return 0


def stage_clips(job: Job, cdp: str, only: str | None) -> int:
    from .flow import download
    shots = job.shots(only)
    picks = job.state.get("pick", {})
    missing = [s["id"] for s in shots if not picks.get(s["id"], {}).get("image")]
    if missing:
        print(f"pick a start picture first for {missing} (pick --shot <id> --image <file>)", file=sys.stderr); return 2
    fl = _flow(job, cdp)
    clips = job.state.get("clips", {})
    try:
        product = _asset(job, fl, job.request["local"]["product_images"][0])
        for s in shots:
            fl.settings("Video", takes=2, model="Omni", seconds=s["seconds"])   # mode first: a mode change drops ingredients
            start_img = _asset(job, fl, picks[s["id"]]["image"])
            fl.clear_attached()
            for a in (start_img, product):
                fl.attach(a)
            ids = fl.generate(s["video_prompt"], expect=2, timeout_s=900)
            st = job.state
            job.set_state(generations=st.get("generations", 0) + 1,
                          credits_used=(st.get("credits_used") or 0) + CREDITS[s["seconds"]] if s["seconds"] in CREDITS else st.get("credits_used"))
            clips[s["id"]] = [{"file": str(download(fl.video_url(a), job.path("clips", f"{s['id']}_t{k + 1}_{a[:8]}.mp4"))), "asset": a}
                              for k, a in enumerate(ids)]
            picks = job.state.get("pick", {})
            picks.get(s["id"], {}).pop("take", None)          # new takes: the old pick no longer applies
            job.set_state(clips=clips, pick=picks)
            print(f"{s['id']}: 2 takes downloaded", flush=True)
    finally:
        fl.close()

    return stage_check(job, only)


def stage_check(job: Job, only: str | None) -> int:
    """Offline: remove the sparkle (LaMa), then words, product and 4 fps sheet for every take; auto-pick the best take."""
    from .checks import ProductTracker, words_check
    from .media import duration, sheet, words
    from .watermark import Remover, residual
    shots = job.shots(only)
    clips = job.state.get("clips", {})
    req = job.request
    tracker_img = (req["local"].get("product_cutout") or req["local"]["product_images"])[0]
    tracker = ProductTracker(tracker_img)
    rm = Remover()
    lang = job.script.get("language", "en")
    for s in shots:
        if s["id"] not in clips:
            print(f"{s['id']}: no takes yet (clips --shots {s['id']})", file=sys.stderr); return 2
        for t in clips[s["id"]]:
            if t.get("clean") and Path(t["clean"]).exists() and t.get("check"):
                continue
            clean = str(job.path("clean", Path(t["file"]).name))
            t["lama"] = rm.clip(t["file"], clean); t["clean"] = clean
            heard = words(clean, lang, prompt=job.script.get("product_name") or req["product_name"])
            wc = words_check(heard, s["line"]) if lang == "en" else {"said": " ".join(w for w, _, _ in heard), "missing": [],
                                                                  "speech": (heard[0][1], heard[-1][2]) if heard else None,
                                                                  "ok": bool(heard), "note": "Hindi/Hinglish: read 'said' against the line"}
            pt = tracker.take(clean, expect_product=bool(s.get("product")))
            t["words"] = heard
            d = duration(clean)
            left = residual(t["file"], clean)
            t["check"] = {**pt, "words": wc, "sparkle_left": left, "ok": pt["ok"] and wc["ok"] and not left, "duration": d}
            t["sheet"] = sheet(clean, str(job.path("checks", Path(clean).stem + "_4fps.jpg")), fps=4, cols=8, rows=max(1, -(-int(d * 4) // 8)))
        best = auto_pick(clips[s["id"]])
        picks = job.state.get("pick", {})
        current = picks.get(s["id"], {}).get("take")
        if best and current not in [t["clean"] for t in clips[s["id"]]]:   # a person's pick of one of these takes stays
            picks.setdefault(s["id"], {}).update(take=best["clean"], by_hand=False)
        job.set_state(clips=clips, pick=picks)
        print(json.dumps({s["id"]: [{"take": Path(t["clean"]).name, "ok": t["check"]["ok"], "visible_pct": t["check"]["visible_pct"],
                                     "issues": t["check"]["issues"], "missing_words": t["check"]["words"]["missing"],
                                     "sparkle_left": len(t["check"].get("sparkle_left", [])),
                                     "sheet": t["sheet"]} for t in clips[s["id"]]], "picked": Path(best["clean"]).name if best else None},
                         ensure_ascii=False), flush=True)
    print(json.dumps({"next": "LOOK at every 4 fps sheet of the picked takes (drops, floats, smears, weird hands = reject); "
                              "re-run clips --shots <id> with a fixed video_prompt for any shot without a good take"}))
    return 0


def stage_edit(job: Job) -> int:
    from . import beats
    from .captions import BOTTOM_MARK, TOP_MARK
    from .checks import ProductTracker, caption_place
    from .edit import render
    from .media import duration, run
    from .remotion import render as remotion_render
    script, req, st = job.script, job.request, job.state
    picks, clips = st.get("pick", {}), st.get("clips", {})
    missing = [s["id"] for s in script["shots"] if not picks.get(s["id"], {}).get("take")]
    if missing:
        why = f"no good take for {missing}: regenerate them (clips --shots ...) or pick one by hand"
        job.set_state(note=why)
        print(why, file=sys.stderr); return 2
    tracker = ProductTracker((req["local"].get("product_cutout") or req["local"]["product_images"])[0])
    plan_clips, speech, heard_by_shot = [], [], []
    for i, s in enumerate(script["shots"]):
        p = picks[s["id"]]
        take = next((t for t in clips.get(s["id"], []) if t.get("clean") == p["take"]), {})
        heard = take.get("words") or []
        dur = duration(p["take"])
        sp = (heard[0][1], heard[-1][2]) if heard else None
        start = p.get("start", max(0.0, sp[0] - 0.25) if sp else 0.0)
        end = p.get("end", min(dur, sp[1] + 0.35) if sp else dur)
        # "caption": "top" | "bottom" in the script overrides the tracker (it cannot find a 3D-rendered box on an animated reel)
        place = s.get("caption") or caption_place(p["take"], tracker if s.get("product") else None)
        plan_clips.append({"file": p["take"], "start": round(start, 2), "end": round(min(end, dur), 2), "max_end": round(dur, 3),
                           "cap_margin": -1 if s.get("no_captions") else (TOP_MARK if place == "top" else BOTTOM_MARK)})
        speech.append(sp); heard_by_shot.append(heard)
    music = (req["local"].get("music") or [None])[0]
    if music:
        wav = str(job.path("final", "_music.wav"))
        run(["ffmpeg", "-v", "error", "-y", "-i", music, "-ac", "1", "-ar", "22050", wav])
        bpm, _ = beats.tempo(*beats.load_mono(wav))
        plan_clips = beats.plan_cuts(plan_clips, speech, 60 / bpm, max_len=max(c["end"] for c in plan_clips) + 0.25)
    for i, c in enumerate(plan_clips):
        if i % 2 == 1 and len([w for w in heard_by_shot[i] if w[1] >= c["start"]]) >= 4:
            c["punch"] = beats.punch_window(heard_by_shot[i], c["start"], c["end"])
    plan = {"clips": plan_clips, "music": music, "music_db": script.get("music_db", -13), "language": script.get("language", "en"),
            "script": " ".join(s["line"] for s in script["shots"]), "lines": [s["line"] for s in script["shots"]],
            "keywords": script.get("keywords", []),
            "phrases": script.get("phrases", [req["product_name"]]), "spelling": script.get("spelling", {}),
            "out_dir": str(job.path("final")), "name": "reel", "phone_look": not animation(script)}
    _save(job.path("final", "edit-plan.json"), plan)
    out = render(plan)
    final = str(job.path("final", "reel_final.mp4"))
    note = []
    try:
        remotion_render(out["nocap"], out["pages"], final, f"job{job.dir.name}")
        captions = "remotion"
    except (RuntimeError, OSError) as exc:
        shutil.copyfile(out["ass"], final); captions = "ass (fallback)"
        note.append(f"Remotion captions failed, plain captions used: {str(exc)[:200]}")
    marks = []
    for s in script["shots"]:
        take = next((t for t in clips.get(s["id"], []) if t.get("clean") == picks[s["id"]]["take"]), None)
        if take is None or "sparkle_left" not in take.get("check", {}):
            continue
        marks += [f"{s['id']}@{m['t']}s" for m in take["check"]["sparkle_left"]]
    lufs = (out.get("loudness") or {}).get("lufs")
    if marks:
        note.append(f"sparkle may be left in {marks[:6]}")
    from .realism import measure
    real = measure(out["nocap"])
    off = {k: real[k] for k, (lo, hi) in REAL_RANGES.items() if real.get(k) is None or not lo <= real[k] <= hi}
    if off and not animation(script):
        note.append(f"does not read as phone footage: {off} (phone range {REAL_RANGES})")
        marks.append("realism")
    shots_ok = all(picks[s["id"]].get("by_hand") or
                   next((t["check"]["ok"] for t in clips.get(s["id"], []) if t.get("clean") == picks[s["id"]]["take"]), False)
                   for s in script["shots"])
    if not shots_ok:
        note.append("at least one picked take did not pass the automatic checks: a person must watch it")
    status = "reel ready" if not marks and shots_ok else "needs a look"
    qc = {"status": status, "final": final, "duration": out["duration"], "lufs": lufs, "captions": captions,
          "caption_pages": out["pages_count"], "sparkle_hits": [m for m in marks if m != "realism"], "realism": real, "note": "; ".join(note)}
    _save(job.path("final", "qc.json"), qc)
    print(json.dumps(qc, indent=1, ensure_ascii=False))
    return 0


def stage_result(job: Job) -> int:
    body = reply_body(job)
    _save(job.path("result.json"), body)
    print(json.dumps(body, indent=1, ensure_ascii=False))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=("new", "refs", "lint", "character", "images", "pick", "clips", "check", "edit", "result"))
    ap.add_argument("--job", required=True)
    ap.add_argument("--request")
    ap.add_argument("--shots")
    ap.add_argument("--shot")
    ap.add_argument("--image")
    ap.add_argument("--take")
    ap.add_argument("--start", type=float)
    ap.add_argument("--end", type=float)
    ap.add_argument("--cdp", default="http://127.0.0.1:9222", help="the reel Chrome's debugging address")
    a = ap.parse_args(argv)
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    job = Job(a.job)
    if a.stage == "new":
        if not a.request:
            ap.error("new needs --request")
        return stage_new(job, a.request)
    if a.stage == "pick":
        if not a.shot or not (a.image or a.take or a.start is not None or a.end is not None):
            ap.error("pick needs --shot and --image or --take (and optional --start/--end)")
        return stage_pick(job, a.shot, a.image, a.take, a.start, a.end)
    from .flow import NeedsPerson
    try:
        return {"refs": lambda: stage_refs(job), "lint": lambda: stage_lint(job), "character": lambda: stage_character(job, a.cdp),
                "images": lambda: stage_images(job, a.cdp, a.shots), "clips": lambda: stage_clips(job, a.cdp, a.shots),
                "check": lambda: stage_check(job, a.shots),
                "edit": lambda: stage_edit(job), "result": lambda: stage_result(job)}[a.stage]()
    except NeedsPerson as exc:
        job.set_state(note=str(exc))
        print(f"needs a person: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
