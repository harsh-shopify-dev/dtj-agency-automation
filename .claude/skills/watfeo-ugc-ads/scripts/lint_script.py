"""Check a WATFEO ad script against the house rules before a single credit is spent.

    python scripts/lint_script.py ads/book-03/script.json          exit 0 = clean, 2 = fix the problems listed
    python scripts/lint_script.py script.json --lines-only         a writing job: check the spoken lines only (no setup/prompts yet)

script.json (see references/script-format.md):
  {"ad": "book-03", "angle": 56, "language": "en|hi|hinglish", "setup": "<the one set, described once>",
   "creator": "<persona id from references/creators.md>",
   "shots": [{"id": "s1", "seconds": 8, "line": "...", "book": "<book state for the whole clip>",
              "image_prompt": "...", "video_prompt": "..."}]}

What it refuses, and why (each rule came from a correction by Harsh or a failed take):
- an opening that copies earlier ads ("Okay so...", "So there's this part...")       -> scripts started sounding the same
- a last clip without a spoken CTA (Read Now / Shop Now / Abhi padhe), or "link in bio" -> Harsh's CTA rule
- the book title and author missing from the closing lines                            -> nobody knows what to buy
- a name that is not in the manuscript                                                -> "don't use any name not in the book"
- a number that is neither in the book nor in the official facts                      -> no invented claims
- the reserved terrace rescue scene                                                   -> parked: most likely to get the ad restricted
- more than 3 words a second, lengths other than 4/6/8/10 s                           -> Omni Flash rushes or cuts the line
- AI-ad words in prompts, a clip with no phone setup, a book shot with no "stays" rule -> AI slop, book drops and floats
- more than one setup                                                                 -> "in no UGC video we will use different setup"
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = re.sub(r"\s+", " ", (ROOT / "assets" / "book_full_text.txt").read_text(encoding="utf-8")).lower()
# The official site's claims (sagarchudesara.com, read 20 Oct 2026); see references/book-bible.md "Allowed claims".
SITE_FACTS = ("national bestseller", "national best seller", "2,00,000+ copies sold", "2 lakh copies", "two lakh copies",
              "hand-signed letter", "signed letter", "free bookmark", "official website")
SECONDS = (4, 6, 8, 10)
CTA = re.compile(r"\b(read now|shop now|abhi padh(e|o|iye)|abhi padhe)\b", re.I)
NO_CTA = re.compile(r"link (in|is in) (my |the )?bio|link bio mein", re.I)
STALE_OPENERS = re.compile(r"^\s*(okay|ok)\s*,?\s*so\b|^\s*so\s+there'?s\s+this\b|^\s*so\s+there\s+is\s+this\b", re.I)
RESERVED = re.compile(r"suicid|jump(ed|ing)? off|terrace (edge|railing|ledge)|papa,? i am coming|end (her|my) life", re.I)
SLOP = ("cinematic", "studio", "flawless", "perfect skin", "porcelain", "airbrushed", "8k", "4k", "ultra-detailed", "ultra detailed",
        "hyperrealistic", "hyper-realistic", "photorealistic", "masterpiece", "professional photo", "commercial", "bokeh",
        "dramatic lighting", "softbox", "ring light", "glossy", "beautiful lighting", "perfect composition", "perfectly symmetrical")
NEGATED = re.compile(r"\b(no|not|avoid|without|never|don't|do not|zero)\b[^.;]{0,40}$", re.I)


def slop_in(text: str) -> list[str]:
    """AI-ad words used as wishes. "No studio light" / "avoid glossy skin" / "not symmetrical" ask for the opposite: allowed."""
    t, found = text.lower(), []
    for w in SLOP:
        for m in re.finditer(re.escape(w), t):
            if not NEGATED.search(t[max(0, m.start() - 60):m.start()]):
                found.append(w); break
    return found


CAMERA = re.compile(r"handheld|selfie|propped|phone|front camera|arm.s length|held by a friend|on a stand", re.I)
STAYS = re.compile(r"\b(same|steady|steadily|keeps?|holds?|still|never (drops|leaves|moves))\b", re.I)
COMMON = set("""I I'm I've I'd Okay Ok Yes No Like Honestly And But So The This That It It's Every Tell Read Shop Now Comment Yaar Arre
Matlab Basically Literally Toh Na Hai Ki Ka Ke Mein Abhi Padhe Book Books Page Chapter Instagram WhatsApp Hindi English Mumbai Hampi
Surat Bangalore Bengaluru Kochi Kerala God India Indian Sunday Monday Friday We Are There For Each Other Sagar Chudesara You Your
What Why When How Who Where Which Wait One Two Three Four Five Also Then Just Even Real Seriously Guys Mmm Hmm Oh Ah""".split())
_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def num_word(n: int) -> str | None:
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("" if n % 10 == 0 else "-" + _ONES[n % 10])
    return None


NUM_WORDS = {num_word(n): str(n) for n in range(6, 100)}   # one-five are counting words ("which one"), not claims
NUM_WORDS = dict(sorted(NUM_WORDS.items(), key=lambda kv: -len(kv[0])))   # "ninety-six" before "six"


def number_claims(text: str) -> list[tuple[str, str]]:
    """Each number with the word after it ("5 lakh", "96%", "10 days") and a pattern that finds it in the book as a whole number
    ("5 lakh" must not match inside "25 lakh")."""
    t = text.lower()
    for w, d in NUM_WORDS.items():
        t = re.sub(rf"\b{w}\b", d, t)
    claim_nouns = r"lakh|crore|thousand|hundred|million|percent|copies|readers|reviews|stars|years|days|weeks|months|kgs?|rupees"
    for w, d in (("one", "1"), ("two", "2"), ("three", "3"), ("four", "4"), ("five", "5")):
        t = re.sub(rf"\b{w}(?=\s+(?:{claim_nouns})\b)", d, t)   # "two lakh copies" is a claim; "which one" is not
    out = []
    for m in re.finditer(r"(\d[\d,]*)\s*(%|percent\b|[a-z]+)?", t):
        num, nxt = m.group(1).replace(",", ""), (m.group(2) or "")
        if num in ("1", "2", "3", "4", "5") and nxt in ("", "of", "and", "people", "friends", "things", "times", "minutes", "seconds"):
            continue                              # "these four people", "one of": counting, not a claim
        nxt = "%" if nxt.startswith("percent") else nxt
        digits = r",?".join(num)                  # 200000 also matches 2,00,000 and 200,000
        word = num_word(int(num)) if len(num) <= 2 else None
        alt = rf"(?:(?<![\d,]){digits}(?![\d,])\+?" + (rf"|\b{word}\b" if word else "") + ")"
        pat = rf"{alt}\s*{re.escape(nxt)}" if nxt else alt
        out.append((m.group(0).strip(), pat))
    return out


def claim_ok(pat: str) -> bool:
    return bool(re.search(pat, BOOK)) or any(re.search(pat, f) for f in SITE_FACTS)


def lint(script: dict, lines_only: bool = False) -> tuple[list[str], list[str]]:
    """lines_only: a writing job (scripts before any prompts exist): skip the setup and prompt checks."""
    bad, warn = [], []
    shots = script.get("shots") or []
    if script.get("language") not in ("en", "hi", "hinglish"):
        bad.append("language must be en, hi or hinglish")
    if not script.get("setup") and not lines_only:
        bad.append("give the ONE setup (room, light, wardrobe, phone position) in 'setup'; every clip uses it")
    if any(s.get("setup") and s["setup"] != script.get("setup") for s in shots):
        bad.append("a shot has its own setup: one setup for the whole ad (change a prop, never the room)")
    slop = slop_in(str(script.get("character", "")))
    if slop and not lines_only:
        bad.append(f"the character prompt uses AI-ad words {slop}")
    if not 3 <= len(shots) <= 7:
        bad.append(f"{len(shots)} clips: an ad has 3 to 7")
    total = 0
    for s in shots:
        sid, line = s.get("id", "?"), str(s.get("line", ""))
        sec = s.get("seconds")
        if sec not in SECONDS:
            bad.append(f"{sid}: seconds must be one of {SECONDS}")
        else:
            total += sec
            n = len(line.split())
            if n > 3.0 * sec:
                bad.append(f"{sid}: {n} words in {sec} s is too fast (at most {int(3 * sec)})")
            if n < 1.2 * sec and sid != shots[-1].get("id"):
                warn.append(f"{sid}: only {n} words in {sec} s: dead air, or a shorter clip")
        if RESERVED.search(line + " " + str(s.get("video_prompt", ""))):
            bad.append(f"{sid}: the terrace rescue scene is reserved (parked by Harsh until every other angle has run)")
        for said, pat in number_claims(line):
            if not claim_ok(pat):
                bad.append(f"{sid}: {said!r} is not in the book or the official facts (no invented numbers)")
        # Mid-sentence capitals are names or details; check them always. A sentence's first word is checked in English only:
        # in Hindi/Hinglish it is usually an ordinary word ("Uski", "Tabhi", "Dono") the English manuscript does not contain.
        words = re.findall(r"(?<![.!?…]\s)(?<![.!?…])(?<!^)(?<=\s)([A-Z][a-z]{2,})\b", line)
        if script.get("language") == "en":
            words += [m.group(1) for m in re.finditer(r"(?:^|[.!?…]\s+)([A-Z][a-z]{2,})\b", line)]
        for w in words:
            stems = {w.lower(), re.sub(r"(ing|ed|es|s)$", "", w.lower())}   # "Sends" is a verb if "send" is in the book
            if w not in COMMON and not any(re.search(rf"\b{re.escape(x)}", BOOK) for x in stems if len(x) > 2):
                bad.append(f"{sid}: {w!r} is not in the book: never use a name or detail the book does not have")
        if lines_only:
            continue
        for field in ("image_prompt", "video_prompt"):
            slop = slop_in(str(s.get(field, "")))
            if slop:
                bad.append(f"{sid}: {field} uses AI-ad words {slop}")
        vp = str(s.get("video_prompt", ""))
        if not CAMERA.search(vp):
            bad.append(f"{sid}: video_prompt must say how the phone films it (selfie at arm's length, phone on a stand, propped)")
        if s.get("book") and not STAYS.search(vp):
            bad.append(f"{sid}: the book is in this clip: the video_prompt must say how it stays (held steadily, never drops)")
        if line and line.strip('"') not in vp:
            warn.append(f"{sid}: the video_prompt should quote the exact line, so the voice says it word for word")
    if not 20 <= total <= 60:
        bad.append(f"{total} s in total: keep an ad between 20 and 60 s")
    if shots:
        first, last = str(shots[0].get("line", "")), str(shots[-1].get("line", ""))
        if STALE_OPENERS.search(first):
            bad.append("s1 opens like earlier ads ('Okay so...' / 'So there's this...'): find a new first line")
        if not CTA.search(last):
            bad.append("the last clip must end with a spoken CTA: Read Now, Shop Now or Abhi padhe")
        if any(NO_CTA.search(str(s.get("line", ""))) for s in shots):
            bad.append("do not say 'link in bio': use Read Now / Shop Now / Abhi padhe")
        closing = " ".join(str(s.get("line", "")) for s in shots[-2:]).lower()
        if "we are there for each other" not in closing:
            bad.append("say the title 'We Are There For Each Other' in the last two clips")
        if "sagar chudesara" not in closing:
            warn.append("the author's name (Sagar Chudesara) is usually said with the title")
    return bad, warn


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print(__doc__); return 1
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    lines_only = "--lines-only" in argv
    argv = [a for a in argv if a != "--lines-only"]
    script = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    bad, warn = lint(script, lines_only)
    secs = sum(s.get("seconds", 0) for s in script.get("shots", []))
    credits = sum({4: 14, 8: 24}.get(s.get("seconds"), 0) for s in script.get("shots", []))
    print(json.dumps({"ok": not bad, "problems": bad, "warnings": warn, "seconds": secs,
                      "flow_credits_one_round": credits or "not available (6/10 s clips)"}, indent=1, ensure_ascii=False))
    return 0 if not bad else 2


if __name__ == "__main__":
    raise SystemExit(main())
