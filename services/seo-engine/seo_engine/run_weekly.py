"""The Monday SEO/AEO run. Safe by default.

    python -m seo_engine.run_weekly                  # free: website check + plans (no AI, no data purchase, no WordPress)
    python -m seo_engine.run_weekly --live           # + AI steps (ANTHROPIC_API_KEY) and data (DATAFORSEO_LOGIN/PASSWORD)

Order:
 1. Website check (free).
 2. Fixes batch: exact before -> after changes for the site, waiting for one yes (apply_batch.py). Nothing is changed here.
 3. Keyword plan: refreshed from DataForSEO when it is missing or 28+ days old (first Monday of the month in practice).
 4. AI-answer check: Claude, ChatGPT, Perplexity and Gemini, by city, state and India.
 5. Page of the week, alternating: a blog article (the "tide": next informational keyword group) and a city service page (the
    "boat": next service x city that has real local proof; without proof, the week falls back to an article). Before writing,
    the top 3 Google results for its main keyword are read. Then the code gate.
 6. WordPress DRAFT only when config.decide(1) allows (kill switch on, SEO_DRY_RUN off, SEO_MODE=approve); otherwise a file.
 7. The report.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import aeo_probe, city_page, dataforseo, fixer, gates, keywords, report, serp_skeleton, site_scan, wordpress, writer
from .actionlog import ActionLog
from .config import load

REPO = Path(__file__).resolve().parents[3]
DEFAULT_OUT = REPO / ".work" / "seo"
PLAN_MAX_AGE_DAYS = 28


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) if not isinstance(data, str) else data, encoding="utf-8")


def _load(path: Path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def article_topics(plan: dict | None, seeds: dict) -> list[dict]:
    """Blog topics in order: the keyword plan's informational groups when there is a plan, else the founder questions in topics.json."""
    if plan and any(c["type"] == "tide" for c in plan["clusters"]):
        out = []
        for c in plan["clusters"]:
            if c["type"] != "tide":
                continue
            svc = seeds["services"].get(c.get("service") or "", {})
            out.append({"id": c["id"], "slug": c["slug"], "question": c["main"], "main_keyword": c["main"], "keywords": c["keywords"],
                        "place": c.get("place"), "link_to": svc.get("page"), "from": "keyword plan"})
        return out
    return [{**t, "from": "topics.json"} for t in gates.load_json("topics.json")["topics"]]


def next_unwritten(topics: list[dict], state: dict, taken=None) -> dict | None:
    """The first topic not drafted yet. taken(slug) asks WordPress (when drafts go there), so a lost state file never repeats one."""
    done = set(state.get("written", []))
    for t in topics:
        if t["id"] in done:
            continue
        if taken and taken(t["slug"]):
            state.setdefault("written", []).append(t["id"])
            continue
        return t
    return None


def previous_pages(out_root: Path, state: dict) -> int | None:
    """Pages read by the last complete check: state.json, else the most of the last 4 saved scans that read every sitemap."""
    if state.get("last_complete_pages"):
        return state["last_complete_pages"]
    seen = []
    for f in sorted(out_root.glob("????-??-??/scan.json"), reverse=True)[:4]:
        try:
            s = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if not s.get("coverage", {}).get("unreadable_sitemaps"):
            seen.append(s.get("pages_in_sitemap") or 0)
    return max(seen, default=0) or None


