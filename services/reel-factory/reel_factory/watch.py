"""The watcher's measured checks (the dtj-reel-watcher skill judges with these numbers; it never guesses them).

    python -m reel_factory.watch g1 --job <dir>                       plan / script: slop.py policy + tells, shots vs the reference
    python -m reel_factory.watch g2 --job <dir> [--marks <dir>]       pictures vs their reference frames, other brands' marks
    python -m reel_factory.watch g3 --job <dir>                       Flow clips: flicker, black/flash frames, start match, sparkle
    python -m reel_factory.watch g4 --job <dir> [--final <mp4>]       final: spec, loudness, frames, safe zones, motion vs reference
    python -m reel_factory.watch marks --job <dir> --from <frame> --box x0,y0,x1,y1 [--box ...]
                                                                      cut another brand's marks out of a reference frame (templates)
Writes <job>/watch/<gate>.json (and g2_pairs.jpg) and prints a one-line summary. Remake job layout (runbook): inputs/reference.mp4,
refs/clean/rNN.png (cleaned reference frames), images/pNN.png, clips/*.mp4 (+ clips/raw/), final/*.mp4, cut.json,
refs/ref_motion.json; marks templates in refs/marks/*.png.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np

SAFE = {"top": 0.14, "bottom": 0.35, "side": 0.06}     # Meta Reels: keep text/logos out of these bands (25 Oct 2026 research)
SPEC = {"width": 1080, "height": 1920}
EDGES_MIN = 0.45   # a picture whose edges match its reference frame less than this does not copy the frame (see g2)


# ---------- small measures
def _gray(img, size=(180, 320)):
    return cv2.cvtColor(cv2.resize(img, size, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)


def layout_similarity(a: np.ndarray, b: np.ndarray) -> dict:
    """How alike two frames are in structure (edges) and colour layout (0..1 each): the picture vs its reference frame."""
    ea, eb = (cv2.GaussianBlur(cv2.Canny(_gray(x), 60, 160).astype(np.float32), (0, 0), 3) for x in (a, b))
    ea, eb = ea - ea.mean(), eb - eb.mean()
    edges = float((ea * eb).sum() / (np.sqrt((ea ** 2).sum() * (eb ** 2).sum()) + 1e-6))
    small = [cv2.resize(x, (9, 16), interpolation=cv2.INTER_AREA).astype(np.float32) for x in (a, b)]
    colour = float(1 - np.abs(small[0] - small[1]).mean() / 255)
    return {"edges": round(max(0.0, edges), 3), "colour": round(colour, 3), "score": round(0.6 * max(0.0, edges) + 0.4 * colour, 3)}


def grade_gap(a: np.ndarray, b: np.ndarray) -> float:
    """Colour-grade distance (mean Lab difference, ~0-60): small = same light and colour."""
    la, lb = (cv2.cvtColor(x, cv2.COLOR_BGR2LAB).reshape(-1, 3).mean(0) for x in (a, b))
    return round(float(np.linalg.norm(la - lb)), 1)


def find_marks(img: np.ndarray, templates: list[tuple[str, np.ndarray]], threshold: float = 0.72) -> list[dict]:
    """Another brand's logo/strip found in a picture by template matching at several sizes (no OCR needed)."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hits = []
    for name, t in templates:
        tg = cv2.cvtColor(t, cv2.COLOR_BGR2GRAY)
        best = (0.0, None)
        for k in (0.6, 0.8, 1.0, 1.25, 1.5):
            w, h = int(tg.shape[1] * k * g.shape[1] / 720), int(tg.shape[0] * k * g.shape[1] / 720)
            if w < 12 or h < 8 or w >= g.shape[1] or h >= g.shape[0]:
                continue
            r = cv2.matchTemplate(g, cv2.resize(tg, (w, h)), cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(r)
            if mx > best[0]:
                best = (float(mx), (int(loc[0]), int(loc[1]), w, h))
        if best[0] >= threshold:
            hits.append({"mark": name, "match": round(best[0], 3), "box": best[1]})
    return hits


def frame_issues(path: str, every: int = 1) -> dict:
    """Black / flash frames and sudden exposure jumps, and the flicker level (median frame-to-frame change)."""
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    prev, means, diffs, black, flash, jumps, i = None, [], [], [], [], [], 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if i % every == 0:
            g = _gray(f, (90, 160)).astype(np.float32)
            m = float(g.mean())
            means.append(m)
            if m < 8:
                black.append(round(i / fps, 2))
            if m > 245:
                flash.append(round(i / fps, 2))
            if prev is not None:
                d = float(np.abs(g - prev).mean())
                diffs.append(d)
                if len(means) > 2 and abs(m - means[-2]) > 60:
                    jumps.append(round(i / fps, 2))
            prev = g
        i += 1
    cap.release()
    return {"frames": i, "fps": round(fps, 2), "black": black[:20], "flash": flash[:20], "exposure_jumps": jumps[:20],
            "flicker_median": round(float(np.median(diffs)) if diffs else 0.0, 2)}


def _first_frame(path: str) -> np.ndarray | None:
    cap = cv2.VideoCapture(path)
    ok, f = cap.read()
    cap.release()
    return f if ok else None


def _img(path: Path) -> np.ndarray:
    return cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_COLOR)


