"""FFmpeg / ffprobe helpers and Whisper word timings."""
from __future__ import annotations

import json
import re
import subprocess


class MediaError(RuntimeError):
    pass


def run(args: list[str]) -> subprocess.CompletedProcess:
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise MediaError(f"{args[0]} failed: {r.stderr[-1500:]}")
    return r


def duration(path: str) -> float:
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).stdout)


def lufs(path: str, start: float | None = None, end: float | None = None) -> float:
    cut = (["-ss", str(start)] if start is not None else []) + (["-to", str(end)] if end is not None else [])
    e = run(["ffmpeg", "-v", "info", *cut, "-i", path, "-af", "ebur128", "-f", "null", "-"]).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", e)[-1])


def loudness_report(path: str) -> dict:
    e = run(["ffmpeg", "-v", "info", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    tail = e[e.rfind("Summary"):]
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", tail)
    p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", tail)
    return {"lufs": float(i[-1]) if i else None, "true_peak_db": float(p[-1]) if p else None}


def probe(path: str) -> dict:
    out = json.loads(run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
                          "-of", "json", path]).stdout)
    v = next((s for s in out.get("streams", []) if s.get("codec_type") == "video"), {})
    return {"width": v.get("width"), "height": v.get("height"), "fps": v.get("r_frame_rate"),
            "has_audio": any(s.get("codec_type") == "audio" for s in out.get("streams", [])),
            "duration": float(out.get("format", {}).get("duration", 0) or 0)}


_MODEL = {}


def words(path: str, language: str | None = "en", prompt: str | None = None, model: str = "medium") -> list[tuple[str, float, float]]:
    """Whisper word timings. GPU when there is one (fp16), else CPU."""
    import torch
    import whisper
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    key = (model, dev)
    if key not in _MODEL:
        _MODEL[key] = whisper.load_model(model, device=dev)
    lang = None if language in (None, "", "auto", "hinglish") else ("hi" if language == "hi" else language)
    r = _MODEL[key].transcribe(path, language=lang, word_timestamps=True, fp16=(dev == "cuda"), initial_prompt=prompt)
    return [(w["word"].strip(), w["start"], w["end"]) for s in r["segments"] for w in s["words"]]


def sheet(path: str, out: str, fps: float = 4, cols: int = 8, rows: int = 6, width: int = 180, start: float = 0,
          length: float | None = None) -> str:
    """Contact sheet with timestamps (the 4 fps review that catches drops, floats and smears)."""
    h = int(width * 16 / 9)
    trim = f"trim=start={start}" + (f":end={start + length}" if length else "") + ","
    vf = (f"{trim}fps={fps},scale={width}:{h},drawtext=text='%{{pts\\:hms}}':x=3:y=3:fontsize=14:fontcolor=yellow:"
          f"box=1:boxcolor=black@0.6,tile={cols}x{rows}:padding=2")
    run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vf", vf, "-frames:v", "1", out])
    return out
