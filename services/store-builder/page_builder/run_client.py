"""Design a client's product page for their DRAFT theme, ready for a person to approve. It reads the store but never writes to it.

    cd services/store-builder
    python -m page_builder.run_client --intake row.json --out ../../.work/clients/<brand>          # a dtj_client_intake row (n8n)
    python -m page_builder.run_client --brand b.json --facts f.json --store x.myshopify.com --theme 123456789 --out OUT
        [--reference ref1.png ref2.jpg]   pages the agency likes (inspiration only, max 5)
        [--plan live] [--copy live]       ONE Claude API call each (needs ANTHROPIC_API_KEY); default dry: nothing is called
        [--plan answer --plan-answer F]   the plan / copy written by a Claude Code session instead of the API (current choice, 9 Oct 2026):
        [--copy answer --copy-answer F]   a dry run writes plan-request.json / copy-request.json, the session answers them, the same gate applies
        [--no-theme-check]                design only, without reading the store (nothing can be pushed from such a run)
        [--client-registry F]             the client's own app copies (handle + uuid per app, page_builder/clients/*.json): the page
                                          is designed and reviewed with our blocks, and template.json points at the client's copies

Steps: 1 check the draft theme (Theme Access, read-only: exists, NOT live, a draft, Horizon) and back up its product page;
2 read the product as the store shows it publicly; 3 Claude plans the sections (or the house rules decide); 4 build; 5 Claude copy
step; 6 screenshot review loop; 7 write template.json, the reports, graphics-todo.json and approval.json.

The write to the draft theme is a separate command that needs the approval code printed at the end (page_builder.push_page).
Exit code: 0 = ready for approval, 2 = needs a person's look first, 1 = could not run.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from provision.actionlog import ActionLog
from provision.theme import ThemeError

from . import theme_target as tt
from .ai_plan import ReferenceImageError, apply_answer, plan_request, read_answer, run_plan_step
from .assemble import InputError, build_pdp, picture_in_use
from .browser import BrowserError, EdgeBrowser
from .catalog import Catalog, load_client_registry, to_client
from .copy_step import apply_copy_answer, copy_request, make_client, run_copy_step
from .review import review_page


def _load(args) -> tuple[dict, dict, str | None, str | None, str]:
    if args.intake:
        row = json.loads(Path(args.intake).read_text(encoding="utf-8"))
        if isinstance(row.get("request"), dict):  # the output of n8n's "Request for Claude Code: Page Design" node
            req = row["request"]
            row = {**req, "brand_json": json.dumps(req.get("brand") or {}), "facts_json": json.dumps(req.get("facts") or {})}
        if row.get("status") not in ("new", "approved"):
            raise SystemExit(f"intake row status is {row.get('status')!r}: fix the brief first (problems: {row.get('problems')!r})")
        brand, facts = json.loads(row["brand_json"]), json.loads(row["facts_json"])
        return brand, facts, args.store or row.get("store_domain"), args.theme or row.get("theme_id"), row.get("brand_name") or brand["brand_name"]
    if not (args.brand and args.facts):
        raise SystemExit("give --intake ROW.json, or --brand and --facts")
    brand = json.loads(Path(args.brand).read_text(encoding="utf-8"))
    return brand, json.loads(Path(args.facts).read_text(encoding="utf-8")), args.store, args.theme, brand["brand_name"]


def graphics_todo(result, catalog: Catalog) -> list[dict]:
    """Every picture slot on the page that is still empty and belongs to something on the page: the graphics are made later, by a person."""
    todo = []
    for sec in result.model.sections + result.model.buybox_sections:
        specs = catalog.settings(sec.app, sec.block)
        pictures = {k for k, s in specs.items() if s.get("type") == "image_picker"}
        for key in sorted(pictures, key=lambda k: [int(n) for n in re.findall(r"\d+", k)] or [0]):
            if not sec.settings.get(key) and picture_in_use(key, sec.settings, pictures):
                todo.append({"section": sec.id, "block": f"{sec.app}/{sec.block}", "setting": key, "label": specs[key].get("label", key)})
    for slot in result.report.get("demo_pictures", []):  # test pictures on a dev store: each one still needs the real picture
        todo.append({"slot": slot, "label": "TEST picture (demo): replace with the real one"})
    return todo


def _client(mode: str, given):
    if mode != "live":
        return None
    if given is not None:
        return given
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("a live Claude step needs ANTHROPIC_API_KEY in this shell's environment. Not set: nothing was called.")
    return make_client()


def main(argv: list[str] | None = None, *, browser=None, client=None, access=None, get=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--intake", help="a dtj_client_intake row exported as JSON")
    ap.add_argument("--brand")
    ap.add_argument("--facts")
    ap.add_argument("--store", help="the client's .myshopify.com address")
    ap.add_argument("--theme", help="the DRAFT theme's id")
    ap.add_argument("--out", required=True, help="output folder (use .work/ so nothing lands in git)")
    ap.add_argument("--media", help="folder holding real picture files named in the facts")
    ap.add_argument("--reference", nargs="*", default=[], help="screenshots of pages the agency likes (max 5)")
    ap.add_argument("--plan", choices=("off", "dry", "live", "answer"), default="dry",
                    help="dry: write plan-request.json only; answer: use --plan-answer (written by a Claude Code session); live: Claude API")
    ap.add_argument("--plan-answer", help="the plan answer file (JSON, or {content: [{type: text, text}]})")
    ap.add_argument("--copy", choices=("off", "dry", "live", "answer"), default="dry",
                    help="dry: write copy-request.json only; answer: use --copy-answer; live: Claude API")
    ap.add_argument("--copy-answer", help="the copy answer file")
    ap.add_argument("--no-theme-check", action="store_true")
    ap.add_argument("--template-suffix", help="write a NEW product template templates/product.<suffix>.json (chosen per product) instead "
                                               "of the theme's product.json")
    ap.add_argument("--recipe", default="dtj-standard-v1", choices=("dtj-standard-v1", "pdp"),
                    help="dtj-standard-v1 = the fixed sections every product gets (Harsh, 10 Oct 2026); pdp = the older chosen-section recipe")
    ap.add_argument("--client-registry", help="the client's app copies (handle + uuid per app); without it the page uses our own apps")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--rounds", type=int, default=2)
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    brand, facts, store, theme_id, client_name = _load(args)
    log = ActionLog(out / "action-log.jsonl", client_name)
    catalog = Catalog()

    # ---- 1. the draft theme (read-only)
    target = None
    if not args.no_theme_check:
        if not (store and theme_id):
            print("the store address and the draft theme id are needed (or use --no-theme-check to design only)", file=sys.stderr)
            return 1
        try:
            if access is None:
                token = tt.read_token(store)
                if not token:
                    print(f"no Theme Access password for {store}: save it as the user environment variable {tt.token_env_name(store)} "
                          "(never in a file or in chat). Nothing was read from the store.", file=sys.stderr)
                    return 1
                access = tt.ThemeAccess(store, token)
            target = tt.check_target(access, theme_id, out / "theme-before", tt.template_file(args.template_suffix))
            log.record(tier=0, mode="shadow", target=f"{target['store']} theme {theme_id}", action="check draft theme and back up product page",
                       reason="the page may only ever be written to a draft copy of a Horizon theme", result="success",
                       evidence={"commands": access.commands}, after=target)
        except ThemeError as exc:
            log.record(tier=0, mode="shadow", target=f"{store} theme {theme_id}", action="check draft theme", reason="safety check before designing",
                       result="blocked", error=str(exc))
            print(f"stopped at the theme check: {exc}", file=sys.stderr)
            return 1

    # the page is built in the theme's own layout: Horizon (our base) or Dawn (on the theme's own product.json)
    layout = {"theme": "horizon", "recipe": args.recipe}
    if target and target["base_theme"] == "Dawn":
        from provision import templates as theme_templates
        layout = {"theme": "dawn", "recipe": args.recipe,
                  "base_template": theme_templates.load(Path(target["theme_product_template"]).read_text(encoding="utf-8"))[1]}

    # ---- 2. the product as the store shows it (context for the plan only)
    handle = facts.get("product", {}).get("handle")
    store_product = tt.fetch_store_product(store, handle, get) if (store and handle) else None

    # ---- 3. Claude plans the sections (or the house rules decide)
    for mode, answer in ((args.plan, args.plan_answer), (args.copy, args.copy_answer)):
        if mode == "answer" and not (answer and Path(answer).is_file()):
            print("--plan answer / --copy answer need the answer file (--plan-answer / --copy-answer)", file=sys.stderr)
            return 1
    try:
        if args.plan != "off":
            request = plan_request(brand, facts, references=args.reference, store_product=store_product, catalog=catalog)
            (out / "plan-request.json").write_text(json.dumps(request, indent=1, ensure_ascii=False), encoding="utf-8")
        if args.plan == "answer":
            plan_out = apply_answer(brand, facts, read_answer(args.plan_answer), references=args.reference,
                                    store_product=store_product, catalog=catalog)
        else:
            plan_out = run_plan_step(brand, facts, client=_client(args.plan, client) if args.plan != "off" else None,
                                     references=args.reference, store_product=store_product, catalog=catalog)
    except ReferenceImageError as exc:
        print(f"reference image refused: {exc}", file=sys.stderr)
        return 1
    plan_report = plan_out.as_report() if args.plan != "off" else {"status": "off", "decided_by": f"house rules (recipes/{args.recipe}.json)"}
    if args.recipe == "dtj-standard-v1":
        plan_report["decided_by"] = "the fixed DTJ Standard Product Page v1 sections (recipes/dtj-standard-v1.json)"
    plan_report["store_product"] = store_product
    (out / "plan.json").write_text(json.dumps(plan_report, indent=1, ensure_ascii=False), encoding="utf-8")
    brand2, plan = plan_out.brand, plan_out.plan

    # ---- 4 + 5. build, then the copy step on the planned page
    try:
        first = build_pdp(brand2, facts, plan=plan, catalog=catalog, **layout)
    except (InputError, ValueError) as exc:
        print(f"could not build the page: {exc}", file=sys.stderr)
        return 1
    copy_report, overrides = {"status": "off"}, {}
    if args.copy != "off":
        (out / "copy-request.json").write_text(json.dumps(copy_request(first), indent=1, ensure_ascii=False), encoding="utf-8")
        if args.copy == "answer":
            outcome = apply_copy_answer(brand2, facts, read_answer(args.copy_answer), first=first, plan=plan, catalog=catalog, **layout)
        else:
            outcome = run_copy_step(brand2, facts, client=_client(args.copy, client), first=first, plan=plan, catalog=catalog, **layout)
        copy_report = outcome.as_report()
        overrides = outcome.accepted
    (out / "copy.json").write_text(json.dumps(copy_report, indent=1, ensure_ascii=False), encoding="utf-8")

    # ---- 6. screenshot review loop
    if args.no_browser:
        final, review = (build_pdp(brand2, facts, plan=plan, catalog=catalog, copy_overrides=overrides or None, **layout),
                         {"verdict": "not reviewed (--no-browser)"})
    else:
        try:
            br = browser or EdgeBrowser(work=out / "_browser")
            review = review_page(brand2, facts, out_dir=out, browser=br, copy_overrides=overrides, max_rounds=args.rounds,
                                 media_dir=Path(args.media) if args.media else None, plan=plan, catalog=catalog, **layout)
        except BrowserError as exc:
            print(f"review loop could not run: {exc}", file=sys.stderr)
            return 1
        final = review.pop("_result")

    # ---- 7. files for the approval (pointing at the client's own app copies when it has them)
    try:
        page = to_client(final.template, load_client_registry(args.client_registry)) if args.client_registry else final.template
    except (OSError, ValueError, KeyError) as exc:
        print(f"client registry: {exc}", file=sys.stderr)
        return 1
    body = tt.template_bytes(page)
    (out / "template.json").write_bytes(body)
    (out / "build-report.json").write_text(json.dumps(final.report, indent=1, ensure_ascii=False), encoding="utf-8")
    todo = graphics_todo(final, catalog)
    (out / "graphics-todo.json").write_text(json.dumps(todo, indent=1, ensure_ascii=False), encoding="utf-8")
    lint_errors = [f for f in final.report["lint"] if f["severity"] == "error"]
    ready = review.get("verdict") == "pass" and not lint_errors and not final.report["problems"]
    digest = tt.sha256(body)
    approval = {
        "client": client_name, "store": target["store"] if target else store, "theme_id": target["theme_id"] if target else theme_id,
        "theme_name": target["theme_name"] if target else None, "file": target["file"] if target else tt.template_file(args.template_suffix),
        "layout": layout["theme"], "template_sha256": digest, "client_registry": args.client_registry,
        "approve_code": digest[:12], "pushable": bool(target), "ready": ready, "demo": bool(facts.get("demo")),
        "demo_pictures": len(final.report.get("demo_pictures", [])), "samples": len(final.report.get("samples", [])), "recipe": args.recipe,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "plan": plan_report.get("status"), "decided_by": plan_report.get("decided_by"), "copy": copy_report.get("status"),
        "review": review.get("verdict"), "backup_of_current_page": target["backup"] if target else None,
    }
    (out / "approval.json").write_text(json.dumps(approval, indent=1, ensure_ascii=False), encoding="utf-8")
    log.record(tier=0, mode="shadow", target=f"{approval['store']} theme {approval['theme_id']} {approval['file']}",
               action="design product page (not written to the store)", reason="client brief", result="recommended",
               evidence={"plan": approval["plan"], "copy": approval["copy"], "review": approval["review"], "template_sha256": digest})

    built = final.report["sections_built"]
    print(f"page: {brand2['brand_name']} | sections chosen by {plan_report.get('decided_by')}: "
          + ", ".join(s["kind"] for s in built))
    for s in built:
        if s.get("why"):
            print(f"  - {s['kind']}: {s['why']}")
    for note in plan_report.get("corrections") or []:
        print(f"  plan corrected: {note}")
    print(f"copy step: {copy_report.get('status')} | review: {review.get('verdict')} | lint errors {len(lint_errors)} | "
          f"build problems {len(final.report['problems'])} | empty picture slots {len(todo)}")
    print(f"files: {out.resolve()}")
    if target:
        print(f"to write this page to draft theme {target['theme_id']} ({target['theme_name']}) after a person has looked at it:\n"
              f"  python -m page_builder.push_page --out \"{out}\" --approve {approval['approve_code']} --approved-by NAME")
    else:
        print("design only (--no-theme-check): this page cannot be pushed; run again with the store and theme to get an approval code")
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
