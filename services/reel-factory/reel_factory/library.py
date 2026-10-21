"""Reel libraries: learn how real winning reels in one niche talk and look, as numbers and examples the writer must match.

A library is a folder of real reels for one niche (food, beauty, books...), e.g. Downloads/dtj-reel-library/food/:
    fb_<id>.mp4 ...           the reels (Meta Ad Library ads running 30+ days, strong organic reels, our own winners)
    manifest.json             one entry per reel: id, file, source, advertiser, started, days_running, query, keep (a person's yes)
    analysis/<id>/            transcript.txt, words.json, features.json, sheet.jpg (what this module writes)
    style.json                the niche's measured ranges (aggregate)

    python -m reel_factory.library review    <lib>    gallery pictures + list for a person to verify (keep / drop)
    python -m reel_factory.library analyze   <lib>    transcribe and measure every kept reel (GPU Whisper)
    python -m reel_factory.library aggregate <lib>    style.json: median and the 20-80 % range of each number

Why numbers: a model shown 50 reels drifts back to its own polished voice; a script that must land inside the real creators'
ranges (words per second, sentence length, fillers, Hindi/English mix, questions to the viewer) cannot.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

from .media import duration, run, sheet, words

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
ROMAN_HINDI = set("""hai hain ho hoga hogi tha thi the ki ka ke ko se mein me main par pe aur bhi toh to nahi nahin na mat kya kyun
kaise kaun kab yeh ye woh wo yahan wahan ab abhi phir fir bas sab ek do teen aap tum hum mai mujhe tujhe aapko tumhe hume unko
apna apni apne mera meri mere tera teri tere uska uski uske yaar arre matlab bhai behen didi ji acha accha theek thik chalo dekho
suno karo kar karna kiya kiye gaya gayi raha rahi rahe wala wali wale bohot bahut thoda zyada kam sirf bilkul pura poora sach
khana khao piyo chai paani ghar""".split())
FILLERS_EN = ("like", "literally", "honestly", "basically", "actually", "okay", "ok", "guys", "bro", "seriously", "wait", "um", "uh",
              "you know", "i mean", "so yeah", "right")
FILLERS_HI = ("yaar", "na", "matlab", "toh", "arre", "acha", "accha", "bas", "dekho", "suno", "haan", "bhai", "basically")
YOU = re.compile(r"\b(you|your|you're|aap|aapko|aapka|aapki|tum|tumhe|tumhara|tera|tujhe)\b|आप|तुम|तेरा|तुझे", re.I)


def _manifest(lib: Path) -> list[dict]:
    p = lib / "manifest.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def features(path: str, ws: list[tuple[str, float, float]], cuts: list[float]) -> dict:
    dur = duration(path)
    toks = [w for w, _, _ in ws]
    n = len(toks)
    text = " ".join(toks)
    low = [re.sub(r"[^\wऀ-ॿ']", "", t.lower()) for t in toks]
    hi = sum(1 for t in low if DEVANAGARI.search(t) or t in ROMAN_HINDI)
    sentences = [s for s in re.split(r"(?<=[.!?।])\s+", text) if s.strip()]
    gaps = [b[1] - a[2] for a, b in zip(ws, ws[1:])]
    talk = (ws[-1][2] - ws[0][1]) if ws else 0
    fill = sum(text.lower().count(" " + f + " ") for f in FILLERS_EN) + sum(1 for t in low if t in FILLERS_HI)
    return {
        "duration_s": round(dur, 1), "words": n, "speaking": n >= 15,
        "first_word_s": round(ws[0][1], 2) if ws else None,
        "words_first_3s": sum(1 for _, a, _ in ws if a < 3),
        "words_per_s": round(n / talk, 2) if talk > 1 else 0,
        "sentence_words": round(n / max(len(sentences), 1), 1),
        "questions_per_30s": round(text.count("?") * 30 / max(dur, 1), 2),
        "you_per_100w": round(len(YOU.findall(text)) * 100 / max(n, 1), 1),
        "fillers_per_100w": round(fill * 100 / max(n, 1), 1),
        "hindi_share": round(hi / max(n, 1), 2),
        "pauses_per_30s": round(sum(1 for g in gaps if g > 0.4) * 30 / max(dur, 1), 2),
        "cuts_per_10s": round(len(cuts) * 10 / max(dur, 1), 2),
    }


def analyze(lib: Path, only: set[str] | None = None) -> int:
    from .breakdown import cuts as scene_cuts
    done = 0
    for e in _manifest(lib):
        if e.get("keep") is False or (only and e["id"] not in only):
            continue
        f = lib / e["file"]
        out = lib / "analysis" / e["id"]
        if (out / "features.json").exists():
            continue
        out.mkdir(parents=True, exist_ok=True)
        try:
            ws = words(str(f), None)
        except Exception as exc:                                   # a reel with no audio track still gets a picture analysis
            print(f"{e['id']}: no words ({exc})", file=sys.stderr)
            ws = []
        c = scene_cuts(str(f))
        (out / "words.json").write_text(json.dumps(ws, ensure_ascii=False), encoding="utf-8")
        (out / "transcript.txt").write_text(" ".join(w for w, _, _ in ws), encoding="utf-8")
        feat = {**features(str(f), ws, c), "id": e["id"], "advertiser": e.get("advertiser", ""), "cuts": c}
        (out / "features.json").write_text(json.dumps(feat, indent=1, ensure_ascii=False), encoding="utf-8")
        sheet(str(f), str(out / "sheet.jpg"), fps=2, cols=8, rows=4, width=160)
        sheet(str(f), str(out / "hook.jpg"), fps=4, cols=6, rows=2, width=200, length=3)
        done += 1
        print(f"{e['id']}: {feat['words']} words, {feat['words_per_s']} w/s, hindi {feat['hindi_share']}", flush=True)
    return done


KEYS = ("first_word_s", "words_first_3s", "words_per_s", "sentence_words", "questions_per_30s", "you_per_100w",
        "fillers_per_100w", "hindi_share", "pauses_per_30s", "cuts_per_10s", "duration_s")


def aggregate(lib: Path) -> dict:
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in (lib / "analysis").glob("*/features.json")]
    keep = {e["id"] for e in _manifest(lib) if e.get("keep") is not False}
    rows = [r for r in rows if r["id"] in keep]
    talk = [r for r in rows if r.get("speaking")]
    style = {"reels": len(rows), "speaking_reels": len(talk), "ranges": {}}
    for k in KEYS:
        vals = sorted(r[k] for r in talk if r.get(k) is not None)
        if len(vals) >= 3:
            q = statistics.quantiles(vals, n=10)
            style["ranges"][k] = {"p20": round(q[1], 2), "median": round(statistics.median(vals), 2), "p80": round(q[7], 2)}
    (lib / "style.json").write_text(json.dumps(style, indent=1), encoding="utf-8")
    return style


def review(lib: Path) -> Path:
    """One gallery picture per 10 reels (6 frames across each reel, its number on the left) + review.md to mark keep/drop."""
    import cv2
    import numpy as np
    m = _manifest(lib)
    out = lib / "review"; out.mkdir(exist_ok=True)
    lines = ["# Review: keep or drop each reel", "", "Reply with the numbers to DROP (not food, no talking/UGC feel, bad quality, duplicate).", "",
             "| # | id | advertiser | started | length | first words |", "|---|---|---|---|---|---|"]
    for page in range(0, len(m), 10):
        rows_img = []
        for i, e in enumerate(m[page:page + 10], start=page + 1):
            f = str(lib / e["file"])
            d = duration(f)
            cap = cv2.VideoCapture(f)
            frames = []
            for t in np.linspace(0.5, max(d - 0.5, 0.6), 6):
                cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, fr = cap.read()
                frames.append(cv2.resize(fr, (135, 240)) if ok else np.zeros((240, 135, 3), np.uint8))
            label = np.zeros((240, 90, 3), np.uint8)
            cv2.putText(label, f"#{i}", (8, 130), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 255), 2)
            rows_img.append(np.hstack([label] + frames))
            tr = lib / "analysis" / e["id"] / "transcript.txt"
            first = tr.read_text(encoding="utf-8")[:60] if tr.exists() else ""
            lines.append(f"| {i} | {e['id']} | {e.get('advertiser', '')[:30]} | {e.get('started', '')} | {d:.0f} s | {first} |")
        cv2.imwrite(str(out / f"gallery_{page // 10 + 1:02d}.jpg"), np.vstack(rows_img))
    (out / "review.md").write_text("\n".join(lines), encoding="utf-8")
    (out / "review.html").write_text(review_html(lib.name, m), encoding="utf-8")
    return out


def review_html(name: str, m: list[dict]) -> str:
    """A page that plays every reel with its number, brand and days running, so a person can verify before analysis."""
    from html import escape
    cards = []
    for i, e in enumerate(m, start=1):
        kind = "creator partnership" if e.get("creator_partnership") else "brand ad"
        cards.append(f'<div class="c"><div class="n">#{i}</div><video src="../{escape(e["file"])}" controls preload="metadata" playsinline></video>'
                     f'<div class="m"><b>{escape(e.get("advertiser", ""))}</b><br>{e.get("days_running")} days running &middot; {kind}'
                     f'<br><span>{escape(e.get("copy", "")[:160])}</span></div></div>')
    return ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(name)} reel review</title><style>body{{font:14px system-ui;background:#111;color:#eee;margin:16px}}'
            'h1{font-size:18px}.g{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px}'
            '.c{background:#1c1c1c;border-radius:10px;padding:8px;position:relative}.n{position:absolute;top:12px;left:14px;'
            'background:#ffd400;color:#000;font-weight:700;padding:2px 8px;border-radius:6px;z-index:2}'
            'video{width:100%;aspect-ratio:9/16;background:#000;border-radius:6px}.m{margin-top:6px;line-height:1.35}'
            '.m span{color:#aaa;font-size:12px}</style></head><body>'
            f'<h1>{escape(name)}: {len(m)} reels from Meta Ad Library &mdash; reply with the numbers to DROP</h1>'
            '<p>Drop: off-niche, no person talking (pure graphics or product montage), duplicates, poor quality.</p>'
            f'<div class="g">{"".join(cards)}</div></body></html>')


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("review", "analyze", "aggregate"))
    ap.add_argument("lib")
    ap.add_argument("--only", help="comma-separated ids")
    a = ap.parse_args(argv)
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    lib = Path(a.lib)
    if a.cmd == "review":
        print(f"review pictures in {review(lib)}")
    elif a.cmd == "analyze":
        print(f"analysed {analyze(lib, set(a.only.split(',')) if a.only else None)} reel(s)")
    else:
        print(json.dumps(aggregate(lib), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
