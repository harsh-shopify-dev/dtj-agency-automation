"""Build a client's HOME page, or only the sections a person picks, from a brand profile and home facts. Nothing is written to any store here.

    cd services/store-builder
    python -m page_builder.run_home --brand brand.json --facts home-facts.json --out ../../.work/home-run --list
        the plan for this brand (home_plan.py): every home section as MUST, NEEDS FACTS, ADD or SKIP, each with its reason. Changes nothing.
    python -m page_builder.run_home --brand brand.json --facts home-facts.json --out ../../.work/home-run --sections auto
        design only: the planned sections (or names, e.g. --sections hero,best-sellers, or all) in <out>/template.json, the report in
        <out>/home-report.json.
    python -m page_builder.run_home ... --sections auto --store X.myshopify.com --theme 123
        read-only on the store: checks that the theme is a DRAFT Horizon theme, backs up its home page, and merges ONLY the chosen
        sections into the home page as it is now (every other section stays, hand edits included). <out>/approval.json then lets
        push_page (or ship_home, under Harsh's standing rule for drafts) write that file, and only while the home page is unchanged.

Harsh, 13 Oct 2026: "it should only design the homepage when told, like I should have options that what needs to be updated". So a home page
is never designed on its own, and a store run needs --sections: the person says what changes, either "auto" (the plan: must sections, add-ons
that add impact, nothing repetitive; "the AI will decide itself according to the brand") or the sections by name, which overrides the plan.
Exit code: 0 = built and clean, 2 = built but a lint error or a build problem needs a person's look, 1 = could not build.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from provision import templates
from provision.theme import ThemeError

from . import assemble_home, catalog, home_plan
from . import theme_target as tt
from .assemble import InputError
from .assemble_home import build_home

HOME = tt.HOME_TEMPLATE


LABEL = {"must": "MUST", "must_missing": "NEEDS FACTS", "add": "ADD", "skip": "SKIP"}


def print_plan(rows: list[dict], kind: str, niche: str, blocks: dict[str, str]) -> None:
    print(f"Home page plan ({kind.replace('_', '-')} store, {niche} niche):")
    for r in rows:
        block = f" [{blocks[r['builder']]}]" if r["decision"] in ("must", "add") and r["builder"] in blocks else ""
        print(f"  {LABEL[r['decision']]:11} {r['option']:13} {r['reason']}{block}")
    print("Build the plan with --sections auto, or pick sections yourself, e.g. --sections hero,best-sellers (or all).")


def main(argv: list[str] | None = None, *, access=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brand", required=True)
    ap.add_argument("--facts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--list", action="store_true", help="show the plan for this brand (must / needs facts / add / skip, with reasons) and stop")
    ap.add_argument("--sections", help="auto (the plan) or the sections by name, e.g. hero,best-sellers (or all); needed with --store")
    ap.add_argument("--fresh", action="store_true",
                    help="the home page becomes ONLY the chosen sections (plus the theme's own product row where the recipe puts it); the "
                         "current page is backed up first. Without it the chosen sections are added to or replaced in the page as it is")
    ap.add_argument("--store", help="the store's ORIGINAL .myshopify.com address (read-only check and merge)")
    ap.add_argument("--theme", help="the DRAFT theme's id")
    ap.add_argument("--client-registry", help="a client's own app copies (handles and extension ids); without it the page uses DTJ's original apps")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        brand = json.loads(Path(args.brand).read_text(encoding="utf-8"))
        facts = json.loads(Path(args.facts).read_text(encoding="utf-8"))
        full = build_home(brand, facts)  # everything the facts allow: what the plan chooses from
        rows = home_plan.plan(full.report, facts)
        if args.list:
            print_plan(rows, home_plan.store_type(facts), full.report["niche"], {s["kind"]: s["block"] for s in full.report["sections_built"]})
            return 0
        if bool(args.store) != bool(args.theme):
            raise InputError("--store and --theme go together")
        if args.store and not args.sections:
            raise InputError("say which sections to build or update with --sections auto (the plan) or their names (see --list): a home page "
                             "changes only where you say")
        planned = home_plan.chosen(rows)
        auto = not args.sections or args.sections.strip().lower() == "auto"
        chosen = planned if auto else assemble_home.pick(args.sections)
        # the page as it will really be, so bands and the wave fit it: fresh = only the chosen sections; an update = the plan's page plus them
        result = build_home(brand, facts, only=set(chosen) if args.fresh else set(planned) | set(chosen))
        rep = result.report
        rep.update(plan=rows, plan_used=auto, store_type=home_plan.store_type(facts), options=assemble_home.options(full))
        template = result.template
        if args.client_registry:
            template = catalog.to_client(template, catalog.load_client_registry(args.client_registry))
    except (InputError, ValueError, KeyError, OSError) as e:
        print(f"could not build the home page: {e}", file=sys.stderr)
        return 1

    built_ids = {s["kind"]: s["id"] for s in rep["sections_built"]}
    missing = {o["section"]: o["reason"] for o in rep["sections_omitted"]}
    page = rep["page_order"]
    chosen = sorted(dict.fromkeys(chosen), key=lambda b: page.index(built_ids[b]) if built_ids.get(b) in page else len(page))  # page order, once each
    chosen_ids = [built_ids[b] for b in chosen if b in built_ids]
    if args.fresh:  # a whole new page: the theme's own sections the recipe placed come along (they are not ours to pick)
        chosen_ids += [sid for sid in result.template["order"] if sid not in built_ids.values()]
    skipped = [{"option": assemble_home.option_of(b), "reason": missing.get(b, "not in this niche's recipe")} for b in chosen if b not in built_ids]
    rep.update(chosen=[assemble_home.option_of(b) for b in chosen if b in built_ids], chosen_not_built=skipped)
    out = Path(args.out)
    (out / "templates").mkdir(parents=True, exist_ok=True)
    for s in skipped:
        print(f"  not built {s['option']:13} {s['reason']}")
    if not chosen_ids:
        print("could not build the home page: none of the chosen sections has its facts (see --list)", file=sys.stderr)
        (out / "home-report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return 1

    base_sha, changes, check = None, [], None
    if args.store:
        try:
            if access is None:
                token = tt.read_token(args.store)
                if not token:
                    raise ThemeError(f"no Theme Access password saved as {tt.token_env_name(args.store)}")
                access = tt.ThemeAccess(args.store, token)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            check = tt.check_target(access, args.theme, out / f"backup-{stamp}", HOME)
            if check["base_theme"] != "Horizon":
                raise ThemeError(f"the home builder makes Horizon home pages only; theme {args.theme} is built on {check['base_theme']}")
            current = {"sections": {}, "order": []}
            if check["backup"] and not args.fresh:  # fresh: start from an empty page (the backup above keeps the old one)
                current = templates.load(Path(check["backup"]).read_text(encoding="utf-8"))[1]
            base_sha = check["current_product_template_sha256"]
            final, changes = assemble_home.merge(current, template, chosen_ids)
        except ThemeError as exc:
            print(f"could not check the theme: {exc}", file=sys.stderr)
            return 1
    else:  # design only: the chosen sections on their own, in page order, for a look
        final, changes = assemble_home.merge({"sections": {}, "order": []}, template, chosen_ids)

    body = tt.template_bytes(final)
    (out / "template.json").write_bytes(body)
    (out / "templates" / "index.json").write_bytes(body)
    digest = tt.sha256(body)
    errors = [f for f in rep["lint"] if f["severity"] == "error"]
    samples = [k for k in rep["samples"] if k.split(".")[0] in chosen_ids]
    ready = not errors and not rep["problems"]
    rep["changes"] = changes
    approval = {
        "client": brand.get("brand_name", ""), "store": tt.normalise_store(args.store) if args.store else "", "theme_id": str(args.theme or ""),
        "file": HOME, "template_sha256": digest, "approve_code": digest[:12], "pushable": bool(args.store), "base_sha256": base_sha,
        "sections": rep["chosen"], "changes": changes, "samples": len(samples), "demo": bool(facts.get("demo")), "ready": ready,
        "review": "pass" if ready else f"{len(errors)} lint errors, {len(rep['problems'])} build problems",
        "theme": {k: check[k] for k in ("theme_name", "role", "base_theme", "base_version")} if check else None,
    }
    (out / "home-report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "approval.json").write_text(json.dumps(approval, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"niche: {rep['niche']} | chosen: {', '.join(rep['chosen'])}")
    for c in changes:
        print(f"  {c['change']:8} {c['section']}" + (f" (after {c['after']})" if c.get("after") else ""))
    print(f"lint errors: {len(errors)} | build problems: {len(rep['problems'])} | samples in the chosen sections: {len(samples)}"
          + (f" | approve code {digest[:12]}" if args.store else " | design only"))
    return 0 if ready else 2


if __name__ == "__main__":
    sys.exit(main())
