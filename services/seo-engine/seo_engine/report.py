"""The Monday report in plain words: what is wrong on the site, the fixes waiting for a yes, whether AI assistants name DTJ, the
keyword plan, the city pages, this week's page, and what a person needs to do. Every number names where it came from."""
from __future__ import annotations

LEVEL = {"high": "Fix now", "medium": "Fix soon", "low": "When there is time"}
KIND = {"meta_description": "Google description", "seo_title": "Google title", "noindex": "Hide from Google", "alt_text": "Image alt text",
        "site_jsonld": "Business details for Google and AI", "manual": "For a person"}


def _cell(s, n: int = 140) -> str:
    return str(s if s is not None else "").replace("|", "/").replace("\n", " ")[:n]


def coverage_warning(cov: dict) -> list[str]:
    """Lines that say the website check missed part of the site, so nobody approves a batch thinking it covers every page."""
    if cov.get("complete", True):
        return []
    L = ["> **This check is incomplete.**"]
    bad = cov.get("unreadable_sitemaps") or []
    if bad:
        L.append(f"> {len(bad)} sitemap(s) (the site's list of pages for Google) could not be read, so the pages in them were not checked "
                 "and their fixes may be missing from the batch below:")
        L += [f"> - {_cell(p['url'], 120)}: {p['why']} after {p['tries']} tries" for p in bad]
    if cov.get("fewer_than_before"):
        L.append(f"> Only {cov['pages_read']} pages were read; the last complete check read {cov['previous_pages']}. "
                 "Pages may have been missed.")
    L += ["> Run the check again before saying yes to the fixes.", ""]
    return L


