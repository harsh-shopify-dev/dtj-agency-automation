"""Run the page builder end to end on this machine: build -> Claude copy step -> screenshot review loop -> files for a person to approve.
It never talks to a store. Pushing the template to an unpublished theme is a separate, approved step.

    cd services/store-builder
    python -m page_builder.run_page --example toilova --out ../../.work/pages/toilova            # copy step as a DRY RUN (no API call)
    python -m page_builder.run_page --brand b.json --facts f.json --out OUT --media PICS          # a real client's facts and pictures
    python -m page_builder.run_page --example toilova --out OUT --copy live                       # ONE Claude API call (needs ANTHROPIC_API_KEY)

Writes into OUT: template.json (the page), build-report.json (every design decision and its reason), copy.json (the copy step: request,
accepted and rejected lines, usage, cost), review.json (the review loop), preview.html and page-390.png / page-1280.png.
Exit code: 0 = pass, 2 = needs human, 1 = could not run.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .assemble import InputError, build_pdp
from .browser import BrowserError, EdgeBrowser
from .copy_step import make_client, run_copy_step
from .examples import fixtures
from .review import review_page


def _load(args) -> tuple[dict, dict]:
    if args.example:
        if args.example == "toilova":
            return fixtures.toilova()
        if args.example in fixtures.BRANDS:
            b, f = fixtures.BRANDS[args.example]
            return json.loads(json.dumps(b)), json.loads(json.dumps(f))
        raise SystemExit(f"unknown example {args.example!r}: toilova, {', '.join(fixtures.BRANDS)}")
    if not (args.brand and args.facts):
        raise SystemExit("give --example NAME, or both --brand and --facts")
    return json.loads(Path(args.brand).read_text(encoding="utf-8")), json.loads(Path(args.facts).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None, *, browser=None, client=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--example", help="toilova or one of the synthetic test brands")
    src.add_argument("--brand", help="brand profile JSON (schemas/brand-profile.schema.json)")
    ap.add_argument("--facts", help="product facts JSON (schemas/product-facts.schema.json)")
    ap.add_argument("--out", required=True, help="output folder (use .work/ so nothing lands in git)")
    ap.add_argument("--media", help="folder holding the real picture files named in the facts")
    ap.add_argument("--copy", choices=("off", "dry", "live"), default="dry", help="Claude copy step: off, dry run (default) or ONE live API call")
    ap.add_argument("--no-browser", action="store_true", help="skip the screenshot review loop (build and copy step only)")
    ap.add_argument("--rounds", type=int, default=2, help="review rounds (default 2)")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):  # a Windows console (cp1252) cannot print characters such as the review stars
        sys.stdout.reconfigure(errors="replace")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    media = Path(args.media) if args.media else None
    try:
        brand, facts = _load(args)
        first = build_pdp(brand, facts)
    except (InputError, ValueError, OSError) as exc:
        print(f"could not build the page: {exc}", file=sys.stderr)
        return 1

    # ---- 1. the Claude copy step (only structural signposts; every line checked by code)
    copy_report, overrides = {"status": "off"}, {}
    if args.copy != "off":
        live_client = client
        if args.copy == "live" and live_client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                print("--copy live needs ANTHROPIC_API_KEY in this shell's environment (from the vault). Not set: nothing was called.", file=sys.stderr)
                return 1
            live_client = make_client()
        outcome = run_copy_step(brand, facts, client=live_client if args.copy == "live" else None, first=first)
        copy_report = outcome.as_report()
        copy_report["request"] = {k: v for k, v in outcome.params.items() if k != "system"}  # the exact call (the system prompt is in prompts/system.md)
        overrides = outcome.accepted
    (out / "copy.json").write_text(json.dumps(copy_report, indent=1, ensure_ascii=False), encoding="utf-8")

    # ---- 2. the screenshot review loop
    if args.no_browser:
        final = build_pdp(brand, facts, copy_overrides=overrides or None)
        review = {"verdict": "not reviewed (--no-browser)"}
    else:
        try:
            br = browser or EdgeBrowser(work=out / "_browser")
            review = review_page(brand, facts, out_dir=out, browser=br, copy_overrides=overrides, max_rounds=args.rounds, media_dir=media)
        except BrowserError as exc:
            print(f"review loop could not run: {exc}", file=sys.stderr)
            return 1
        final = review.pop("_result")
    (out / "template.json").write_text(json.dumps(final.template, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "build-report.json").write_text(json.dumps(final.report, indent=1, ensure_ascii=False), encoding="utf-8")

    lint_errors = [f for f in final.report["lint"] if f["severity"] == "error"]
    print(f"page: {brand['brand_name']} ({brand['category']}) | sections {len(final.report['sections_built'])} built, "
          f"{len(final.report['sections_omitted'])} omitted | lint errors {len(lint_errors)} | build problems {len(final.report['problems'])}")
    print(f"copy step: {copy_report.get('status')} | accepted {len(copy_report.get('accepted', {}))} | rejected {len(copy_report.get('rejected', {}))}"
          + (f" | cost ${copy_report['cost_usd']}" if copy_report.get("cost_usd") is not None else ""))
    if "rounds" in review:
        last = review["rounds"][-1]
        print(f"review: {review['verdict']} after {len(review['rounds'])} round(s) | errors {last['errors']} | warnings {last['warnings']} | "
              f"reverted copy lines {len(review['reverted_copy'])} | screenshots {', '.join(review['screenshots'].values())}")
        for f in last["findings"]:
            print(f"  [{f['severity']}] {f['check']} @{f['width']}px {f['section'] or ''}: {f['message']}")
    else:
        print(f"review: {review['verdict']}")
    print(f"files: {out.resolve()}")
    passed = review.get("verdict") == "pass" and not lint_errors and not final.report["problems"]
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
