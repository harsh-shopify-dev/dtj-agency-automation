"""Caption pages from word timings.

Rules learned on the book-01 and senso-01 runs (20-21 Oct 2026):
- Spelling, capitals and punctuation come from the approved script, not from Whisper (it mishears names, drops words).
- Script words Whisper skipped are slotted in just before the next heard word.
- 1-3 words per page, break on punctuation, never across a cut; named phrases (product name) stay on one page.
- A page never runs past the cut into the next clip; a clip can opt out of captions (cap_margin < 0, e.g. the product shot).
- Placement: Harsh's bottom mark (cap_margin 548 at 1920 high) unless the clip says otherwise.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

BOTTOM_MARK = 548   # text bottom 548 px above the frame bottom at 1080x1920 (text centre ~69 % down)
TOP_MARK = 1608     # only when the top band is empty and the bottom would hide the product name

Word = tuple[str, float, float]   # (text, start s, end s)


def bare(w: str) -> str:
    return re.sub(r"[^\w']", "", w).lower()


NUMS = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight",
        "9": "nine", "10": "ten", "12": "twelve", "15": "fifteen", "20": "twenty", "30": "thirty"}


def same_word(script_word: str, heard: str) -> bool:
    """The heard word is this script word: same letters, a digit for its word ('10' = 'ten'), or a near spelling of a longer
    word ('Arey' = 'Arre', senso test 21 Oct 2026)."""
    a, b = bare(script_word), bare(heard)
    a, b = NUMS.get(a, a), NUMS.get(b, b)
    if a == b:
        return True
    return min(len(a), len(b)) >= 4 and SequenceMatcher(None, a, b).ratio() >= 0.75


def apply_spelling(words: list[Word], spelling: dict[str, str]) -> list[Word]:
    fixes = {k.lower(): v for k, v in (spelling or {}).items()}
    out = []
    for w, a, b in words:
        key = bare(w)
        out.append((re.sub(r"[\w']+", fixes[key], w, count=1) if key in fixes else w, a, b))
    return out


def align_to_script(words: list[Word], script: str, lookahead: int = 4) -> list[Word]:
    """Take each heard word's spelling from the script; insert script words the recogniser skipped."""
    if not script:
        return list(words)
    toks, p, aligned = script.split(), 0, []
    for w, a, b in words:
        k = next((j for j in range(p, min(p + lookahead, len(toks))) if same_word(toks[j], w)), None)
        if k is None:
            aligned.append((w, a, b))
            continue
        miss = toks[p:k]
        if miss:
            prev_end = aligned[-1][2] if aligned else max(0.0, a - 0.4)
            slot = max(0.12 * len(miss), min(0.35 * len(miss), a - prev_end))
            t0 = max(prev_end, a - slot)
            step = (a - t0) / len(miss) if a > t0 else 0.12
            for j, mw in enumerate(miss):
                aligned.append((mw, t0 + j * step, t0 + (j + 1) * step))
            if a <= t0:
                a = t0 + step * len(miss)
        aligned.append((toks[k], a, b))
        p = k + 1
    return aligned


@dataclass
class ClipSpan:
    start: float        # where the clip starts in the joined reel (s)
    cap_margin: int     # caption bottom margin; < 0 = no captions on this clip


def clip_spans(clips: list[dict]) -> list[ClipSpan]:
    spans, acc = [], 0.0
    for c in clips:
        spans.append(ClipSpan(acc, int(c.get("cap_margin", BOTTOM_MARK))))
        acc += c["end"] - c.get("start", 0.0)
    return spans


def _clip_index(spans: list[ClipSpan], t: float) -> int:
    return sum(1 for s in spans if s.start <= t + 0.05)


def _margin(spans: list[ClipSpan], t: float) -> int:
    return [s.cap_margin for s in spans if s.start <= t + 0.01][-1]


def clean_text(w: str) -> str:
    return w.rstrip(",.-").replace("...", "")


def build_pages(words: list[Word], spans: list[ClipSpan], duration: float, keywords=(), phrases=()) -> list[dict]:
    """Caption pages (Remotion's DtjPage shape): text, startMs, durationMs, marginV, keywords[], tokens[]."""
    kw = {k.lower() for k in keywords}
    phr = [p.lower().split() for p in phrases]
    cards, cur, i = [], [], 0
    while i < len(words):
        hit = next((p for p in phr if [bare(x[0]) for x in words[i:i + len(p)]] == p), None)
        if hit:
            if cur:
                cards.append(cur); cur = []
            cards.append(words[i:i + len(hit)]); i += len(hit)
            continue
        cur.append(words[i]); i += 1
        nxt = words[i][1] if i < len(words) else None
        cut = nxt is not None and _clip_index(spans, nxt) != _clip_index(spans, cur[0][1])
        ends = re.search(r"[.,?!-]$", cur[-1][0])
        next_ends = i < len(words) and re.search(r"[.,?!-]$", words[i][0]) and not cut
        if (len(cur) >= 3 and not (len(cur) == 3 and next_ends)) or ends or cut:
            cards.append(cur); cur = []
    if cur:
        cards.append(cur)

    pages = []
    for n, card in enumerate(cards):
        start = card[0][1]
        end = cards[n + 1][0][1] if n + 1 < len(cards) else card[-1][2] + 0.3
        end = min(end, card[-1][2] + 0.6)
        next_cut = min([s.start for s in spans if s.start > start + 0.01] or [duration])
        end = min(end, next_cut - 0.02)
        mid = (card[0][1] + card[-1][2]) / 2
        margin = _margin(spans, mid)
        if margin < 0 or end <= start:
            continue
        is_phrase = [bare(x[0]) for x in card] in phr
        pages.append({
            "text": " ".join(clean_text(w) for w, _, _ in card),
            "startMs": round(start * 1000), "durationMs": round((end - start) * 1000), "marginV": margin,
            "keywords": [bare(w) in kw or is_phrase for w, _, _ in card],
            "tokens": [{"text": clean_text(w), "fromMs": round(a * 1000), "toMs": round(b * 1000)} for w, a, b in card],
        })
    return pages


def ass_file(pages: list[dict], pop: bool = True) -> str:
    """Burned-in fallback captions (libass) with the same pages: white, keywords yellow, optional pop-in."""
    def ts(ms: int) -> str:
        t = ms / 1000; h, t = divmod(t, 3600); m, s = divmod(t, 60)
        return f"{int(h)}:{int(m):02d}:{s:05.2f}"
    lines = []
    for pg in pages:
        words = []
        for j, (tok, key) in enumerate(zip(pg["tokens"], pg["keywords"])):
            t = tok["text"]
            if j == 0:
                t = t[:1].upper() + t[1:]
            words.append(r"{\c&H00D4FF&}" + t + r"{\c&HFFFFFF&}" if key else t)
        anim = r"{\fscx70\fscy70\t(0,90,\fscx112\fscy112)\t(90,170,\fscx100\fscy100)}" if pop else ""
        lines.append(f"Dialogue: 0,{ts(pg['startMs'])},{ts(pg['startMs'] + pg['durationMs'])},Cap,,0,0,{pg['marginV']},,{anim}{' '.join(words)}")
    return ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
            "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Cap,Segoe UI Black,82,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,7,2,2,80,80,548,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n" + "\n".join(lines) + "\n")
