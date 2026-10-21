"""Find a phrase, name or fact in "We Are There For Each Other" (the full manuscript in assets/book_full_text.txt).

    python scripts/book_search.py "crossing roads"                 every hit with the text around it and its page
    python scripts/book_search.py "six[- ]?pack" --regex --max 3
    python scripts/book_search.py --chapter 21                      the start of chapter 21
    python scripts/book_search.py --names "Kanika" "Devaki"         is each name in the book? (never use a name that is not)

Every story detail in a script (who did what, a number, a quote, a place) must be found here before it is used.
Page numbers are the printed page markers in the manuscript ([page 106 ...]); they are approximate for text near a page break.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BOOK = Path(__file__).resolve().parents[1] / "assets" / "book_full_text.txt"


def load() -> str:
    return BOOK.read_text(encoding="utf-8")


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def page_at(text: str, pos: int) -> str:
    m = list(re.finditer(r"\[page (\d+)", text[:pos]))
    return f"p.{int(m[-1].group(1)) + 1}" if m else "front matter"


def search(pattern: str, regex: bool = False, max_hits: int = 5, width: int = 220) -> list[dict]:
    t = flat(load())
    p = pattern if regex else re.escape(pattern).replace(r"\ ", r"\s+")
    hits = []
    for m in re.finditer(p, t, re.I):
        hits.append({"page": page_at(t, m.start()), "text": t[max(0, m.start() - width):m.end() + width]})
        if len(hits) >= max_hits:
            break
    return hits


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pattern", nargs="?")
    ap.add_argument("--regex", action="store_true")
    ap.add_argument("--max", type=int, default=5)
    ap.add_argument("--width", type=int, default=220)
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--names", nargs="+")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t = flat(load())
    if a.names:
        for n in a.names:
            c = len(re.findall(rf"\b{re.escape(n)}\b", t))
            print(f"{n}: {c} mention(s){'' if c else '  <- NOT IN THE BOOK: do not use this name'}")
        return 0
    if a.chapter:
        m = re.search(rf"Chapter\s*{a.chapter}\b(.{{0,1500}})", t)
        print(m.group(0) if m else f"chapter {a.chapter} not found")
        return 0 if m else 1
    if not a.pattern:
        ap.error("give a pattern, --chapter or --names")
    hits = search(a.pattern, a.regex, a.max, a.width)
    total = len(re.findall(a.pattern if a.regex else re.escape(a.pattern).replace(r"\ ", r"\s+"), t, re.I))
    print(f"{total} hit(s) for {a.pattern!r}" + (f" (showing {len(hits)})" if total > len(hits) else ""))
    for h in hits:
        print(f"\n[{h['page']}] ...{h['text']}...")
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
