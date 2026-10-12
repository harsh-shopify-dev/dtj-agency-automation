"""Proves the original page (/) did not change: compares its rendered HTML (scripts, chunk URLs and
links stripped) with the saved baseline in ../assets/original-page-baseline.txt.

  python diff_original.py              # compare; exits 1 and prints the differing lines if / changed
  python diff_original.py --update     # save the current / as the new baseline (only after Harsh
                                       # asked for a change to / and it is done and verified)
"""
import argparse
import difflib
import re
import sys
import urllib.request
from pathlib import Path

BASELINE = Path(__file__).resolve().parent.parent / "assets" / "original-page-baseline.txt"


def normalized(html: str) -> list[str]:
    html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S)  # RSC payload and loaders
    html = re.sub(r"<(link|script)\b[^>]*>", "", html)                    # chunk URLs change per compile
    html = re.sub(r"(/_next/static/[^\"' ]+)", "/_next/static/X", html)
    return re.sub(r">\s*<", ">\n<", html).split("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:3100")
    ap.add_argument("--update", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    with urllib.request.urlopen(f"{args.base}/", timeout=180) as r:
        now = normalized(r.read().decode("utf-8"))
    if args.update or not BASELINE.exists():
        BASELINE.write_text("\n".join(now), encoding="utf-8")
        print(f"Baseline saved ({len(now)} lines): {BASELINE}")
        return
    before = BASELINE.read_text(encoding="utf-8").split("\n")
    diff = [l for l in difflib.unified_diff(before, now, lineterm="", n=0) if not l.startswith(("---", "+++", "@@"))]
    if not diff:
        print(f"Original page unchanged ({len(now)} lines).")
        return
    print(f"Original page CHANGED: {len(diff)} differing lines")
    for line in diff[:40]:
        print("  ", re.sub(r'class="[^"]*"', 'class=…', line)[:200])
    sys.exit(1)


if __name__ == "__main__":
    main()