def _num(p: Path) -> int:
    m = re.search(r"(\d+)", p.stem)
    return int(m.group(1)) if m else -1


def _templates(job: Path, marks: Path | None) -> list[tuple[str, np.ndarray]]:
    d = marks or job / "refs" / "marks"
    return [(p.stem, _img(p)) for p in sorted(d.glob("*.png"))] if d.exists() else []


# ---------- gates
def g1(job: Path) -> dict:
    from . import slop  # noqa: PLC0415
    out: dict = {"gate": "g1"}
    cut = job / "cut.json"
    if cut.exists():
        segs = json.loads(cut.read_text(encoding="utf-8")).get("segments", [])
        out["shots_planned"] = len(segs)
        out["clips_planned"] = sum(1 for s in segs if str(s.get("src", "")).endswith(".mp4"))
    script = job / "script.json"
    if script.exists():
        res = slop.check(json.loads(script.read_text(encoding="utf-8")))
        out.update(slop_ok=res["ok"], policy=res["policy"], tells=res["tells"], numbers=res["numbers"])
        shots = json.loads(script.read_text(encoding="utf-8")).get("shots", [])
        out["short_clips"] = [s.get("id") for s in shots if 0 < float(s.get("seconds", 8)) < 6]
    return out


def g2(job: Path, marks: Path | None = None) -> dict:
    pics = sorted((p for p in (job / "images").glob("p*.png") if _num(p) > 0), key=_num)
    refs = {(_num(p)): p for p in (job / "refs" / "clean").glob("r*.png")}
    temps = _templates(job, marks)
    rows, pair_tiles = [], []
    for p in pics:
        n = _num(p)
        img = _img(p)
        row = {"picture": p.name, "n": n}
        ref = refs.get(n)
        if ref is not None:
            r = _img(ref)
            row["layout_similarity"] = layout_similarity(img, r)
            row["grade_gap_vs_reference"] = grade_gap(img, r)
            pair_tiles.append(np.hstack([cv2.resize(r, (180, 320)), cv2.resize(img, (180, 320))]))
        row["foreign_marks"] = find_marks(img, temps)
        rows.append(row)
    if pair_tiles:
        cols = 4
        while len(pair_tiles) % cols:
            pair_tiles.append(np.zeros_like(pair_tiles[0]))
        grid = np.vstack([np.hstack(pair_tiles[i:i + cols]) for i in range(0, len(pair_tiles), cols)])
        (job / "watch").mkdir(exist_ok=True)
        cv2.imencode(".jpg", grid)[1].tofile(str(job / "watch" / "g2_pairs.jpg"))
    # calibrated on mahalaxmi-02 (25 Oct 2026): the 16 approved pictures scored edges 0.54-0.93, the 4 "AI slop" ones 0.20-0.40
    low = [r["picture"] for r in rows if r.get("layout_similarity", {}).get("edges", 1) < EDGES_MIN]
    return {"gate": "g2", "pictures": rows, "low_similarity": low, "with_foreign_marks": [r["picture"] for r in rows if r["foreign_marks"]],
            "marks_checked": [t[0] for t in temps], "pairs_sheet": "watch/g2_pairs.jpg" if pair_tiles else ""}


def g3(job: Path) -> dict:
    rows = []
    for c in sorted((job / "clips").glob("*.mp4")):
        row = {"clip": c.name, **frame_issues(str(c))}
        start = job / "images" / (c.stem.split("_")[0] + ".png")
        f0 = _first_frame(str(c))
        if start.exists() and f0 is not None:
            row["start_match"] = layout_similarity(f0, _img(start))["score"]
        raw = job / "clips" / "raw" / c.name
        if raw.exists():
            try:
                from .watermark import residual  # noqa: PLC0415
                row["sparkle_left"] = residual(str(raw), str(c))
            except Exception as exc:  # noqa: BLE001 - LaMa/torch missing: say so, do not guess
                row["sparkle_left"] = f"not measured ({str(exc)[:80]})"
        rows.append(row)
    return {"gate": "g3", "clips": rows}


