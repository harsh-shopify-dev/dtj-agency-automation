"""Edit chosen takes into one 1080x1920 reel: trims, per-clip voice levelling, punch-in zooms, captions, music, loudness.

Plan (edit-plan.json):
  {"clips": [{"file": ".../clean/s1.mp4", "start": 0.1, "end": 3.9, "cap_margin": 548, "punch": [[t0, t1, 1.18]]}],
   "music": ".../bed.wav" | null, "music_db": -13, "language": "en", "script": "<the approved lines, in order>",
   "keywords": [...], "phrases": ["<product name>"], "spelling": {"heard": "Right"},
   "out_dir": ".../final", "name": "reel", "phone_look": true}
Writes <out_dir>/<name>_nocap.mp4 (clean picture + final audio), <name>_pages.json (caption pages for Remotion),
<name>_ass.mp4 (libass captions, the fallback) and returns their paths.
"""
from __future__ import annotations

import json
import os

from . import captions as cap
from .media import duration, loudness_report, lufs, run, words

VOICE_TARGET_LUFS = -20.0   # every clip's voice levelled to this before the mix (book-01 v2 had a 6 dB dip)
FINAL_LUFS, FINAL_TP = -14, -1.5


# Phone camera look (measured 21 Oct 2026 against real phone reels and Harsh's AI winners, see realism.py):
# Flow takes are locked off (hand wobble 0.20-0.26 px vs 0.73-0.86) and over-detailed (sharpness 1,058-1,517 vs 47-614).
# An edge-keeping soften (eyes, glasses, text stay crisp) and a slow hand wobble bring them to wobble ~0.73 and sharpness ~280.
SOFTEN = "smartblur=lr=2.0:ls=0.8:lt=-3"
WOBBLE_PX = 1.5


def wobble(i: int, a: float = WOBBLE_PX) -> str:
    """A slow, never-repeating hand wobble (three incommensurate sines), different for every clip i."""
    ph = [(i * 1.7 + k * 0.9) % 6.28 for k in range(6)]
    x = f"(iw-ow)/2+{a}*(sin(2*PI*t*0.47+{ph[0]:.2f})+0.7*sin(2*PI*t*1.13+{ph[1]:.2f})+0.2*sin(2*PI*t*3.1+{ph[2]:.2f}))"
    y = f"(ih-oh)/2+{a}*(sin(2*PI*t*0.39+{ph[3]:.2f})+0.7*sin(2*PI*t*0.97+{ph[4]:.2f})+0.2*sin(2*PI*t*2.7+{ph[5]:.2f}))"
    return f"scale=iw*1.03:-2,crop=1080:1920:'{x}':'{y}'"


def _part_filter(c: dict, i: int = 0, phone: bool = True) -> str:
    vf = "scale=1080:1920:flags=bicubic,fps=30"
    if phone:
        vf += f",{SOFTEN}"
    if c.get("punch"):
        z = "1"
        for t0, t1, zm in reversed(c["punch"]):
            z = f"if(between(in_time,{t0},{t1}),{zm},{z})"
        cy = c.get("punch_cy", 0.38)
        vf += f",zoompan=z='{z}':x='iw/2-iw/zoom/2':y='ih*{cy}-ih/zoom*{cy}':d=1:s=1080x1920:fps=30"
    if phone:
        vf += "," + wobble(i)
    return vf + ",format=yuv420p"


def render(plan: dict) -> dict:
    out_dir = plan["out_dir"]; name = plan.get("name", "reel")
    work = os.path.join(out_dir, "_work"); os.makedirs(work, exist_ok=True)

    parts = []
    for i, c in enumerate(plan["clips"]):
        p = os.path.join(work, f"part{i}.mp4")
        start = c.get("start", 0.0)
        gain = VOICE_TARGET_LUFS - lufs(c["file"], start, c["end"])
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-to", str(c["end"]), "-i", c["file"], "-vf", _part_filter(c, i, plan.get("phone_look", True)),
             "-af", f"aresample=48000,volume={gain:.2f}dB,acompressor=threshold=-24dB:ratio=2.5:attack=10:release=150,afade=t=in:d=0.03",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-c:a", "aac", "-b:a", "192k", "-ac", "2", p])
        parts.append(p)
    lst = os.path.join(work, "list.txt")
    with open(lst, "w", encoding="utf-8") as f:
        f.write("".join(f"file '{p}'\n" for p in parts))
    joined = os.path.join(work, "joined.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
    dur = duration(joined)

    heard = words(joined, plan.get("language", "en"), prompt=" ".join(plan.get("phrases", [])) or None)
    w = cap.align_to_script(cap.apply_spelling(heard, plan.get("spelling", {})), plan.get("script", ""))
    pages = cap.build_pages(w, cap.clip_spans(plan["clips"]), dur, plan.get("keywords", []), plan.get("phrases", []))
    pages_path = os.path.join(out_dir, f"{name}_pages.json")
    with open(pages_path, "w", encoding="utf-8") as f:
        json.dump(pages, f, indent=1, ensure_ascii=False)
    with open(os.path.join(work, "words.json"), "w", encoding="utf-8") as f:
        json.dump({"heard": heard, "aligned": w}, f, ensure_ascii=False)

    mix = os.path.join(work, "mix.wav")
    if plan.get("music"):
        fc = (f"[1:a]aloop=loop=-1:size=2e9,atrim=0:{dur},volume={plan.get('music_db', -16)}dB,afade=t=in:d=0.8,"
              f"afade=t=out:st={max(dur - 1.2, 0)}:d=1.2[m];[0:a]asplit[v1][v2];"
              f"[m][v2]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[md];"
              f"[v1][md]amix=inputs=2:duration=first:normalize=0[a]")
        run(["ffmpeg", "-v", "error", "-y", "-i", joined, "-i", plan["music"], "-filter_complex", fc, "-map", "[a]", "-ar", "48000", mix])
    else:
        run(["ffmpeg", "-v", "error", "-y", "-i", joined, "-vn", "-ar", "48000", mix])
    meas = run(["ffmpeg", "-v", "info", "-i", mix, "-af", f"loudnorm=I={FINAL_LUFS}:TP={FINAL_TP}:LRA=11:print_format=json",
                "-f", "null", "-"]).stderr
    mj = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
    ln = (f"loudnorm=I={FINAL_LUFS}:TP={FINAL_TP}:LRA=11:measured_I={mj['input_i']}:measured_TP={mj['input_tp']}:"
          f"measured_LRA={mj['input_lra']}:measured_thresh={mj['input_thresh']}:offset={mj['target_offset']}:linear=true")

    nocap = os.path.join(out_dir, f"{name}_nocap.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-i", joined, "-i", mix, "-filter_complex", f"[1:a]{ln},aresample=48000[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", nocap])

    ass = os.path.join(work, "caps.ass")
    with open(ass, "w", encoding="utf-8") as f:
        f.write(cap.ass_file(pages))
    ass_f = ass.replace("\\", "/").replace(":", "\\:")
    with_ass = os.path.join(out_dir, f"{name}_ass.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-i", nocap, "-vf", f"subtitles='{ass_f}'", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", with_ass])
    return {"nocap": nocap, "pages": pages_path, "ass": with_ass, "duration": round(dur, 2), "pages_count": len(pages),
            "loudness": loudness_report(nocap)}
