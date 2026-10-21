"""Catch AI-written script tells before a line is ever spoken, and compare a script with a niche's real creators.

    python -m reel_factory.slop script.json [--style <lib>/style.json]      exit 0 = sounds like a creator, 2 = rewrite

Two kinds of checks:
1. Tells: phrases and shapes that models reach for and Instagram creators almost never say (ad-speak, "It's not X, it's Y",
   "Let that sink in", tidy lists of three, explaining the feeling, formal "shuddh" Hindi). Each hit says what to do instead.
2. Numbers (with --style): the script's words per second, sentence length, fillers, Hindi share, questions and "you" must land
   inside the niche's real-reel range (style.json from reel_factory.library). Outside = it will sound written, not said.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from .library import DEVANAGARI, FILLERS_EN, FILLERS_HI, ROMAN_HINDI, YOU

# (pattern, why it reads as AI, what a creator would do)
TELLS = [
    (r"\bit'?s not (just )?(about )?[^.,!?]{1,40}[,;—-]+\s*it'?s\b", "the 'It's not X, it's Y' turn", "say the Y part plainly"),
    (r"\blet that sink in\b", "AI drama line", "pause or react instead"),
    (r"\bhere'?s the (thing|truth|kicker|catch)\b", "AI set-up line", "just say the thing"),
    (r"\b(imagine|picture this)\b[^.]{0,30}\b(a world|if)\b", "'Imagine a world...' opener", "start with what happened"),
    (r"\b(game[- ]?changer|elevate|unlock|unleash|revolutioni[sz]e|seamless(ly)?|effortless(ly)?|curated|crafted|indulge|delight(ful)?)\b",
     "ad-speak", "the plain word you'd say to a friend"),
    (r"\b(say goodbye to|look no further|whether you'?re|in today'?s (fast[- ]paced )?world|the secret to|level up|take it to the next level)\b",
     "ad cliche", "a concrete detail instead"),
    (r"\b(perfect blend|rich aroma|bursting with flavou?r|melt[- ]in[- ]your[- ]mouth|taste the difference|guilt[- ]free|wholesome goodness)\b",
     "food-ad cliche", "describe what you actually notice: the crunch, the smell, the first sip"),
    (r"\b(experience|discover|explore) (the|a|our)\b", "brochure verb", "use 'try', 'had', 'tasted'"),
    (r"\byou deserve\b|\btreat yourself\b", "ad-speak", "drop it"),
    (r"\bi (felt|feel) (so )?(seen|understood|heard)\b", "therapy-speak", "show the reaction, don't name it"),
    (r"\b(trust me|believe me),? you'?ll\b", "salesy promise", "let the reaction sell it"),
    (r"\b(atyant|uttam|swadisht|anubhav|prastut|sampoorn|vishesh|uplabdh|labhdayak|swasthya ke liye)\b",
     "formal Hindi no creator says on a reel", "everyday Hindi: 'bohot tasty', 'try karo', 'mast'"),
    (r"(उत्तम|अत्यंत|स्वादिष्ट|अनुभव|प्रस्तुत|संपूर्ण|विशेष|उपलब्ध|लाभदायक)", "formal Hindi", "everyday Hindi"),
]
LIST_OF_THREE = re.compile(r"\b\w+(?:\s\w+)?, \w+(?:\s\w+)?,? (?:and|aur|or) \w+", re.I)


def lines_of(script: dict) -> list[str]:
    return [str(s.get("line") or s.get("spoken_line") or "") for s in script.get("shots") or script.get("clips") or []]


def measure_text(lines: list[str], seconds: float) -> dict:
    text = " ".join(lines)
    toks = text.split()
    n = len(toks)
    low = [re.sub(r"[^\wऀ-ॿ']", "", t.lower()) for t in toks]
    sentences = [s for s in re.split(r"(?<=[.!?।])\s+", text) if s.strip()]
    fill = sum(f" {text.lower()} ".count(" " + f + " ") for f in FILLERS_EN) + sum(1 for t in low if t in FILLERS_HI)
    return {"words_per_s": round(n / max(seconds, 1), 2), "sentence_words": round(n / max(len(sentences), 1), 1),
            "questions_per_30s": round(text.count("?") * 30 / max(seconds, 1), 2),
            "you_per_100w": round(len(YOU.findall(text)) * 100 / max(n, 1), 1),
            "fillers_per_100w": round(fill * 100 / max(n, 1), 1),
            "hindi_share": round(sum(1 for t in low if DEVANAGARI.search(t) or t in ROMAN_HINDI) / max(n, 1), 2)}


def check(script: dict, style: dict | None = None) -> dict:
    lines = lines_of(script)
    text = " ".join(lines)
    tells = []
    for pat, why, fix in TELLS:
        for m in re.finditer(pat, text, re.I):
            tells.append({"said": m.group(0), "why": why, "instead": fix})
    if len(LIST_OF_THREE.findall(text)) >= 2:
        tells.append({"said": "; ".join(LIST_OF_THREE.findall(text)[:2]), "why": "more than one tidy list of three", "instead": "break the rhythm"})
    if text.count("—") + text.count(" - ") >= 3:
        tells.append({"said": "dashes", "why": "dash-heavy rhythm reads as written", "instead": "use '...' or a new sentence"})
    if text.count("!") > max(2, len(lines) // 2):
        tells.append({"said": "!", "why": "too many exclamation marks", "instead": "energy comes from the delivery, not the punctuation"})
    seconds = sum(s.get("seconds", 0) for s in script.get("shots") or script.get("clips") or []) or 30
    nums = measure_text(lines, seconds)
    off = {}
    if style:
        lang = script.get("language", "en")
        for k, v in nums.items():
            r = style.get("ranges", {}).get(k)
            # Whisper writes Hindi in Devanagari, so a library's hindi_share only compares with a Devanagari script;
            # Roman Hindi is counted from a short word list and would always look "too English".
            if not r or (k == "hindi_share" and (lang == "en" or not DEVANAGARI.search(text))):
                continue
            lo, hi = r["p20"], r["p80"]
            if lo == hi:
                continue
            if v < lo * 0.85 or v > hi * 1.15:
                off[k] = {"script": v, "real_creators_20_80": [lo, hi]}
    return {"ok": not tells and not off, "tells": tells, "numbers": nums, "outside_real_range": off}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script")
    ap.add_argument("--style")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    script = json.loads(Path(a.script).read_text(encoding="utf-8"))
    style = json.loads(Path(a.style).read_text(encoding="utf-8")) if a.style else None
    res = check(script, style)
    print(json.dumps(res, indent=1, ensure_ascii=False))
    return 0 if res["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
