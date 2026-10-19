"""Design a client's product page and, when every gate passes, write it into the client's DRAFT theme: one command for the store
factory's page step, and the answer n8n's "Store Factory: Page Design" run waits for.

    cd services/store-builder
    python -m page_builder.ship_draft --client ../../.work/clients/<client> --store X.myshopify.com --theme 123456789
        --template-suffix dtj-<product> [--client-registry page_builder/clients/<store>.json] [--design-only]

The client folder holds brand.json, facts.json, copy-answer.json (the session's copy) and optionally media/ and kept-edits.json;
the run goes to <client>/run. Without copy-answer.json the copy step runs dry and writes run/copy-request.json: answer it into
<client>/copy-answer.json (a --design-only run is the usual way to get it) and run again. Gates, in order; any failure stops before the store is touched and the answer says why:
  1 run_client (a run whose headless browser failed to start is retried, at most 3 runs in all; any other failure is not)
  2 the build's own gates: review loop pass, lint errors 0, build problems 0 (run_client exit 0)
  3 Harsh's design checks (.claude/skills/dtj-pdp-design-review/scripts/design_checks.py): every check passes
  4 push_page with the build's own approval code: draft theme only, fingerprint, backup, read-back, action-log row
Harsh's standing rule (10 Oct 2026): a page that passes every gate goes to the DRAFT theme without asking for an approval code. The
live theme stays out of reach: push_page has no live path. A page with SAMPLE values or test pictures is written only because this
is a draft preview; every sample is replaced or signed off before anything goes live.

Writes <client>/run/ship-result.json, the body for n8n/store-factory/reply.py.
Exit code: 0 = written to the draft (or designed, with --design-only), 2 = needs a person's look, 1 = could not build.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import push_page, run_client

REPO = Path(__file__).resolve().parents[3]
DESIGN_CHECKS = REPO / ".claude" / "skills" / "dtj-pdp-design-review" / "scripts" / "design_checks.py"
STANDING = "Harsh (standing: draft pushes without asking)"
BROWSER_FAILED = "review loop could not run"  # run_client's words when the headless browser did not start (the one flaky step)
RUNS = 3


def run_design_checks(out: Path) -> dict:
    """Harsh's design checks on the built template.json, from the review skill's own script (the one source of truth)."""
    p = subprocess.run([sys.executable, str(DESIGN_CHECKS), str(out)], capture_output=True, text=True, encoding="utf-8", timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f"design_checks.py failed: {(p.stderr or p.stdout).strip()[-400:]}")
    return json.loads(p.stdout)["page"]


def _quiet(fn, argv: list[str]) -> tuple[int, str]:
    with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
        try:
            code = fn(argv)
        except SystemExit as exc:  # argparse and the input checks stop with SystemExit
            code = exc.code if isinstance(exc.code, int) else 1
            print(exc.code if not isinstance(exc.code, int) else "", file=sys.stderr)
    return code, out.getvalue() + err.getvalue()


PEOPLE_APPROVAL = "Harsh (standing 19 Oct 2026: DTJ's sample people photos on every store we build)"


def upload_people(store: str, files: list[str], log_dir: Path) -> tuple[bool, str]:
    """DTJ's sample people photos that the page uses, into the store's Files (store_files: skips what the store already has; Harsh,
    19 Oct 2026: "make this images as default any store we build"). (True, "") when every one is there."""
    from . import store_files  # noqa: PLC0415  (only when a page uses them)
    from .assemble import PEOPLE_DIR  # noqa: PLC0415
    try:
        plan = store_files.upload(store_files.Store(store), PEOPLE_DIR, PEOPLE_APPROVAL, only=files, limit=len(files),
                                  out=lambda *_: None, log_dir=log_dir)
    except (store_files.StoreError, OSError) as exc:
        return False, str(exc)[:300]
    bad = [p for p in plan if p["status"] not in ("uploaded", "already there")]
    return not bad, "; ".join(f"{p['file']}: {p['status']}" for p in bad)


def preview_url(store: str, handle: str | None, theme_id: str, suffix: str | None) -> str:
    if not handle:
        return f"https://{store}/?preview_theme_id={theme_id}"
    return f"https://{store}/products/{handle}?preview_theme_id={theme_id}" + (f"&view={suffix}" if suffix else "")


def main(argv: list[str] | None = None, *, design=run_client.main, push=push_page.main, checks=run_design_checks,
         sleep=time.sleep, people=upload_people) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--client", required=True, help="the client folder (brand.json, facts.json, copy-answer.json, media/)")
    ap.add_argument("--store", help="the store's ORIGINAL .myshopify.com address")
    ap.add_argument("--theme", help="the DRAFT theme's id")
    ap.add_argument("--template-suffix", help="write templates/product.<suffix>.json (one per product)")
    ap.add_argument("--client-registry", help="the client's app copies (page_builder/clients/<store>.json)")
    ap.add_argument("--approved-by", default=STANDING, help="recorded in the action log (default: Harsh's standing rule for drafts)")
    ap.add_argument("--design-only", action="store_true", help="design and check, never touch the store")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    client = Path(args.client)
    out = client / "run"
    out.mkdir(parents=True, exist_ok=True)
    facts = json.loads((client / "facts.json").read_text(encoding="utf-8"))
    build = ["--brand", str(client / "brand.json"), "--facts", str(client / "facts.json"), "--out", str(out), "--plan", "off"]
    copy_answer = client / "copy-answer.json"
    # no copy answer yet: a dry copy step writes run/copy-request.json for the session to answer (nothing is called, template words stay)
    build += ["--copy", "answer", "--copy-answer", str(copy_answer)] if copy_answer.is_file() else ["--copy", "dry"]
    for flag, path in (("--media", client / "media"), ("--keep-edits", client / "kept-edits.json")):
        if path.exists():
            build += [flag, str(path)]
    for flag, value in (("--client-registry", args.client_registry), ("--template-suffix", args.template_suffix)):
        if value:
            build += [flag, value]
    if args.design_only:
        build.append("--no-theme-check")
    elif not (args.store and args.theme):
        ap.error("--store and --theme are needed to write the draft (or use --design-only)")
    else:
        build += ["--store", args.store, "--theme", args.theme]

    result: dict = {"page_status": "", "approve_code": "", "preview_url": "", "design_checks": "", "failed_checks": [], "lint_errors": 0,
                    "build_problems": 0, "samples": 0, "dtj_copy": 0, "demo_pictures": 0, "kept_edits": 0, "file": "",
                    "theme_id": args.theme or "", "run_folder": str(out.resolve()), "summary": "", "note": "",
                    "finished_at": ""}

    def finish(status: str, code: int, note: str = "") -> int:
        result.update(page_status=status, note=note, finished_at=datetime.now(timezone.utc).isoformat())
        (out / "ship-result.json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{status}: {result['summary'] or note}")
        if result["preview_url"]:
            print(f"preview: {result['preview_url']}")
        if note and result["summary"]:
            print(note)
        print(f"answer for n8n: {out / 'ship-result.json'}")
        return code

    # ---- 1 + 2. build (a stale approval.json from an earlier run must never be pushed: it is removed first)
    (out / "approval.json").unlink(missing_ok=True)
    code, log = 1, ""
    for run in range(1, RUNS + 1):
        code, log = _quiet(design, build)
        (out / f"ship-build-{run}.log").write_text(log, encoding="utf-8")
        if not (code == 1 and BROWSER_FAILED in log) or run == RUNS:
            break
        sleep(5)
    if code == 1 or not (out / "approval.json").is_file():
        return finish("could not build", 1, log.strip()[-600:] or "run_client stopped without a message")
    approval = json.loads((out / "approval.json").read_text(encoding="utf-8"))
    report = json.loads((out / "build-report.json").read_text(encoding="utf-8"))
    lint = [f for f in report.get("lint", []) if f.get("severity") == "error"]
    result.update(approve_code=approval["approve_code"], lint_errors=len(lint), build_problems=len(report.get("problems", [])),
                  samples=approval.get("samples", 0), dtj_copy=approval.get("dtj_copy", 0), demo_pictures=approval.get("demo_pictures", 0),
                  kept_edits=len(approval.get("kept_edits") or []), file=approval.get("file", ""))
    result["summary"] = (f"{len(report.get('sections_built', []))} sections, review {approval.get('review')}, lint errors {len(lint)}, "
                         f"{result['samples']} samples, {result['dtj_copy']} DTJ copy lines, {result['demo_pictures']} test pictures")
    if code != 0:
        why = [f"review: {approval.get('review')}"] + [f"lint {f.get('rule')}: {f.get('message')}" for f in lint] + \
              [f"build problem: {p}" for p in report.get("problems", [])]
        return finish("needs a look", 2, "; ".join(why))

    # ---- 3. Harsh's design checks
    try:
        page = checks(out)
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return finish("needs a look", 2, f"design checks could not run: {exc}")
    failed = {k: v.get("findings", []) for k, v in page["checks"].items() if not v.get("pass")}
    result.update(design_checks=f"{page['passed']}/{page['of']}", failed_checks=[f"{k}: {'; '.join(v)}" for k, v in failed.items()])
    if failed:
        return finish("needs a look", 2, "design checks failed: " + " | ".join(result["failed_checks"]))
    if args.design_only:
        return finish("designed (not written)", 0, "design only: run again with --store and --theme to write the draft")

    # ---- 4. the sample people photos the page uses must be in the store's Files first (a draft never points at a missing picture)
    used = report.get("people_photos") or []
    if used:
        ok, why = people(approval["store"], used, out)
        if not ok:
            return finish("needs a look", 2, f"not written: DTJ's sample people photos could not be put in the store's Files ({why}); "
                                             "check the Shopify CLI's sign-in to this store (shopify store auth)")
        result["note"] = f"{len(used)} sample people photos in the store's Files"

    # ---- 5. write the draft (push_page checks everything again and refuses the live theme)
    flags = ["--out", str(out), "--approve", approval["approve_code"], "--approved-by", args.approved_by]
    flags += ["--allow-samples"] if result["samples"] else []
    flags += ["--allow-demo"] if approval.get("demo") else []
    rc, pushed = _quiet(push, flags)
    (out / "ship-push.log").write_text(pushed, encoding="utf-8")
    if rc != 0:
        return finish("needs a look", 2, f"not written: {pushed.strip()[-600:]}")
    suffix = args.template_suffix
    result["preview_url"] = preview_url(approval["store"], facts.get("product", {}).get("handle"), str(approval["theme_id"]), suffix)
    return finish("written to draft", 0, "check the real page next (factory P9): every section, 390 px, no sideways scroll")


if __name__ == "__main__":
    raise SystemExit(main())
