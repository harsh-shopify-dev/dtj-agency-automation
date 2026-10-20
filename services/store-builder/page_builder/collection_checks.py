"""Collection page checks on the template (run_collection's output), before anything is written. The page as shoppers see it (ratings,
swatches, sort, the first screen) is checked on the draft by the skill's check_collection_live.py.

    python -m page_builder.collection_checks --run ../../.work/clients/<client>/collection-run

  CC1 exactly one DTJ Product List on the page, switched on
  CC2 it shows the PAGE's own collection (the dynamic source or empty): a fixed collection would show the same products on every collection
  CC3 the theme's own product grid is switched off: never two grids of the same products
  CC4 exactly one title (H1): our title band on, the theme's old title section off
  CC5 the list is set for a collection page: up to 50 products, count and Sort on, 0-review placeholder ratings hidden, 2 phone columns,
      3-4 laptop columns
  CC6 the app's address is known (not pending): a page with a pending address can be looked at, never written
Writes <run>/collection-checks.json. Exit code: 0 = every check passes, 2 = a finding needs a person's look.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

LIST_REF = re.compile(r"shopify://apps/[a-z0-9-]+/blocks/dtj-product-list/(?P<uuid>[0-9a-f-]{36}|pending)")
PAGE_SOURCES = ("{{ closest.collection }}", "{{closest.collection}}", "{{ collection }}", "{{collection}}", "", None)


def _lists(template: dict) -> list[tuple[str, dict, dict]]:
    out = []
    for sid, sec in template.get("sections", {}).items():
        for block in (sec.get("blocks") or {}).values():
            if LIST_REF.fullmatch(str(block.get("type", ""))):
                out.append((sid, sec, block))
    return out


def check_template(template: dict) -> list[dict]:
    findings = []

    def add(check: str, message: str):
        findings.append({"check": check, "message": message})

    order = template.get("order", [])
    on = [(sid, sec, b) for sid, sec, b in _lists(template) if sid in order and not sec.get("disabled") and not b.get("disabled")]
    if len(on) != 1:
        add("CC1", f"{len(on)} DTJ Product List sections are switched on; a collection page needs exactly one")
    for sid, sec, block in on:
        s = block.get("settings", {})
        if s.get("collection") not in PAGE_SOURCES:
            add("CC2", f"{sid}: the list shows the fixed collection {s.get('collection')!r}; on a collection page it must show the page's own")
        wanted = {"max_products": 50, "show_sort": True, "pf_hide_no_reviews": True, "mobile_columns": "2"}
        for key, value in wanted.items():
            if s.get(key) != value:
                add("CC5", f"{sid}: {key} is {s.get(key)!r}, a collection page needs {value!r}")
        if s.get("columns") not in (3, 4):
            add("CC5", f"{sid}: {s.get('columns')!r} laptop columns; the study's pages use 3 or 4")
        if LIST_REF.fullmatch(block["type"])["uuid"] == "pending":
            add("CC6", "the DTJ Collection app's address is not known yet: place DTJ Product List once in the theme editor, then "
                       "run_collection --learn-uuid, then build again")
    grids = [sid for sid, sec in template.get("sections", {}).items() if sec.get("type") == "main-collection" and sid in order and not sec.get("disabled")]
    if grids:
        add("CC3", f"the theme's own product grid is still on ({', '.join(grids)}): two grids of the same products")
    titles = [sid for sid, sec in template.get("sections", {}).items() if sid in order and not sec.get("disabled")
              and "<h1" in json.dumps(sec.get("blocks", {}))]
    if len(titles) != 1:
        add("CC4", f"{len(titles)} sections carry an H1 title ({', '.join(titles) or 'none'}); a page needs exactly one")
    return findings


def _read(path: Path):
    return json.loads(re.sub(r"^\s*/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.S))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="the folder with template.json (run_collection)")
    a = ap.parse_args(argv)
    run = Path(a.run)
    findings = check_template(_read(run / "template.json"))
    result = {"pass": not findings, "findings": findings}
    (run / "collection-checks.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for f in findings:
        print(f"  {f['check']} {f['message']}")
    print("collection checks: " + ("pass" if not findings else f"{len(findings)} finding(s)"))
    return 0 if not findings else 2


if __name__ == "__main__":
    sys.exit(main())
