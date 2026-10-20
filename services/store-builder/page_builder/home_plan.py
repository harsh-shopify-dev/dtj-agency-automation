"""Which home sections a brand gets: the AI's plan, made by rules a person can read (Harsh, 13 Oct 2026: "the AI will decide itself according
to the brand what's needed and what not ... a specific section will be must ... if anything can add more impact it should add that section
or else leave if it just makes something repetitive"; "99% we will work on multi product page stores").

Every home section gets one decision, always with its reason:
  must          the page needs it for this kind of store; built whenever its facts exist
  must_missing  the page needs it, but its facts are missing: a gap to fill (never invented)
  add           not needed, but it adds something the page does not already say (proof, a new way to shop, the brand's voice)
  skip          left out: it would repeat another section, it is not for this kind of store, its facts are missing, or the page is
                long enough without it

The rules (recipes/home.json, "plan"): a must list and an impact order of add-ons per store type (multi_product, single_product), the
sections a store type never uses, and a length budget. On top of them three repetition checks: concerns that are mostly the same
collections as the categories, a top strip that says what the trust strip says, and a wave with no band below it. Nothing here touches a
store; the person can still pick sections themselves (run_home --sections), which overrides the plan."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DECORATION = {"wave_home"}  # adds no words or products: it never counts towards the length budget
STRIPS = {"announcement_bar", "trust_band_home"}  # thin strips count as half a section


def policy() -> dict:
    return json.loads((HERE / "recipes" / "home.json").read_text(encoding="utf-8"))["plan"]


def store_type(facts: dict) -> str:
    return facts.get("store_type") or "multi_product"


def _texts(items) -> set[str]:
    return {str(i.get("text", "")).strip().lower() for i in items or [] if i.get("text")}


def _repeats(facts: dict, builder: str, chosen: set[str]) -> str | None:
    """Why this section would only repeat a section already on the page (None = it adds something)."""
    if builder == "concerns_home" and "categories_home" in chosen:
        concern = {i["collection"] for i in facts["concerns"]["items"]}
        category = {i["collection"] for i in facts["categories"]["items"]}
        if len(concern & category) * 2 >= len(concern):
            return "most of its concerns are the same collections the categories already show"
    if builder == "announcement_bar" and "trust_band_home" in chosen:
        top, trust = _texts(facts["announcements"]["items"]), _texts(facts.get("trust_points"))
        if len(top & trust) * 2 >= len(top):
            return "the top strip would mostly say what the trust strip already says"
    if builder == "wave_home" and "concerns_home" not in chosen:
        return "a wave only softens the edge into the shop-by-concern band, and that band is not on this page"
    return None


def plan(report: dict, facts: dict) -> list[dict]:
    """One decision per home section, in the page's own order. `report` is a FULL build's report (every builder ran)."""
    from .assemble_home import OPTIONS, option_of  # assemble_home imports this module

    rules = policy()[store_type(facts)]
    built = {s["kind"] for s in report["sections_built"]}
    missing = {o["section"]: o["reason"] for o in report["sections_omitted"]}
    decisions: dict[str, dict] = {}

    for b in rules["must"]:
        decisions[b] = ({"decision": "must", "reason": rules["why"].get(b, "the page needs it")} if b in built else
                        {"decision": "must_missing", "reason": f"the page needs it, but {missing.get(b, 'its facts are missing')}"})
    chosen = {b for b, d in decisions.items() if d["decision"] == "must"}
    budget = rules["max_sections"] - sum(0.5 if b in STRIPS else 1 for b in chosen if b not in DECORATION)
    for b in rules["add"]:  # in impact order: the strongest add-on first, so the budget is spent where it matters most
        if b not in built:
            decisions[b] = {"decision": "skip", "reason": missing.get(b, "its facts are missing")}
            continue
        why_not = _repeats(facts, b, chosen)
        if why_not:
            decisions[b] = {"decision": "skip", "reason": why_not}
            continue
        cost = 0 if b in DECORATION else (0.5 if b in STRIPS else 1)
        if cost > budget:
            decisions[b] = {"decision": "skip", "reason": f"the page is long enough: {rules['why'].get(b, 'it')} adds less than the sections above it"}
            continue
        decisions[b] = {"decision": "add", "reason": rules["why"].get(b, "it adds something new")}
        chosen.add(b)
        budget -= cost
    for b, why in rules.get("never", {}).items():
        decisions[b] = {"decision": "skip", "reason": why}
    for b in OPTIONS.values():
        decisions.setdefault(b, {"decision": "skip", "reason": "not used for this kind of store"})
    order = report["page_order"]
    ids = {s["kind"]: s["id"] for s in report["sections_built"]}
    rows = [{"option": option_of(b), "builder": b, **d} for b, d in decisions.items()]
    return sorted(rows, key=lambda r: order.index(ids[r["builder"]]) if ids.get(r["builder"]) in order else len(order))


def chosen(rows: list[dict]) -> list[str]:
    return [r["builder"] for r in rows if r["decision"] in ("must", "add")]
