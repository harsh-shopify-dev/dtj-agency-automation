"""Monthly keyword research: real searches from DataForSEO, filtered to the ones DTJ can win, grouped into pages.

1. Ideas: DataForSEO keyword_ideas for the seeds in data/seeds.json (India).
2. Filters (Harsh's, 14 Oct 2026): searches per month >= 50 (>= 10 for city searches: few searches, but close to buying),
   difficulty <= 30, cost per click > 0 (someone pays for the click, so it brings customers), off-topic words removed.
3. Type: informational = "tide" (blog article); commercial / transactional = "boat" (service or city page). Navigational is dropped.
4. Groups: keywords whose Google top 10 share >= 3 pages are one page (Google already treats them as one topic). A page aims at
   5+ keywords. Only the strongest MAX_SERP candidates are looked up, to keep the cost down.
Every number in the plan comes from DataForSEO and the plan says so.
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timezone

from . import gates
from .dataforseo import Client

MIN_VOLUME, MIN_VOLUME_LOCAL, MAX_KD = 50, 10, 30
MAX_SERP = 30
OVERLAP = 3
CLUSTER_TARGET = 5


def slugify(text: str, max_words: int = 7) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return "-".join(words[:max_words])


def seed_list(seeds: dict) -> list[str]:
    out = []
    for svc in seeds["services"].values():
        for phrase in svc["phrases"]:
            for tier in ("local", "state", "national"):
                out += [f"{phrase} in {p.lower()}" for p in seeds["places"][tier]]
    return list(dict.fromkeys(out + seeds["pains"]))


def place_of(keyword: str, seeds: dict) -> tuple[str | None, str | None]:
    k = keyword.lower()
    for tier in ("local", "state"):
        for p in seeds["places"][tier]:
            if re.search(rf"\b{p.lower()}\b", k):
                return p, tier
    return None, "national"


def service_of(keyword: str, seeds: dict) -> str | None:
    k = keyword.lower()
    best = None
    for sid, svc in seeds["services"].items():
        for phrase in svc["phrases"]:
            words = phrase.replace("agency", "").replace("company", "").split()
            if all(w in k for w in words) and (best is None or len(words) > best[1]):
                best = (sid, len(words))
    return best[0] if best else None


def keep(k: dict, seeds: dict) -> tuple[bool, str]:
    text = k["keyword"].lower()
    if any(re.search(rf"\b{re.escape(w)}\b", text) for w in seeds["exclude_words"]):
        return False, "off-topic word"
    if not any(re.search(rf"\b{re.escape(w)}\b", text) for w in seeds["must_contain_one"]):
        return False, "not about what DTJ does"
    place, tier = place_of(text, seeds)
    floor = MIN_VOLUME_LOCAL if tier in ("local", "state") and place else MIN_VOLUME
    if (k.get("volume") or 0) < floor:
        return False, f"fewer than {floor} searches a month"
    if k.get("kd") is not None and k["kd"] > MAX_KD:
        return False, f"difficulty above {MAX_KD}"
    if not (k.get("cpc") or 0) > 0:
        return False, "nobody pays for this click"
    if k.get("intent") == "navigational":
        return False, "people look for a specific site"
    return True, "kept"


def page_type(k: dict) -> str:
    if k.get("intent") in ("commercial", "transactional") or re.search(r"\b(agency|company|services?|developer|consultant)\b", k["keyword"]):
        return "boat"
    return "tide"


def priority(k: dict) -> float:
    """More searches, easier to rank, more valuable clicks. Unknown difficulty counts as 30 (the ceiling)."""
    kd = k["kd"] if k.get("kd") is not None else MAX_KD
    return round((k.get("volume") or 0) * (100 - kd) / 100 * (1 + math.log1p(k.get("cpc") or 0)), 2)


def cluster(cands: list[dict], serps: dict[str, list[str]]) -> list[list[dict]]:
    """Greedy: the strongest keyword starts a group; others join the first group whose leader shares >= OVERLAP of its top 10."""
    groups: list[list[dict]] = []
    for k in sorted(cands, key=priority, reverse=True):
        mine = set(serps.get(k["keyword"], []))
        for g in groups:
            lead = set(serps.get(g[0]["keyword"], []))
            if g[0]["type"] == k["type"] and mine and len(mine & lead) >= OVERLAP:
                g.append(k)
                break
        else:
            groups.append([k])
    return groups


def build_plan(client: Client, seeds: dict | None = None, *, now: datetime | None = None) -> dict:
    seeds = seeds or gates.load_json("seeds.json")
    now = now or datetime.now(timezone.utc)
    ideas = client.keyword_ideas(seed_list(seeds))
    kept, rejected = [], {}
    for k in {i["keyword"].lower(): i for i in ideas}.values():
        ok, why = keep(k, seeds)
        if ok:
            k["type"] = page_type(k)
            k["place"], k["tier"] = place_of(k["keyword"], seeds)
            k["service"] = service_of(k["keyword"], seeds)
            k["priority"] = priority(k)
            kept.append(k)
        else:
            rejected[why] = rejected.get(why, 0) + 1
    kept.sort(key=priority, reverse=True)
    serps, serp_note = {}, None
    for k in kept[:MAX_SERP]:
        try:
            serps[k["keyword"]] = [r["url"] for r in client.serp(k["keyword"])][:10]
        except Exception as exc:  # noqa: BLE001 - the cap or an error stops the lookups; groups are made from what we have
            serp_note = f"Google lookups stopped after {len(serps)}: {exc}"
            break
    groups = cluster(kept, serps)
    clusters = []
    for g in groups:
        main = g[0]
        clusters.append({
            "id": slugify(main["keyword"]), "slug": slugify(main["keyword"]), "type": main["type"], "main": main["keyword"],
            "keywords": [x["keyword"] for x in g], "volume_sum": sum(x.get("volume") or 0 for x in g),
            "avg_kd": round(sum(x["kd"] for x in g if x.get("kd") is not None) / max(1, sum(1 for x in g if x.get("kd") is not None)), 1)
            if any(x.get("kd") is not None for x in g) else None,
            "max_cpc": max((x.get("cpc") or 0) for x in g), "priority": round(sum(priority(x) for x in g), 2),
            "place": main["place"], "tier": main["tier"], "service": main["service"],
            "grouped_by_google": main["keyword"] in serps, "meets_target": len(g) >= CLUSTER_TARGET,
            "top_urls": serps.get(main["keyword"], []),
        })
    clusters.sort(key=lambda c: c["priority"], reverse=True)
    return {
        "made_at": now.isoformat(), "source": "DataForSEO keyword_ideas (India, English) and Google mobile top 10 (serp/google/organic)",
        "filters": {"min_volume": MIN_VOLUME, "min_volume_city": MIN_VOLUME_LOCAL, "max_kd": MAX_KD, "cpc": "> 0", "overlap": OVERLAP},
        "ideas": len(ideas), "kept": len(kept), "rejected": rejected, "serp_lookups": len(serps), "note": serp_note,
        "cost_usd": round(client.spent, 4), "clusters": clusters,
    }


def plan_age_days(plan: dict | None, now: datetime | None = None) -> int | None:
    if not plan or not plan.get("made_at"):
        return None
    return ((now or datetime.now(timezone.utc)) - datetime.fromisoformat(plan["made_at"])).days
