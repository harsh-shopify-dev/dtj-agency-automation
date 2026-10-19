"""The "boats": one service page per city (Performance marketing in Rajkot, Shopify development in Ahmedabad, ...).

Built only where real local proof exists (data/local_proof.json), and blocked if it reads too much like another city page
(gates.similarity), because Google ignores copied city pages. Order comes from the keyword plan when there is one (the most
searched "<service> in <city>" first); otherwise offices first, then the service order on the site.
"""
from __future__ import annotations

from pathlib import Path

from . import gates

CITY_ORDER = ["Rajkot", "Ahmedabad", "Surat", "Vadodara"]


def proof_ok(city: dict | None) -> tuple[bool, str]:
    if not city:
        return False, "no entry in local_proof.json"
    clients = [c for c in city.get("clients", []) if c.get("consent") is True and c.get("result")]
    if not clients:
        return False, "needs at least one client from this city who agreed to be named, with a result"
    if not (city.get("office") or city.get("reviews") or city.get("photos")):
        return False, "needs one more piece of local proof: an office, a review or a photo"
    return True, "ready"


def matrix(seeds: dict, proof: dict, plan: dict | None, built: set[str]) -> list[dict]:
    """Every service x city, with its status and (when the keyword plan has it) its search numbers."""
    by_key = {}
    for c in (plan or {}).get("clusters", []):
        if c["type"] == "boat" and c.get("place") and c.get("service"):
            by_key.setdefault((c["service"], c["place"]), c)
    rows = []
    for city in CITY_ORDER:
        ok, why = proof_ok(proof["cities"].get(city))
        for sid, svc in seeds["services"].items():
            cl = by_key.get((sid, city))
            slug = f"{svc['phrases'][0].replace(' ', '-')}-in-{city.lower()}"
            rows.append({"service": sid, "city": city, "slug": slug, "keywords": cl["keywords"] if cl else [svc["phrases"][0] + f" in {city.lower()}"],
                         "volume_sum": cl["volume_sum"] if cl else None, "priority": cl["priority"] if cl else 0,
                         "status": "built" if slug in built else ("ready" if ok else "needs proof"), "why": why,
                         "service_page": svc["page"]})
    return rows


def next_city_page(rows: list[dict]) -> dict | None:
    ready = [r for r in rows if r["status"] == "ready"]
    return max(ready, key=lambda r: (r["priority"], -CITY_ORDER.index(r["city"]))) if ready else None


def topic_for(row: dict, seeds: dict) -> dict:
    svc = seeds["services"][row["service"]]
    return {"id": row["slug"], "slug": row["slug"], "place": row["city"], "main_keyword": row["keywords"][0],
            "keywords": row["keywords"], "question": f"{svc['phrases'][0].capitalize()} in {row['city']} for D2C brands",
            "link_to": svc["page"]}


def local_for_model(city: str, proof: dict, service: str) -> dict:
    c = proof["cities"][city]
    clients = [x for x in c.get("clients", []) if x.get("consent") is True]
    return {"city": city, "office": c.get("office"),
            "clients": sorted(clients, key=lambda x: x.get("service") != service),  # this service's clients first
            "reviews": c.get("reviews", []), "photos": c.get("photos", [])}


def too_similar(text: str, built_dir: Path, limit: float | None = None) -> tuple[bool, float, str | None]:
    """Compare a new city page with every city page already built (their text is kept in built_dir)."""
    limit = limit if limit is not None else gates.load_json("rules.json")["city_page"]["max_similarity"]
    worst, worst_name = 0.0, None
    for f in sorted(built_dir.glob("*.txt")) if built_dir.exists() else []:
        sim = gates.similarity(text, f.read_text(encoding="utf-8"))
        if sim > worst:
            worst, worst_name = sim, f.stem
    return worst > limit, round(worst, 3), worst_name
