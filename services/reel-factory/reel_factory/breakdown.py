"""Break down a reference reel: format, cuts, loudness, words with timings, 4 fps sheets, hook strip, music stem (optional)."""
from __future__ import annotations

import json
import os
import re

from .media import loudness_report, probe, run, sheet, words


def cuts(path: str, threshold: float = 0.25) -> list[float]:
    e = run(["ffmpeg", "-v", "info", "-i", path, "-vf", f"select='gt(scene,{threshold})',showinfo", "-an", "-f", "null", "-"]).stderr
    return [round(float(t), 2) for t in re.findall(r"pts_time:([\d.]+)", e)]


def breakdown(path: str, out_dir: str, language: str | None = None, music_stem: bool = False) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    info = probe(path)
    w = words(path, language)
    gaps = [(round(a[2], 2), round(b[1] - a[2], 2)) for a, b in zip(w, w[1:]) if b[1] - a[2] > 0.4]
    talk = (w[-1][2] - w[0][1]) if w else 0
    sheets = []
    step = 12.0
    t = 0.0
    while t < info["duration"]:
        sheets.append(sheet(path, os.path.join(out_dir, f"sheet_{int(t):02d}.jpg"), fps=4, cols=8, rows=6, start=t, length=step))
        t += step
    hook = sheet(path, os.path.join(out_dir, "hook.jpg"), fps=4, cols=6, rows=2, width=270, length=3)
    res = {
        "file": path, **info, "loudness": loudness_report(path), "cuts": cuts(path),
        "words": w, "first_word_s": w[0][1] if w else None, "words_first_3s": sum(1 for x in w if x[1] < 3),
        "words_per_s": round(len(w) / talk, 2) if talk else 0, "pauses_over_0_4s": gaps,
        "transcript": " ".join(x[0] for x in w), "sheets": sheets, "hook_sheet": hook,
    }
    if music_stem:
        wav = os.path.join(out_dir, "audio.wav")
        run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vn", "-ac", "2", "-ar", "44100", wav])
        import sys
        run([sys.executable, "-m", "demucs", "--two-stems=vocals", "-o", os.path.join(out_dir, "sep"), wav])
        res["music_stem"] = os.path.join(out_dir, "sep", "htdemucs", "audio", "no_vocals.wav")
    with open(os.path.join(out_dir, "breakdown.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    return res