def _onsets(path: str) -> list[float]:
    """Music hits: peaks of the loudness rise (spectral-flux-like on 23 ms frames)."""
    try:
        from .beats import load_mono  # noqa: PLC0415
        a, sr = load_mono(path)
    except Exception:  # noqa: BLE001
        return []
    hop = 512
    n = len(a) // hop
    if n < 4:
        return []
    e = np.array([np.sqrt(np.mean(a[i * hop:(i + 1) * hop] ** 2)) for i in range(n)])
    rise = np.maximum(0, np.diff(e, prepend=e[0]))
    thr = rise.mean() + 2 * rise.std()
    return [round(i * hop / sr, 3) for i in range(1, n - 1) if rise[i] > thr and rise[i] >= rise[i - 1] and rise[i] >= rise[i + 1]]


def g4(job: Path, final: Path | None = None) -> dict:
    from . import media  # noqa: PLC0415
    final = final or max((job / "final").glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    out: dict = {"gate": "g4", "final": str(final)}
    pr = media.probe(str(final))
    out["spec"] = pr
    try:
        out["lufs"] = round(media.lufs(str(final)), 1)
    except Exception as exc:  # noqa: BLE001
        out["lufs"] = f"not measured ({str(exc)[:80]})"
    out["frames"] = frame_issues(str(final), every=1)
    ref = job / "inputs" / "reference.mp4"
    cut_p = job / "cut.json"
    cut = json.loads(cut_p.read_text(encoding="utf-8")) if cut_p.exists() else {}
    if ref.exists():
        out["duration"] = {"ours": round(media.duration(str(final)), 2), "reference": round(media.duration(str(ref)), 2)}
    # safe zones: the corner logo (cut.json corner_xy + its size) against Meta's bands
    if cut.get("corner") and cut.get("corner_xy"):
        logo = _img(job / cut["corner"]) if (job / cut["corner"]).exists() else None
        if logo is not None:
            x, y = cut["corner_xy"]
            w, h = logo.shape[1], logo.shape[0]
            W, H = cut.get("size", [1080, 1920])
            out["safe_zone"] = {"logo_box": [x, y, w, h], "in_top_band": y < SAFE["top"] * H, "in_bottom_band": y + h > (1 - SAFE["bottom"]) * H,
                                "in_side_band": x < SAFE["side"] * W or x + w > (1 - SAFE["side"]) * W}
    # cuts vs the music's hits
    hits = _onsets(str(final))
    cuts = [s["t0"] for s in cut.get("segments", [])[1:]]
    if hits and cuts:
        gaps = [min(abs(c - h) for h in hits) * 1000 for c in cuts]
        out["cuts_vs_beats_ms"] = {"median": round(float(np.median(gaps))), "worst": round(max(gaps)), "over_80ms": sum(g > 80 for g in gaps)}
    # motion vs the reference: our reel measured exactly like the reference (tools/remake/measure_motion.py)
    refm = job / "refs" / "ref_motion.json"
    if refm.exists() and cut.get("segments"):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "remake"))
        import measure_motion  # noqa: PLC0415
        ref_motion = json.loads(refm.read_text(encoding="utf-8"))
        anchors = [s["anchor"] for s in ref_motion["shots"]]
        ours = measure_motion.measure(str(final), cut["segments"], anchors, out=lambda *_: None)
        per = []
        for a, b in zip(ref_motion["shots"], ours["shots"]):
            n = min(len(a["frames"]), len(b["frames"]))
            ra = np.array([f.get("scale", np.nan) for f in a["frames"][:n]], float)
            rb = np.array([f.get("scale", np.nan) for f in b["frames"][:n]], float)
            ok = ~(np.isnan(ra) | np.isnan(rb)) & (ra > 0.3) & (rb > 0.3)
            ba = sum(f.get("blur", 0) >= 3 for f in a["frames"][:n])
            bb = sum(f.get("blur", 0) >= 3 for f in b["frames"][:n])
            per.append({"shot": a["shot"], "zoom_gap_max": round(float(np.max(np.abs(ra[ok] - rb[ok]))), 3) if ok.any() else None,
                        "zoom_gap_mean": round(float(np.mean(np.abs(ra[ok] - rb[ok]))), 3) if ok.any() else None,
                        "ref_scale_range": [round(float(np.nanmin(ra)), 2), round(float(np.nanmax(ra)), 2)] if ok.any() else None,
                        "our_scale_range": [round(float(np.nanmin(rb)), 2), round(float(np.nanmax(rb)), 2)] if ok.any() else None,
                        "blurred_frames": {"reference": ba, "ours": bb}})
        out["motion_vs_reference"] = per
    return out


VERDICTS = {"pass": 0, "fix": 1, "block": 2}


