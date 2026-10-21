"""Update a client's HOME page in the DRAFT theme: only the sections a person picks, and only when every gate passes. One command.

    cd services/store-builder
    python -m page_builder.ship_home --client ../../.work/clients/<client> --list
        the plan for this brand: every home section as MUST, NEEDS FACTS, ADD or SKIP, with its reason. Changes nothing.
    python -m page_builder.ship_home --client ../../.work/clients/<client> --sections auto --store X.myshopify.com --theme 123
        [--fresh] [--client-registry page_builder/clients/<store>.json] [--design-only]
        --sections auto builds the plan; names (hero,best-sellers or all) override it.

The client folder holds brand.json and home-facts.json; the run goes to <client>/home-run. A home page is designed ONLY when someone asks,
and only the chosen sections change (Harsh, 13 Oct 2026). Gates, in order; any failure stops before the store is touched and says why:
  1 run_home: build the page, check the theme is a DRAFT Horizon theme, back up its home page, merge ONLY the chosen sections into it
  2 the build's own gates: lint errors 0, build problems 0 (run_home exit 0)
  3 push_page with the build's own approval code: draft theme only, the home page unchanged since step 1, backup, read-back, action-log row
Harsh's standing rule (10 Oct 2026, home pages added 13 Oct 2026): a page that passes every gate goes to the DRAFT theme without asking. The
live theme stays out of reach: push_page has no live path. SAMPLE values or test pictures go only to a draft preview.

Writes <client>/home-run/ship-result.json. Exit code: 0 = written to the draft (or designed, with --design-only), 2 = needs a person's look,
1 = could not build.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import push_page, run_home

STANDING = "Harsh (standing: draft pushes without asking, home pages included)"


def _quiet(fn, argv: list[str]) -> tuple[int, str]:
    with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
        try:
            code = fn(argv)
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
            print(exc.code if not isinstance(exc.code, int) else "", file=sys.stderr)
    return code, out.getvalue() + err.getvalue()


def main(argv: list[str] | None = None, *, design=run_home.main, push=push_page.main) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--client", required=True, help="the client folder (brand.json, home-facts.json)")
    ap.add_argument("--list", action="store_true", help="show the plan for this brand (must / needs facts / add / skip) and stop")
    ap.add_argument("--sections", help="auto (the plan) or the sections by name, e.g. hero,best-sellers (or all)")
    ap.add_argument("--fresh", action="store_true", help="the home page becomes ONLY the chosen sections (the current page is backed up first)")
    ap.add_argument("--remove", help="sections to switch OFF on the page as it is (names as for --sections; kept in the file)")
    ap.add_argument("--store", help="the store's ORIGINAL .myshopify.com address")
    ap.add_argument("--theme", help="the DRAFT theme's id")
    ap.add_argument("--client-registry", help="the client's app copies (page_builder/clients/<store>.json)")
    ap.add_argument("--approved-by", default=STANDING, help="recorded in the action log (default: Harsh's standing rule for drafts)")
    ap.add_argument("--design-only", action="store_true", help="design and check, never touch the store")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    client = Path(args.client)
    out = client / "home-run"
    build = ["--brand", str(client / "brand.json"), "--facts", str(client / "home-facts.json"), "--out", str(out)]
    if args.client_registry:
        build += ["--client-registry", args.client_registry]
    if args.list:
        return design(build + ["--list"])
    if not args.sections and not args.remove:
        ap.error("say which sections to build or update with --sections auto (the plan) or their names (see --list): a home page changes "
                 "only where you say")
    build += (["--sections", args.sections] if args.sections else []) + (["--fresh"] if args.fresh else []) + (["--remove", args.remove] if args.remove else [])
    if not args.design_only:
        if not (args.store and args.theme):
            ap.error("--store and --theme are needed to write the draft (or use --design-only)")
        build += ["--store", args.store, "--theme", args.theme]

    out.mkdir(parents=True, exist_ok=True)
    result: dict = {"page_status": "", "approve_code": "", "preview_url": "", "sections": [], "not_built": [], "gaps": [], "changes": [], "lint_errors": 0,
                    "build_problems": 0, "samples": 0, "file": run_home.HOME, "theme_id": args.theme or "", "run_folder": str(out.resolve()),
                    "summary": "", "note": "", "finished_at": ""}

    def finish(status: str, code: int, note: str = "") -> int:
        result.update(page_status=status, note=note, finished_at=datetime.now(timezone.utc).isoformat())
        (out / "ship-result.json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{status}: {result['summary'] or note}")
        if result["preview_url"]:
            print(f"preview: {result['preview_url']}")
        if note and result["summary"]:
            print(note)
        return code

    # ---- 1 + 2. build and merge (a stale approval.json from an earlier run must never be pushed: it is removed first)
    (out / "approval.json").unlink(missing_ok=True)
    code, log = _quiet(design, build)
    (out / "ship-build.log").write_text(log, encoding="utf-8")
    if code == 1 or not (out / "approval.json").is_file():
        return finish("could not build", 1, log.strip()[-600:] or "run_home stopped without a message")
    approval = json.loads((out / "approval.json").read_text(encoding="utf-8"))
    report = json.loads((out / "home-report.json").read_text(encoding="utf-8"))
    lint = [f for f in report.get("lint", []) if f.get("severity") == "error"]
    gaps = [{"option": r["option"], "reason": r["reason"]} for r in report.get("plan", []) if r["decision"] == "must_missing"]
    result.update(approve_code=approval["approve_code"], sections=approval["sections"], not_built=report.get("chosen_not_built", []), gaps=gaps,
                  changes=approval["changes"], lint_errors=len(lint), build_problems=len(report.get("problems", [])), samples=approval["samples"])
    result["summary"] = (f"{len(approval['sections'])} section(s) ({', '.join(approval['sections'])}), "
                         f"{sum(1 for c in approval['changes'] if c['change'] == 'replaced')} replaced, "
                         f"{sum(1 for c in approval['changes'] if c['change'] == 'added')} added, "
                         f"{sum(1 for c in approval['changes'] if c['change'] == 'switched off')} switched off, lint errors {len(lint)}, "
                         f"{result['samples']} samples"
                         + (f"; not built: {', '.join(s['option'] for s in result['not_built'])}" if result["not_built"] else "")
                         + (f"; the plan needs facts for: {', '.join(g['option'] for g in gaps)}" if gaps else ""))
    if code != 0:
        why = [f"lint {f.get('rule')}: {f.get('message')}" for f in lint] + [f"build problem: {p}" for p in report.get("problems", [])]
        return finish("needs a look", 2, "; ".join(why))
    if args.design_only:
        return finish("designed (not written)", 0, "design only: run again with --store and --theme to write the draft")

    # ---- 3. write the draft (push_page checks everything again, refuses the live theme and a home page changed since step 1)
    flags = ["--out", str(out), "--approve", approval["approve_code"], "--approved-by", args.approved_by]
    flags += ["--allow-samples"] if approval["samples"] else []
    flags += ["--allow-demo"] if approval.get("demo") else []
    rc, pushed = _quiet(push, flags)
    (out / "ship-push.log").write_text(pushed, encoding="utf-8")
    if rc != 0:
        return finish("needs a look", 2, f"not written: {pushed.strip()[-600:]}")
    result["preview_url"] = f"https://{approval['store']}/?preview_theme_id={approval['theme_id']}"
    return finish("written to draft", 0, "check the real home page next: every changed section, phone and desktop, no sideways scroll")


if __name__ == "__main__":
    raise SystemExit(main())
