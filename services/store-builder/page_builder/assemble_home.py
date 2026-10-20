"""Home page assembler (Harsh, 13 Oct 2026): brand profile + home facts -> templates/index.json + a report that explains every decision.

    from page_builder.assemble_home import build_home
    result = build_home(brand, facts)
    result.template   # the templates/index.json content, ready for an UNPUBLISHED theme (a Tier 2 action: a person approves)
    result.report     # niche, direction, sections built and omitted (with reasons), provenance, problems, lint findings

Same rules as build_pdp: deterministic, nothing talks to Shopify or an AI, every text has a recorded origin, a section whose facts are missing is
omitted with a reason. What is new is the NICHE: the brand's category maps to a niche (niches.py); the recipe's order and the hero layout follow it,
and each section picks the block made for that niche first (then blocks that suit every niche). The theme's own featured-products section stays."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from . import direction as direction_mod
from . import home_sections, niches, rules, sections, styling
from .assemble import WRAP, InputError, PageModel, Result, _block_entry, _key, _validate
from .catalog import Catalog

HERE = Path(__file__).resolve().parent
THEME_PREFIX = "theme:"

# the palette method's pacing down a home page (Harsh, 19 Oct 2026: "apply better colors ... like a top level figma designer"): the soft blue is not
# used four times in a row any more. White, soft blue, ONE solid brand band, white, the accent family's mint, white, one deep ink band for the
# customer stories, white, soft blue, white. A kind that is not listed alternates as before; a neighbour never repeats (lint L04).
RAMPS_RHYTHM = {"categories_home": "plain", "best_sellers_home": "band", "before_after_home": "plain", "compare_home": "mint", "story_home": "plain",
                "video_reviews_home": "dark", "press_home": "plain", "concerns_home": "band", "faq": "plain"}



def _recipe() -> dict:
    return json.loads((HERE / "recipes" / "home.json").read_text(encoding="utf-8"))


def build_home(brand: dict, facts: dict, *, logo_path: Path | None = None, catalog: Catalog | None = None, copy_overrides: dict | None = None,
               base_template: dict | None = None, only: set[str] | None = None) -> Result:
    """only: the builders this page uses (home_plan.py or the person's pick); the rest are left out, so bands, colours and the wave are
    worked out for the page as it will really be. None = every builder (the full build the plan is made from)."""
    _validate(brand, "brand-profile")
    _validate(facts, "home-facts")
    cat = catalog or Catalog()
    direction = direction_mod.derive(brand, logo_path)
    ctx = sections.Ctx(brand, facts, direction, cat, copy_overrides)
    recipe = _recipe()
    niche = niches.niche_of(brand["category"])
    order = recipe.get("overrides", {}).get(niche, {}).get("order") or [e.get("builder") or THEME_PREFIX + e["theme"] for e in recipe["sections"]]
    base = copy.deepcopy(base_template or json.loads((HERE / "base" / "home-base.json").read_text(encoding="utf-8")))

    unless = {THEME_PREFIX + e["theme"]: e["unless"] for e in recipe["sections"] if e.get("theme") and e.get("unless")}
    built, omitted, slots = [], [], []  # slots: the final order, our sections and the theme's own ones
    for name in order:
        if name.startswith(THEME_PREFIX):
            slots.append(("pending", name))  # decided after every builder ran: it may give way to one of our sections
            continue
        if only is not None and name not in only:
            omitted.append({"section": name, "reason": "not on this page (the plan or the person's choice)"})
            continue
        res = home_sections.HOME_BUILDERS[name](ctx)
        if isinstance(res, sections.Omit):
            omitted.append({"section": name, "reason": res.reason})
        else:
            built.append(res)
            slots.append(("dtj", res))
    kinds = {s.kind for s in built}
    resolved = []
    for kind, item in slots:
        if kind != "pending":
            resolved.append((kind, item))
            continue
        if unless.get(item) in kinds:
            omitted.append({"section": item, "reason": f"{unless[item]} already shows the shop's products"})
            continue
        if facts.get("store_type") == "single_product":  # one product: the hero's button leads to it; a product row would repeat it
            omitted.append({"section": item, "reason": "one product: the hero's button already leads to it"})
            continue
        key = next((k for k, v in base["sections"].items() if v.get("type") == item[len(THEME_PREFIX):].replace("_", "-")), None)
        if key:
            resolved.append(("theme", key))
        else:
            omitted.append({"section": item, "reason": "the base template has no such section"})
    slots = resolved

    # ---- bands: the hero and the strip carry their own look; the rest alternate plain / band, never two neighbours alike
    roles, prev = {}, "band"
    for sec in built:
        if sec.role == "none" or sec.kind == "hero_home":
            roles[sec.id] = "none"
            continue
        if direction.ramps and sec.kind == "value_props_home":  # the palette method's one solid brand band: the signature section
            roles[sec.id], prev = "accent", "band"
            continue
        role = "plain" if prev in ("band", "mint") else "band"
        if direction.ramps and sec.kind in RAMPS_RHYTHM:  # the palette method's pacing: white, soft blue, solid blue, white, mint, white, deep ink...
            want = RAMPS_RHYTHM[sec.kind]
            if want != prev and (want != "dark" or sum(1 for v in roles.values() if v == "dark") < direction.max_dark):
                role = want
        roles[sec.id] = role
        prev = role
    first_done = False
    for sec in built:
        styling.apply(sec, roles[sec.id], direction, cat, first=not first_done and roles[sec.id] != "none")
        styling.apply_home_type(sec, cat)  # one heading scale for the whole page (styling.HOME_TYPE)
        if roles[sec.id] != "none":
            first_done = True

    # ---- a wave takes its two colours from its neighbours: the colour above as its background, the colour below as the wave. With the
    # same colour on both sides there is no edge to soften, and it is left out.
    page_bg = direction.roles["bg"]

    def colour(slot) -> str:
        return (slot[1].settings.get("background") if slot[0] == "dtj" else None) or page_bg

    for kind, item in list(slots):
        if kind != "dtj" or item.block != "wave-divider":
            continue
        k = slots.index((kind, item))
        above, below = (colour(slots[k - 1]) if k > 0 else page_bg), (colour(slots[k + 1]) if k + 1 < len(slots) else None)
        if below is None or above.upper() == below.upper():
            slots.pop(k)
            built.remove(item)
            omitted.append({"section": item.kind, "reason": "nothing follows it on this page" if below is None else
                            "the sections above and below share one colour: there is no edge for a wave to soften"})
            continue
        item.settings.update({"background": above, "wave_color": below})

    # ---- the vertical rhythm (styling.HOME_SPACE, measured on the reference pages): the space sits on the theme's section wrapper, which the
    # theme scales to 0.7 on phones, so one number is the laptop and the phone rhythm. The wrapper carries the band colour, the block's own
    # padding is 0, so a band is one colour from edge to edge. The hero and thin strips keep their own height.
    ours = [item for kind, item in slots if kind == "dtj"]
    rhythm = dict(zip((s.id for s in ours), styling.home_rhythm([s.kind for s in ours])))
    wrappers = {}
    for sec in ours:
        top, bottom = rhythm[sec.id] or (0, 0)
        wrap = dict(WRAP)
        if rhythm[sec.id] and (top or bottom):
            for key in ("padding_top", "padding_bottom"):
                if cat.has(sec.app, sec.block, key):
                    sec.settings[key] = 0
            wrap.update({"padding-block-start": top, "padding-block-end": bottom, "background_color": sec.settings.get("background") or ""})
        wrappers[sec.id] = wrap

    # ---- the template: our sections as the theme's own Apps wrappers, the theme's own featured products where the recipe puts them
    template = {"sections": {}, "order": []}
    for kind, item in slots:
        if kind == "theme":
            template["sections"][item] = base["sections"][item]
            template["order"].append(item)
        else:
            template["sections"][item.id] = {"type": "_blocks", "blocks": {_key(item): _block_entry(item, cat)}, "block_order": [_key(item)], "settings": wrappers[item.id]}
            template["order"].append(item.id)

    model = PageModel(brand, facts, direction, cat, built, [], roles, ctx.prov, template, bool(facts.get("demo")))
    problems = []
    for sec in built:
        problems += cat.validate(sec.app, sec.block, sec.settings)
    findings = rules.lint(model)
    samples = sorted(f"{sid}.{key}" for (sid, key), v in ctx.prov.items() if v["kind"] == "sample")
    report = {
        "recipe": recipe["id"], "niche": niche, "category": brand["category"], "chosen_by": "house rules", "direction": direction.as_report(),
        "rhythm": {sid: ({"top": v[0], "bottom": v[1]} if v else "its own") for sid, v in rhythm.items()},  # the theme wrapper's padding (0.7 of it on phones)
        "sections_built": [{"id": s.id, "block": f"{s.app}/{s.block}", "role": roles[s.id], "kind": s.kind,
                            "niche_fit": niches.fit_label(f"{s.app}/{s.block}", brand["category"])} for s in built],
        "page_order": [item if kind == "theme" else item.id for kind, item in slots],
        "samples": samples,
        "sections_omitted": omitted,
        "needs_replacement": samples + model.demo_items,
        "provenance": {f"{sid}.{key}": {"kind": v["kind"], "source": v["source"]} for (sid, key), v in ctx.prov.items()},
        "evidence": {s.id: s.evidence for s in built if getattr(s, "evidence", None)},  # the proof behind press, before/after, comparison
        "problems": problems,
        "lint": [{"rule": f.rule, "severity": f.severity, "message": f.message} for f in findings],
    }
    return Result(template, report, model)


# ------------------------------------------------------------------------------------------------ options and partial updates
# Harsh, 13 Oct 2026: "it should only design the homepage when told, like I should have options that what needs to be updated". A home page
# is never designed on its own; the person sees these options (run_home --list) and picks the sections to build or update (--sections).
OPTIONS = {  # the name a person picks -> the builder that makes it
    "announcement": "announcement_bar", "hero": "hero_home", "trust": "trust_band_home", "press": "press_home", "categories": "categories_home",
    "best-sellers": "best_sellers_home", "reasons": "value_props_home", "before-after": "before_after_home", "compare": "compare_home",
    "story": "story_home", "wave": "wave_home", "concerns": "concerns_home", "videos": "video_reviews_home", "faq": "faq",
}


def option_of(builder: str) -> str:
    return next((k for k, v in OPTIONS.items() if v == builder), builder)


def pick(names: str) -> list[str]:
    """'hero, best-sellers' (or 'all') -> the builder names; an unknown name stops with the list of known ones."""
    wanted = [n.strip().lower() for n in names.split(",") if n.strip()]
    if wanted == ["all"]:
        return list(OPTIONS.values())
    builders = []
    for n in wanted:
        b = OPTIONS.get(n) or (n if n in OPTIONS.values() else None)
        if not b:
            raise InputError(f"unknown home section {n!r}; pick from: {', '.join(OPTIONS)} (or all)")
        builders.append(b)
    return builders


def options(result: Result) -> list[dict]:
    """Every section a person may pick, in page order: ready (with its block) or not (with the facts it is missing)."""
    built = {s["kind"]: s for s in result.report["sections_built"]}
    missing = {o["section"]: o["reason"] for o in result.report["sections_omitted"]}
    out = []
    for name, builder in OPTIONS.items():
        if builder in built:
            out.append({"option": name, "ready": True, "section": built[builder]["id"], "block": built[builder]["block"]})
        else:
            out.append({"option": name, "ready": False, "reason": missing.get(builder, "not in this niche's recipe")})
    order = result.report["page_order"]
    return sorted(out, key=lambda o: order.index(o["section"]) if o.get("section") in order else len(order))


def merge(current: dict, page: dict, chosen_ids: list[str]) -> tuple[dict, list[dict]]:
    """Put ONLY the chosen sections of the freshly built page into the home page as it is now. A section that is already there (same id)
    is replaced where it stands; a new one goes next to its neighbours from the built page; every other section, ours or not, is kept exactly
    as it is (hand edits in the theme editor included)."""
    out = copy.deepcopy(current)
    out.setdefault("sections", {})
    out.setdefault("order", [])
    order, changes = page["order"], []
    for sid in [s for s in order if s in chosen_ids]:
        if sid in out["sections"]:
            out["sections"][sid] = copy.deepcopy(page["sections"][sid])
            changes.append({"section": sid, "change": "replaced"})
            continue
        i = order.index(sid)
        before = next((s for s in reversed(order[:i]) if s in out["order"]), None)
        after = next((s for s in order[i + 1:] if s in out["order"]), None)
        pos = out["order"].index(before) + 1 if before else (out["order"].index(after) if after else (0 if i == 0 else len(out["order"])))
        out["order"].insert(pos, sid)
        out["sections"][sid] = copy.deepcopy(page["sections"][sid])
        changes.append({"section": sid, "change": "added", "after": out["order"][pos - 1] if pos else "(top of the page)"})
    return out, changes