def _json_in(text: str) -> dict | None:
    """The last complete JSON object in a judge's answer (Claude's --output-format json wraps it in "result")."""
    try:
        outer = json.loads(text)
        if isinstance(outer, dict) and isinstance(outer.get("result"), str):
            text = outer["result"]
        elif isinstance(outer, dict) and "verdict" in outer:
            return outer
    except ValueError:
        pass
    best = None
    for start in [i for i, ch in enumerate(text) if ch == "{"]:
        depth = 0
        for j in range(start, len(text)):
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            if depth == 0:
                try:
                    got = json.loads(text[start:j + 1])
                    if isinstance(got, dict) and "verdict" in got:
                        best = got
                except ValueError:
                    pass
                break
    return best


def merge(job: Path, gate: str, rnd: int) -> dict:
    """Both judges into one verdict: the stricter verdict and the lower score win; blocking issues, issues and ideas from both
    (each tagged with its judge); a judge that gave nothing usable is named, never filled in."""
    w = job / "watch"
    got, missing = [], []
    for judge in ("claude", "codex"):
        raw = w / f"{gate}.{judge}.raw"
        v = _json_in(raw.read_text(encoding="utf-8", errors="replace")) if raw.exists() else None
        if v and v.get("verdict") in VERDICTS:
            v["judge"] = judge
            got.append(v)
        else:
            missing.append(judge)
    if not got:
        res = {"gate": gate, "round": rnd, "verdict": "fix", "score": None, "judges": [], "missing_judges": missing,
               "blocking": [], "issues": [{"item": "watcher", "issue": "no judge answered", "fix": "check claude/codex login on the VPS",
                                           "owner": "tools"}], "ideas": [], "for_person": "The watcher could not judge this step (no judge answered)."}
    else:
        tag = lambda items, j: [dict(x, judge=j) for x in items or [] if isinstance(x, dict)]  # noqa: E731
        res = {"gate": gate, "round": rnd, "judges": [v["judge"] for v in got], "missing_judges": missing,
               "verdict": max((v["verdict"] for v in got), key=VERDICTS.get),
               "score": min((v.get("score") for v in got if isinstance(v.get("score"), (int, float))), default=None),
               "blocking": sum((tag(v.get("blocking"), v["judge"]) for v in got), []),
               "issues": sum((tag(v.get("issues"), v["judge"]) for v in got), []),
               "ideas": sum((tag(v.get("ideas"), v["judge"]) for v in got), []),
               "for_person": " / ".join(str(v.get("for_person") or "") for v in got if v.get("for_person"))}
        if res["blocking"] and res["verdict"] != "block":
            res["verdict"] = "block"
    (w / f"{gate}.verdict.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    return res


from .watch_card import card  # noqa: E402,F401 - the Telegram card (shared with reel_job.py)


def marks(job: Path, frame: Path, boxes: list[list[int]]) -> dict:
    img = _img(frame)
    d = job / "refs" / "marks"
    d.mkdir(parents=True, exist_ok=True)
    k = img.shape[1] / 720                          # boxes are given on a 720 px wide frame (like clean_brand.py)
    saved = []
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        crop = img[int(y0 * k):int(y1 * k), int(x0 * k):int(x1 * k)]
        p = d / f"mark{i + 1}.png"
        cv2.imencode(".png", cv2.resize(crop, (int((x1 - x0)), int((y1 - y0)))))[1].tofile(str(p))
        saved.append(str(p))
    return {"saved": saved}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gate", choices=["g1", "g2", "g3", "g4", "marks", "merge", "card"])
    ap.add_argument("--job", type=Path, required=True)
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--marks", type=Path)
    ap.add_argument("--final", type=Path)
    ap.add_argument("--from", dest="frame", type=Path)
    ap.add_argument("--box", action="append", default=[])
    ap.add_argument("--of", help="merge / card: which gate (a0 g0 g1 g2 g3 g4 g5)")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if a.gate == "marks":
        print(json.dumps(marks(a.job, a.frame, [[int(v) for v in b.split(",")] for b in a.box])))
        return 0
    if a.gate in ("merge", "card"):
        if not a.of:
            raise SystemExit("--of <gate> is needed")
        v = merge(a.job, a.of, a.round) if a.gate == "merge" else json.loads((a.job / "watch" / f"{a.of}.verdict.json").read_text(encoding="utf-8"))
        print(card(v) if a.gate == "card" else json.dumps({k: v[k] for k in ("gate", "verdict", "score", "judges", "missing_judges")}))
        return 0
    res = {"g1": lambda: g1(a.job), "g2": lambda: g2(a.job, a.marks), "g3": lambda: g3(a.job), "g4": lambda: g4(a.job, a.final)}[a.gate]()
    (a.job / "watch").mkdir(exist_ok=True)
    (a.job / "watch" / f"{a.gate}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k in ("gate", "low_similarity", "with_foreign_marks", "lufs", "duration", "cuts_vs_beats_ms")},
                     ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
