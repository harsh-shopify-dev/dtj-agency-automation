"""The angle ledger: which of the 58 book angles have been made into ads, and which are still fresh.

    python scripts/angles.py list                  every angle, fresh ones first
    python scripts/angles.py fresh                 only the angles never used
    python scripts/angles.py show 56               one angle: section, title, book anchor, starting hook
    python scripts/angles.py use 56 --ad book-02 --note "which friend are you"    record that an ad used it

The ledger lives in assets/angle-ledger.json (built from references/angle-bank.md the first time). A team that shares this
skill should also record each ad in their shared tracker (DTJ: the n8n table dtj_watfeo_ads), so two laptops do not reuse one angle.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "references" / "angle-bank.md"
LEDGER = ROOT / "assets" / "angle-ledger.json"


def parse_bank() -> list[dict]:
    angles, section = [], ""
    for line in BANK.read_text(encoding="utf-8").splitlines():
        h = re.match(r"^## \d+\.\s*(.+)", line)
        if h:
            section = h.group(1).strip().title()
            continue
        m = re.match(r"^(\d+)\.\s+\*\*(.+?)\*\*\s*(`\[USED[^`]*\]`)?\s*[—-]?\s*(.*)$", line)
        if m:
            rest = m.group(4)
            anchor = (re.search(r"\*(.+?)\*", rest) or [None, ""])[1]
            hook = (re.search(r"→\s*\"?(.+?)\"?\s*$", rest) or [None, ""])[1]
            angles.append({"no": int(m.group(1)), "section": section, "title": m.group(2), "pain": rest.split("*")[0].strip(" —-"),
                           "anchor": anchor, "hook": hook, "used": [{"ad": "before Oct 2026", "note": m.group(3).strip("`")}] if m.group(3) else []})
    return angles


def load() -> list[dict]:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    data = parse_bank()
    save(data)
    return data


def save(data: list[dict]) -> None:
    LEDGER.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


def line(a: dict) -> str:
    tag = f"USED x{len(a['used'])}" if a["used"] else "fresh"
    return f"#{a['no']:>2} [{tag:7}] {a['section'][:26]:26} {a['title']}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list"); sub.add_parser("fresh")
    s = sub.add_parser("show"); s.add_argument("no", type=int)
    u = sub.add_parser("use"); u.add_argument("no", type=int); u.add_argument("--ad", required=True); u.add_argument("--note", default="")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    data = load()
    by = {x["no"]: x for x in data}
    if a.cmd in ("list", "fresh"):
        for x in sorted(data, key=lambda x: (bool(x["used"]), x["no"])):
            if a.cmd == "list" or not x["used"]:
                print(line(x))
        print(f"\n{sum(1 for x in data if not x['used'])} fresh of {len(data)}")
        return 0
    if a.no not in by:
        print(f"no angle #{a.no} (1-{max(by)})", file=sys.stderr); return 1
    x = by[a.no]
    if a.cmd == "show":
        print(json.dumps(x, indent=1, ensure_ascii=False)); return 0
    x["used"].append({"ad": a.ad, "note": a.note, "date": dt.date.today().isoformat()})
    save(data)
    print(f"recorded: {line(x)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
