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


def _recipe() -> dict:
    return json.loads((HERE / "recipes" / "home.json").read_text(encoding="utf-8"))


def build_home(brand: dict, facts: dict, *, logo_path: Path | None = None, catalog: Catalog | None = None, copy_overrides: dict | None = None,
               base_template: dict | None = None) -> Result:
    _validate(brand, "brand-profile")
    _validate(facts, "home-facts")
    cat = catalog or Catalog()
    direction = direction_mod.derive(brand, logo_path)
    ctx = sections.Ctx(brand, facts, direction, cat, copy_overrides)
    recipe = _recipe()
    niche = niches.niche_of(brand["category"])
    order = recipe.get("overrides", {}).get(niche, {}).get("order") or [e.get("builder") or THEME_PREFIX + e["theme"] for e in recipe["sections"]]
    base = copy.deepcopy(base_template or json.loads((HERE / "base" / "home-base.json").read_text(encoding="utf-8")))

    built, omitted, slots = [], [], []  # slots: the final order, our sections and the theme's own ones
    for name in order:
        if name.startswith(THEME_PREFIX):
            key = next((k for k, v in base["sections"].items() if v.get("type") == name[len(THEME_PREFIX):].replace("_", "-")), None)
            if key:
                slots.append(("theme", key))
            else:
                omitted.append({"section": name, "reason": "the base template has no such section"})
            continue
        res = home_sections.HOME_BUILDERS[name](ctx)
        if isinstance(res, sections.Omit):
            omitted.append({"section": name, "reason": res.reason})
        else:
            built.append(res)
            slots.append(("dtj", res))

    # ---- bands: the hero and the strip carry their own look; the rest alternate plain / band, never two neighbours alike
    roles, prev = {}, "band"
    for sec in built:
        if sec.role == "none" or sec.kind == "hero_home":
            roles[sec.id] = "none"
            continue
        role = "plain" if prev == "band" else "band"
        roles[sec.id] = role
        prev = role
    first_done = False
    for sec in built:
        styling.apply(sec, roles[sec.id], direction, cat, first=not first_done and roles[sec.id] != "none")
        if roles[sec.id] != "none":
            first_done = True

    # ---- the template: our sections as the theme's own Apps wrappers, the theme's own featured products where the recipe puts them
    template = {"sections": {}, "order": []}
    for kind, item in slots:
        if kind == "theme":
            template["sections"][item] = base["sections"][item]
            template["order"].append(item)
        else:
            template["sections"][item.id] = {"type": "_blocks", "blocks": {_key(item): _block_entry(item, cat)}, "block_order": [_key(item)], "settings": dict(WRAP)}
            template["order"].append(item.id)

    model = PageModel(brand, facts, direction, cat, built, [], roles, ctx.prov, template, bool(facts.get("demo")))
    problems = []
    for sec in built:
        problems += cat.validate(sec.app, sec.block, sec.settings)
    findings = rules.lint(model)
    samples = sorted(f"{sid}.{key}" for (sid, key), v in ctx.prov.items() if v["kind"] == "sample")
    report = {
        "recipe": recipe["id"], "niche": niche, "chosen_by": "house rules", "direction": direction.as_report(),
        "sections_built": [{"id": s.id, "block": f"{s.app}/{s.block}", "role": roles[s.id], "kind": s.kind,
                            "niche_fit": niches.fit_label(f"{s.app}/{s.block}", brand["category"])} for s in built],
        "page_order": [item if kind == "theme" else item.id for kind, item in slots],
        "samples": samples,
        "sections_omitted": omitted,
        "needs_replacement": samples + model.demo_items,
        "provenance": {f"{sid}.{key}": {"kind": v["kind"], "source": v["source"]} for (sid, key), v in ctx.prov.items()},
        "problems": problems,
        "lint": [{"rule": f.rule, "severity": f.severity, "message": f.message} for f in findings],
    }
    return Result(template, report, model)
