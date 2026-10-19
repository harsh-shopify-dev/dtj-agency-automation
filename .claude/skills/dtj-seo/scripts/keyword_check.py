"""Filter keyword rows with the engine's own rules (keywords.keep / page_type / priority), on demand.

Input: a JSON list of rows from DataForSEO or the OpenSEO connector. Accepted field names:
  keyword | query, volume | search_volume, kd | keyword_difficulty | difficulty, cpc, intent | search_intent
Output: kept rows (sorted by the engine's priority) with page type (tide = blog article, boat = service/city page), place, service,
and the rejected rows with the reason. Every number is the source's; this script only filters and sorts.

  python .claude/skills/dtj-seo/scripts/keyword_check.py rows.json --source "OpenSEO research_keywords, India, 19 Oct 2026" \
      --out .work/seo/research/<date>-<topic>.json
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone

from _engine import read_json, write_json
from seo_engine import gates, keywords

ALIASES = {"keyword": ("keyword", "query", "key"), "volume": ("volume", "search_volume", "monthly_searches"),
           "kd": ("kd", "keyword_difficulty", "difficulty"), "cpc": ("cpc",), "intent": ("intent", "search_intent", "main_intent")}


def normalise(row: dict) -> dict:
    out = {}
    for field, names in ALIASES.items():
        out[field] = next((row[n] for n in names if row.get(n) is not None), None)
    if isinstance(out["intent"], list):
        out["intent"] = out["intent"][0] if out["intent"] else None
    if isinstance(out["intent"], str):
        out["intent"] = out["intent"].lower()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rows", help="JSON file: a list of keyword rows")
    ap.add_argument("--source", required=True, help="where the numbers came from, with the date (shown in the result)")
    ap.add_argument("--out", help="save the result here")
    args = ap.parse_args()

    seeds = gates.load_json("seeds.json")
    rows = read_json(args.rows)
    if isinstance(rows, dict):
        rows = rows.get("items") or rows.get("keywords") or rows.get("rows") or []
    kept, rejected = [], []
    for raw in rows:
        k = normalise(raw)
        if not k["keyword"]:
            continue
        ok, why = keywords.keep(k, seeds)
        if not ok:
            rejected.append({**k, "why": why})
            continue
        place, tier = keywords.place_of(k["keyword"], seeds)
        kept.append({**k, "type": keywords.page_type(k), "place": place, "tier": tier,
                     "service": keywords.service_of(k["keyword"], seeds), "priority": keywords.priority(k),
                     "slug": keywords.slugify(k["keyword"])})
    kept.sort(key=lambda r: r["priority"], reverse=True)
    result = {"made_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "source": args.source,
              "filters": {"min_volume": keywords.MIN_VOLUME, "min_volume_city": keywords.MIN_VOLUME_LOCAL,
                          "max_kd": keywords.MAX_KD, "cpc": "> 0"},
              "kept": kept, "rejected": rejected,
              "note": "Grouping into pages needs each keyword's Google top 10 (3+ shared pages = one page); not done here."}
    if args.out:
        write_json(args.out, result)

    print(f"Source: {args.source}. {len(kept)} kept, {len(rejected)} rejected.")
    print("| Keyword | Searches/month | Difficulty | CPC | Page type | Place |")
    print("|---|---|---|---|---|---|")
    for r in kept:
        page = "blog article" if r["type"] == "tide" else "service/city page"
        print(f"| {r['keyword']} | {r['volume']} | {r['kd'] if r['kd'] is not None else 'n/a'} | {r['cpc']} | {page} | {r['place'] or 'India'} |")
    reasons: dict[str, int] = {}
    for r in rejected:
        reasons[r["why"]] = reasons.get(r["why"], 0) + 1
    if reasons:
        print("Rejected: " + "; ".join(f"{why} ({n})" for why, n in sorted(reasons.items(), key=lambda x: -x[1])))
    if args.out:
        print(f"Saved: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
