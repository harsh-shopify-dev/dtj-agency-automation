"""Animated TikTok-style captions with the Remotion project in ../captions-remotion (word-by-word yellow highlight, pop-in).

Licence: Remotion is free for companies of up to 3 people; above that a Remotion company licence is needed
(remotion.pro/license). The libass version from edit.py (<name>_ass.mp4) is the licence-free fallback.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .media import run

PROJECT = Path(__file__).resolve().parents[1] / "captions-remotion"


def render(nocap: str, pages: str, out: str, job_key: str) -> str:
    pub = PROJECT / "public"
    pub.mkdir(exist_ok=True)
    video = pub / f"{job_key}.mp4"
    shutil.copyfile(nocap, video)
    shutil.copyfile(pages, pub / f"{job_key}.pages.json")
    raw = str(Path(out).with_suffix(".raw.mp4"))
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        raise RuntimeError("npx not found: install Node 22+ and run `npm ci` in captions-remotion")
    r = subprocess.run([npx, "remotion", "render", "CaptionedVideo", raw, "--codec", "h264", "--crf", "18", "--overwrite",
                        "--props", json.dumps({"src": video.name})], cwd=PROJECT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode:
        raise RuntimeError(f"remotion render failed: {r.stderr[-1500:]}")
    run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-i", nocap, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "copy",
         "-movflags", "+faststart", out])
    for p in (raw, video, pub / f"{job_key}.pages.json"):
        Path(p).unlink(missing_ok=True)
    return out
