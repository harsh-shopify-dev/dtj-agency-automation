"""Applies an APPROVED fixes batch to the live site, then checks the live pages until every fix shows (up to 3 rounds).

Tier 2: it runs only with --approved-by "<name>" (Harsh, or a DTJ teammate by name when he can't be reached; one yes = one batch),
the kill switch on and dry run off. Each change is guarded: if the live page no longer shows the "before" the batch was made from
(someone edited it since), that change is skipped. Every write is logged with its old value, and --undo puts the old values back
(also with a named approver).

    python -m seo_engine.apply_batch --batch .work/seo/2026-10-20/fixes.json --approved-by "Harsh"
    python -m seo_engine.apply_batch --batch ... --approved-by "Harsh" --only c001,c004
    python -m seo_engine.apply_batch --undo .work/seo/2026-10-20/applied-fix-2026-10-20.json --approved-by "Harsh"
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import site_scan, wordpress
from .actionlog import ActionLog
from .config import load

FIELD = {"meta_description": "metadesc", "seo_title": "title", "noindex": "noindex"}
VERIFY_ROUNDS = 3


def _norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def _live(url: str, fetch) -> site_scan.Page | None:
    bust = ("&" if "?" in url else "?") + f"dtj_check={int(time.time())}"  # ask past page caches for the current version
    r = fetch(url + bust)
    return site_scan.parse_page(url, r.text, r.status) if r.status == 200 else None


def _shows(change: dict, page: site_scan.Page | None, cfg, opener) -> bool:
    k = change["kind"]
    if k == "alt_text":
        return _norm(wordpress.get_alt(cfg, change["media_id"], opener)) == _norm(change["after"])
    if page is None:
        return False
    if k == "meta_description":
        return _norm(page.description) == _norm(change["after"])
    if k == "seo_title":
        return _norm(page.title) == _norm(change["after"])
    if k == "noindex":
        return "noindex" in page.robots.lower()
    if k == "site_jsonld":
        return "ProfessionalService" in page.schema_types or "Organization" in page.schema_types
    return False


def _guard(change: dict, page: site_scan.Page | None) -> str | None:
    """Why this change must be skipped (the page changed since the batch was made), or None."""
    k = change["kind"]
    if k in ("meta_description", "seo_title", "noindex") and page is None:
        return "the page did not load"
    if k == "meta_description" and _norm(page.description) != _norm(change["before"]):
        return "the description changed since the batch was made"
    if k == "seo_title" and _norm(page.title) != _norm(change["before"]):
        return "the title changed since the batch was made"
    return None


def apply(batch: dict, *, approved_by: str, out_dir: Path, only: set[str] | None = None, fetch=site_scan.http_fetch,
          opener=None, env=None, wait: float = 20, rounds: int = VERIFY_ROUNDS) -> dict:
    cfg = load(env)
    decision = cfg.decide(2, approved_by)
    if not decision.allowed:
        raise SystemExit(f"Not applied: {decision.reason}")
    kw = {"opener": opener} if opener else {}
    log = ActionLog(out_dir.parent / "actions.jsonl")
    approved_at = datetime.now(timezone.utc).isoformat()
    results = []
    for c in batch["changes"]:
        if c["how"] != "auto" or (only and c["cid"] not in only):
            continue
        res = {"cid": c["cid"], "kind": c["kind"], "url": c["url"], "after": c["after"], "status": "failed"}
        try:
            page = _live(c["url"], fetch) if c["kind"] != "alt_text" else None
            skip = _guard(c, page)
            if c["kind"] == "alt_text" and _norm(wordpress.get_alt(cfg, c["media_id"], **kw)):
                skip = "the image already has alt text"
            if skip:
                res["status"], res["why"] = "skipped", skip
            elif c["kind"] in FIELD:
                snap = wordpress.resolve(cfg, c["url"], **kw)
                res.update(post_id=snap["post_id"], field=FIELD[c["kind"]], undo_value=snap.get(FIELD[c["kind"]], ""))
                wordpress.set_field(cfg, snap["post_id"], FIELD[c["kind"]], "1" if c["kind"] == "noindex" else c["after"], **kw)
                res["status"] = "written"
            elif c["kind"] == "alt_text":
                res.update(media_id=c["media_id"], undo_value="")
                wordpress.set_alt(cfg, c["media_id"], c["after"], **kw)
                res["status"] = "written"
            elif c["kind"] == "site_jsonld":
                res["undo_value"] = wordpress.get_jsonld(cfg, **kw)
                wordpress.set_jsonld(cfg, c["after"], **kw)
                res["status"] = "written"
        except Exception as exc:  # noqa: BLE001 - one failed change must not stop the batch; it is logged and reported
            res["why"] = str(exc)[:300]
        results.append(res)
        log.record(tier=2, mode=cfg.mode, target=c["url"], action=f"fix {c['kind']}", reason=c["reason"],
                   result={"written": "success", "skipped": "blocked"}.get(res["status"], "failed"),
                   before=res.get("undo_value", c.get("before")), after=c["after"], approved_by=approved_by,
                   approved_at=approved_at, error=res.get("why"))

    pending = [r for r in results if r["status"] == "written"]
    changes = {c["cid"]: c for c in batch["changes"]}
    for n in range(rounds):  # the site's own caches can delay what visitors see
        if not pending:
            break
        if n and wait:
            time.sleep(wait)
        still = []
        for r in pending:
            c = changes[r["cid"]]
            try:
                ok = _shows(c, _live(c["url"], fetch) if c["kind"] != "alt_text" else None, cfg, opener)
            except Exception:  # noqa: BLE001
                ok = False
            if ok:
                r["status"], r["verified_round"] = "verified", n + 1
            else:
                still.append(r)
        pending = still
    for r in pending:
        r["status"] = "not visible yet"
        r["why"] = f"written, but the live page did not show it after {rounds} checks (a page cache, or Yoast ignores the field)"

    record = {"batch_id": batch["id"], "site": batch["site"], "approved_by": approved_by, "approved_at": approved_at, "results": results,
              "counts": {s: sum(1 for r in results if r["status"] == s) for s in ("verified", "not visible yet", "skipped", "failed")}}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"applied-{batch['id']}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    return record


def undo(record: dict, *, approved_by: str, out_dir: Path, opener=None, env=None) -> dict:
    cfg = load(env)
    decision = cfg.decide(2, approved_by)
    if not decision.allowed:
        raise SystemExit(f"Not undone: {decision.reason}")
    kw = {"opener": opener} if opener else {}
    log = ActionLog(out_dir.parent / "actions.jsonl")
    done = []
    for r in record["results"]:
        if r["status"] not in ("verified", "not visible yet"):
            continue
        try:
            if "field" in r:
                wordpress.set_field(cfg, r["post_id"], r["field"], r.get("undo_value") or "", **kw)
            elif r["kind"] == "alt_text":
                wordpress.set_alt(cfg, r["media_id"], r.get("undo_value") or "", **kw)
            elif r["kind"] == "site_jsonld":
                wordpress.set_jsonld(cfg, r.get("undo_value"), **kw)
            status, err = "undone", None
        except Exception as exc:  # noqa: BLE001
            status, err = "failed", str(exc)[:300]
        done.append({"cid": r["cid"], "status": status, "error": err})
        log.record(tier=2, mode=cfg.mode, target=r["url"], action=f"undo {r['kind']}", reason=f"undo batch {record['batch_id']}",
                   result="success" if status == "undone" else "failed", before=r["after"], after=r.get("undo_value"),
                   approved_by=approved_by, approved_at=datetime.now(timezone.utc).isoformat(), error=err)
    return {"batch_id": record["batch_id"], "undone": done}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch", type=Path)
    ap.add_argument("--undo", type=Path)
    ap.add_argument("--approved-by", required=True, help="the person who said yes, by name")
    ap.add_argument("--only", default="", help="comma-separated change ids (c001,...); default: every auto change")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if a.undo:
        res = undo(json.loads(a.undo.read_text(encoding="utf-8")), approved_by=a.approved_by, out_dir=a.undo.parent)
    elif a.batch:
        res = apply(json.loads(a.batch.read_text(encoding="utf-8")), approved_by=a.approved_by, out_dir=a.batch.parent,
                    only={x.strip() for x in a.only.split(",") if x.strip()} or None)
    else:
        ap.error("give --batch or --undo")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
