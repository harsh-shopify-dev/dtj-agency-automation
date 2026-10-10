"""Write an APPROVED product page into the client's DRAFT theme (Tier 2: a person approves this exact page, every time).

    cd services/store-builder
    python -m page_builder.push_page --out ../../.work/clients/<brand> --approve <code> --approved-by Harsh

The approval code is the start of the page file's fingerprint, printed by run_client. If the page changed after it was approved, the code
no longer matches and nothing is written. Right before writing it checks again that the theme is a draft (never the live theme), takes a
fresh backup of the theme's current product page, writes ONLY templates/product.json (no other file, nothing deleted, nothing
published), reads the file back to prove it landed, and writes an action-log row with who approved it.
Undo: push the backup file the same way (backup-<time>/templates/product.json).
Exit code: 0 = written and verified, 1 = refused or failed (the theme is unchanged unless it says otherwise).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from provision.actionlog import ActionLog
from provision.theme import ThemeError

from . import theme_target as tt


def main(argv: list[str] | None = None, *, access=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="the run_client output folder")
    ap.add_argument("--approve", required=True, help="the approval code printed by run_client")
    ap.add_argument("--approved-by", required=True, help="who looked at the page and said yes")
    ap.add_argument("--allow-demo", action="store_true",
                    help="write a page that uses TEST pictures (facts say demo: true): only for a development store, never a client")
    ap.add_argument("--accept-review-findings", action="store_true",
                    help="write even though the review loop asked for a person's look (the approver has looked)")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    out = Path(args.out)
    approval = json.loads((out / "approval.json").read_text(encoding="utf-8"))
    log = ActionLog(out / "action-log.jsonl", approval.get("client") or approval.get("store") or "unknown")
    file = approval.get("file") or tt.PRODUCT_TEMPLATE  # templates/product.json or a new templates/product.<suffix>.json
    target = f"{approval['store']} theme {approval['theme_id']} {file}"
    now = datetime.now(timezone.utc)

    def refuse(reason: str) -> int:
        log.record(tier=2, mode="approve", target=target, action="write product page to draft theme", reason="approved page",
                   result="blocked", error=reason, approved_by=args.approved_by, approved_at=now.isoformat())
        print(f"not written: {reason}", file=sys.stderr)
        return 1

    body = (out / "template.json").read_bytes()
    digest = tt.sha256(body)
    if not approval.get("pushable"):
        return refuse("this run was design-only (no theme check); run run_client with the store and theme first")
    if digest != approval["template_sha256"]:
        return refuse("template.json changed after the approval file was written; run run_client again")
    if args.approve.strip().lower() != digest[:12]:
        return refuse("the approval code does not match this page (it was approved for a different version)")
    if approval.get("demo") and not args.allow_demo:
        return refuse("this page uses TEST pictures (demo: true); they may only go to a development store: add --allow-demo if this is one")
    if not approval.get("ready") and not args.accept_review_findings:
        return refuse(f"the review said {approval.get('review')!r}: look at the screenshots and add --accept-review-findings if it is fine")

    try:
        if access is None:
            token = tt.read_token(approval["store"])
            if not token:
                return refuse(f"no Theme Access password saved as {tt.token_env_name(approval['store'])}")
            access = tt.ThemeAccess(approval["store"], token)
        stamp = now.strftime("%Y%m%d-%H%M%S")
        check = tt.check_target(access, approval["theme_id"], out / f"backup-{stamp}", file)  # again, right before writing
        staging = tt.stage(out / "template.json", out / "_push", file)
        theme = access.push_product_template(approval["theme_id"], staging, file)
        after = access.pull(approval["theme_id"], [file], out / f"after-{stamp}")
        landed = (after / file).exists() and tt.same_template(body, (after / file).read_text(encoding="utf-8"))
    except ThemeError as exc:
        log.record(tier=2, mode="approve", target=target, action="write product page to draft theme", reason="approved page",
                   result="failed", error=str(exc), approved_by=args.approved_by, approved_at=now.isoformat(),
                   evidence={"commands": access.commands if access else []})
        print(f"failed: {exc}", file=sys.stderr)
        return 1

    log.record(tier=2, mode="approve", target=target, action="write product page to draft theme", reason="approved page",
               result="success" if landed else "failed", error=None if landed else "the file read back does not match what was sent",
               approved_by=args.approved_by, approved_at=now.isoformat(), evidence={"commands": access.commands},
               before={"sha256": check["current_product_template_sha256"], "backup": check["backup"]},
               after={"sha256": digest, "theme_role": theme.get("role")})
    if not landed:
        print("written, but the file read back from Shopify does not match: check the theme editor before going on", file=sys.stderr)
        return 1
    print(f"written and verified: {file} in draft theme {approval['theme_id']} ({theme.get('name')}, {theme.get('role')})")
    print(f"backup of the previous page: {check['backup']}")
    if theme.get("editor_url"):
        print(f"open in the theme editor: {theme['editor_url']}")
    if theme.get("preview_url"):
        print(f"preview: {theme['preview_url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