def render(*, cfg, scan: dict, batch: dict, plan: dict | None, probe: dict, rows: list[dict], topic: dict | None, kind: str, draft,
           skeleton: dict | None, notes: list[str], dfs_cost: float | None, top: int = 12) -> str:
    c = scan["counts"]
    L = [f"# DTJ search report, {scan['scanned_at'][:10]}", "",
         f"Mode: **{cfg.mode}**{' (dry run)' if cfg.dry_run else ''}. Site: {cfg.site}. Pages checked: {scan['pages_in_sitemap']}."
         + (f" Data bought this run: ${dfs_cost:.2f} (DataForSEO's own cost figures)." if dfs_cost else ""), ""]
    L += coverage_warning(scan.get("coverage") or {})

    # 1. Site
    L += ["## 1. Website check", "", f"{c['high']} to fix now, {c['medium']} to fix soon, {c['low']} for later. Source: {scan['source']}.", "",
          "| Priority | Problem | Page | What we saw |", "|---|---|---|---|"]
    L += [f"| {LEVEL[f['severity']]} | {f['rule']} | {_cell(f['page'], 90)} | {_cell(f['evidence'])} |" for f in scan["findings"][:top]]
    if len(scan["findings"]) > top:
        L.append(f"\n{len(scan['findings']) - top} more in scan.json.")

    # 2. Fixes batch
    b = batch["counts"]
    L += ["", f"## 2. Fixes waiting for one yes (batch `{batch['id']}`)", "",
          f"{b['auto']} changes ready to apply, {b['blocked']} written but stopped by the checks, {b['manual']} for a person.", ""]
    auto = [x for x in batch["changes"] if x["how"] == "auto"]
    if auto:
        L += ["| Id | Change | Page | Now | After |", "|---|---|---|---|---|"]
        for x in auto:
            after = "business details for Rajkot and Ahmedabad offices" if x["kind"] == "site_jsonld" else x["after"]
            L.append(f"| {x['cid']} | {KIND.get(x['kind'], x['kind'])} | {_cell(x['url'], 70)} | {_cell(x['before'] or '(empty)', 80)} | {_cell(after, 160)} |")
        L += ["", "**To apply:** Harsh (or a teammate by name when he can't be reached) says yes to this batch, then run GitHub > Actions >",
              "\"SEO apply fixes\" with this run's number and your name, or in Claude Code:",
              f"`python -m seo_engine.apply_batch --batch <this folder>/fixes.json --approved-by \"<name>\"` (add `--only c001,c002` to apply some)."]
    for x in [x for x in batch["changes"] if x["how"] == "blocked"][:5]:
        L.append(f"- Stopped: {KIND.get(x['kind'])} for {_cell(x['url'], 70)}: {'; '.join(x.get('blocks', []))[:200]}")
    manual = [x for x in batch["changes"] if x["how"] == "manual"]
    if manual:
        L += ["", "For a person:"] + [f"- {x['reason']} ({x.get('pages', '')} page(s))" if x.get("pages") else f"- {x['reason']}" for x in manual]

    # 3. AI answers
    L += ["", "## 3. Do AI assistants name DTJ?", ""]
    if probe["mode"] != "live":
        L.append(f"Not run this week (planned {len(probe['planned'])} questions). It needs the Claude API key and/or the DataForSEO login.")
    else:
        s = probe["summary"]
        L.append(f"Asked {s['asked']} times, answered {s['answered']}: DTJ named **{s['dtj_named']}** times, DTJ's site cited **{s['dtj_cited']}** times.")
        if s.get("by_engine"):
            L += ["", "| Assistant | Answered | DTJ named | DTJ cited |", "|---|---|---|---|"]
            L += [f"| {e} | {v['answered']} | {v['dtj_named']} | {v['dtj_cited']} |" for e, v in sorted(s["by_engine"].items())]
        L += ["", "| Question | Where | Assistant | Named | Cited |", "|---|---|---|---|---|"]
        for r in probe["results"]:
            named = "error" if r.get("dtj_named") is None else ("yes" if r["dtj_named"] else "no")
            cited = "error" if r.get("dtj_cited") is None else ("yes" if r["dtj_cited"] else "no")
            L.append(f"| {_cell(r['question'], 80)} | {r.get('place') or 'India'} | {_cell(r.get('engine', ''), 30)} | {named} | {cited} |")
        if s["top_cited_sites"]:
            L += ["", "Sites the answers lean on most (get DTJ listed or mentioned there): " + ", ".join(s["top_cited_sites"])]
        if probe.get("note"):
            L.append(f"\n{probe['note']}")

    # 4. Keywords
    L += ["", "## 4. Keyword plan", ""]
    if not plan:
        L.append("No plan yet: made on the first live run with the DataForSEO login (then every 28 days).")
    else:
        L += [f"Made {plan['made_at'][:10]} from {plan['source']}: {plan['ideas']} searches looked at, {plan['kept']} kept "
              f"(at least {plan['filters']['min_volume']} searches a month, or {plan['filters']['min_volume_city']} for a city; difficulty "
              f"{plan['filters']['max_kd']} or less; someone pays for the click). Cost ${plan['cost_usd']:.2f}.", "",
              "| Page | Type | Main search | Keywords | Searches/month | Difficulty |", "|---|---|---|---|---|---|"]
        for cl in plan["clusters"][:8]:
            L.append(f"| {cl['id']} | {'blog article' if cl['type'] == 'tide' else 'service/city page'} | {_cell(cl['main'], 60)} | "
                     f"{len(cl['keywords'])} | {cl['volume_sum']} | {cl['avg_kd'] if cl['avg_kd'] is not None else 'n/a'} |")

    # 5. City pages
    ready = [r for r in rows if r["status"] == "ready"]
    built = [r for r in rows if r["status"] == "built"]
    need = sorted({r["city"] for r in rows if r["status"] == "needs proof"})
    L += ["", "## 5. City pages", "", f"{len(built)} built, {len(ready)} ready to write, cities still needing real proof: {', '.join(need) or 'none'}."]
    if need:
        L.append("Each city needs at least one client from there who agreed to be named (with a result) plus an office, a review or a photo "
                 "(services/seo-engine/seo_engine/data/local_proof.json).")

    # 6. Page of the week
    L += ["", "## 6. This week's page", ""]
    if topic is None:
        L.append("None this week (see notes).")
    elif draft is None or draft.status == "not-run":
        L.append(f"Planned {'city page' if kind == 'city' else 'article'}: \"{topic['question']}\" ({topic.get('from', 'city matrix')}). "
                 "Not written (needs the Claude API key and --live).")
    else:
        if skeleton and skeleton.get("pages"):
            L.append("Shaped after the top Google results: " + ", ".join(p["url"] for p in skeleton["pages"]) + ".")
        if draft.status == "passed":
            a = draft.article
            L += [f"**{a['title']}** (/{a['slug']}/), {draft.gate['words']} words, cost "
                  f"{'$' + format(draft.cost_usd, '.2f') if draft.cost_usd is not None else 'not available'}.", "", f"> {a['short_answer']}", ""]
            if draft.gate["warnings"]:
                L += ["Reviewer, please look at:"] + [f"- {w}" for w in draft.gate["warnings"]]
        else:
            L.append(f"\"{topic['question']}\": **{draft.status}**. It is not in WordPress.")
            L += [f"- {x}" for x in draft.gate.get("blocks", [])[:10]] + ([f"- {draft.error}"] if draft.error else [])

    L += ["", "## 7. Notes", ""] + ([f"- {n}" for n in notes] or ["- None."])
    L += ["", "## 8. For a person", "",
          "- Say yes (or no) to the fixes batch above.",
          "- Review the draft and press Publish in WordPress (one yes per page).",
          "- Google Business Profiles for Rajkot and Ahmedabad: the address and phone exactly as on the contact page.",
          "- Ask happy clients for a Google review that names the service and the city; add city clients to local_proof.json."]
    return "\n".join(L) + "\n"