def run(*, live: bool, out_root: Path, max_pages: int = site_scan.MAX_PAGES, probe_limit: int = 10, fetch=site_scan.http_fetch,
        client=None, dfs=None, wp_opener=None, env=None, refresh_keywords: bool = False) -> dict:
    cfg = load(env)
    environ = os.environ if env is None else env
    now = datetime.now(timezone.utc)
    out = out_root / now.strftime("%Y-%m-%d")
    log = ActionLog(out_root / "actions.jsonl")
    state_path, plan_path, built_dir = out_root / "state.json", out_root / "keyword_plan.json", out_root / "city-pages"
    state = _load(state_path, {"written": []})
    seeds, proof = gates.load_json("seeds.json"), gates.load_json("local_proof.json")
    mode, notes = cfg.mode, []

    if live and client is None:
        if environ.get("ANTHROPIC_API_KEY"):
            client = writer.make_client()
        else:
            notes.append("ANTHROPIC_API_KEY is not set: the AI steps were planned, not run.")
    if live and dfs is None:
        if dataforseo.available(environ):
            dfs = dataforseo.Client(env=environ)
        else:
            notes.append("DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD are not set: no keyword data, Google results or ChatGPT/Perplexity/Gemini check.")
    if not live:
        client = dfs = None

    # 1. Website check (Tier 0, free)
    prev = previous_pages(out_root, state)
    scan = site_scan.scan(cfg.site, fetch, max_pages=max_pages, previous_pages=prev and min(prev, max_pages))
    _save(out / "scan.json", scan)
    cov = scan["coverage"]
    log.record(tier=0, mode=mode, target=cfg.site, action="site scan", reason="weekly SEO/AEO check", result="success",
               evidence={"source": scan["source"], "pages": scan["pages_in_sitemap"], "counts": scan["counts"], "complete": cov["complete"],
                         "unreadable_sitemaps": [p["url"] for p in cov["unreadable_sitemaps"]], "previous_pages": cov["previous_pages"]})
    # the yardstick for next week: never a check that lost a sitemap, nor one cut short by a smaller --max-pages
    if not cov["unreadable_sitemaps"] and max_pages >= site_scan.MAX_PAGES:
        state["last_complete_pages"] = scan["pages_in_sitemap"]
        _save(state_path, state)

    # 2. Fixes batch (prepared only; Tier 2 to apply, with a named approver)
    batch = fixer.propose(scan, client=client, proof=proof, now=now)
    _save(out / "fixes.json", batch)
    notes += batch["notes"]
    log.record(tier=2, mode=mode, target=cfg.site, action="prepare fixes batch", reason="waiting for one yes (apply_batch.py)",
               result="recommended", evidence={"batch": batch["id"], "counts": batch["counts"]})

    # 3. Keyword plan (monthly; Tier 0, paid data inside the cap)
    plan = _load(plan_path)
    age = keywords.plan_age_days(plan, now)
    if dfs is not None and (plan is None or refresh_keywords or (age is not None and age >= PLAN_MAX_AGE_DAYS)):
        try:
            plan = keywords.build_plan(dfs, seeds, now=now)
            _save(plan_path, plan)
            _save(out / "keyword_plan.json", plan)
            log.record(tier=0, mode=mode, target="keywords", action="keyword research", reason="monthly refresh", result="success",
                       evidence={"source": plan["source"], "kept": plan["kept"], "clusters": len(plan["clusters"]), "cost_usd": plan["cost_usd"]})
        except Exception as exc:  # noqa: BLE001 - keep last month's plan
            notes.append(f"Keyword research failed, last plan kept: {str(exc)[:200]}")

    # 4. AI-answer check
    questions = gates.load_json("topics.json")["probe_questions"]["items"]
    probe = aeo_probe.probe(questions, client, limit=probe_limit, dfs=dfs)
    _save(out / "aeo.json", probe)
    log.record(tier=0, mode=mode, target="AI answers", action="AEO check", reason="is DTJ named for founder questions",
               result="success" if probe["mode"] == "live" else "dry_run", evidence=probe.get("summary") or {"planned": len(probe["planned"])})

    # 5. Page of the week: alternate article (tide) and city page (boat)
    draft_allowed = cfg.decide(1).allowed
    rows = city_page.matrix(seeds, proof, plan, set(state.get("written", [])))
    _save(out / "city_matrix.json", rows)
    want = "city" if state.get("last_kind") == "article" else "article"
    kind, topic, local = "article", None, None

    def taken_for(wp_kind):
        if not draft_allowed:
            return None
        return lambda slug: wordpress.slug_taken(cfg, slug, **({"opener": wp_opener} if wp_opener else {}), kind=wp_kind)

    try:
        if want == "city":
            row = city_page.next_city_page(rows)
            if row and not (taken_for("pages") and taken_for("pages")(row["slug"])):
                kind, topic = "city", city_page.topic_for(row, seeds)
                local = city_page.local_for_model(row["city"], proof, row["service"])
            else:
                notes.append("No city page this week: no service x city has enough real proof yet (local_proof.json). An article instead.")
        if topic is None:
            topic = next_unwritten(article_topics(plan, seeds), state, taken_for("posts"))
    except wordpress.WordPressError as exc:
        topic = None
        notes.append(f"Could not check WordPress for earlier drafts, so no page this week: {exc}")

    skeleton, draft = None, None
    if topic is None:
        if not any(n.startswith("Could not check WordPress") for n in notes):
            notes.append("Every topic has a draft: the next keyword refresh adds more.")
    else:
        if dfs is not None:
            try:
                skeleton = serp_skeleton.build(dfs, topic.get("main_keyword") or topic["question"], topic.get("place"), fetch)
                _save(out / "top3.json", serp_skeleton.for_model(skeleton))
                if skeleton.get("note"):
                    notes.append(skeleton["note"])
            except Exception as exc:  # noqa: BLE001 - write without the outline rather than not at all
                notes.append(f"Top 3 Google results not read: {str(exc)[:200]}")
        draft = writer.write_article(topic, scan["pages"], client=client, skeleton=skeleton, local=local, kind=kind)
        if draft.status == "passed" and kind == "city":
            similar, score, other = city_page.too_similar(gates.article_text(draft.article), built_dir)
            if similar:
                draft.status = "blocked"
                draft.gate["blocks"].append(f"reads {score:.0%} like the {other} page: make it about this city")
        _save(out / "draft.json", draft.as_report())
        target = f"wordpress {'page' if kind == 'city' else 'post'} draft: {topic['id']}"
        if draft.status != "passed":
            log.record(tier=0, mode=mode, target=target, action=f"draft {kind}", reason=topic["question"],
                       result="dry_run" if draft.status == "not-run" else "blocked", error=draft.error,
                       evidence={"status": draft.status, "blocks": draft.gate.get("blocks", [])})
        else:
            body = writer.to_html(draft.article)
            _save(out / "draft.html", body)
            decision = cfg.decide(1)
            if not decision.allowed:
                log.record(tier=1, mode=mode, target=target, action="save as WordPress draft", reason=decision.reason,
                           result="recommended", after={"title": draft.article["title"], "slug": draft.article["slug"]})
                notes.append(f"Page ready for review (not in WordPress: {decision.reason}).")
            else:
                try:
                    saved = wordpress.create_draft(cfg, title=draft.article["title"], slug=draft.article["slug"], html=body,
                                                   excerpt=draft.article["meta_description"], kind="pages" if kind == "city" else "posts",
                                                   **({"opener": wp_opener} if wp_opener else {}))
                    log.record(tier=1, mode=mode, target=target, action="save as WordPress draft", reason=topic["question"],
                               result="success", after=saved)
                    notes.append(f"Draft saved in WordPress for review: {saved['edit_url']}")
                except Exception as exc:  # noqa: BLE001 - logged and reported, never retried blindly
                    log.record(tier=1, mode=mode, target=target, action="save as WordPress draft", reason=topic["question"],
                               result="failed", error=str(exc)[:300])
                    notes.append(f"WordPress draft failed: {str(exc)[:200]}")
            state.setdefault("written", []).append(topic["id"])
            state["last_kind"] = kind
            if kind == "city":
                built_dir.mkdir(parents=True, exist_ok=True)
                (built_dir / f"{topic['id']}.txt").write_text(gates.article_text(draft.article), encoding="utf-8")
            _save(state_path, state)

    cost = round(dfs.spent, 4) if dfs is not None else None
    md = report.render(cfg=cfg, scan=scan, batch=batch, plan=plan, probe=probe, rows=rows, topic=topic, kind=kind, draft=draft,
                       skeleton=skeleton, notes=notes, dfs_cost=cost)
    _save(out / "report.md", md)
    return {"out": str(out), "report": md, "notes": notes}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", action="store_true", help="run the AI and data steps (needs the keys)")
    ap.add_argument("--refresh-keywords", action="store_true", help="redo the keyword plan now (paid, inside DFS_MAX_USD)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-pages", type=int, default=site_scan.MAX_PAGES)
    ap.add_argument("--probe-limit", type=int, default=10)
    a = ap.parse_args(argv)
    res = run(live=a.live, out_root=a.out, max_pages=a.max_pages, probe_limit=a.probe_limit, refresh_keywords=a.refresh_keywords)
    sys.stdout.reconfigure(encoding="utf-8")
    print(res["report"])
    print(f"\nFiles: {res['out']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
