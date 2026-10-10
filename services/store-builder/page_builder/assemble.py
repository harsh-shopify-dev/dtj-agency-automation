"""Assembler: brand profile + product facts -> product page template (JSON) + a report that explains every decision.

    from page_builder.assemble import build_pdp
    result = build_pdp(brand, facts)
    result.template   # the templates/product.<suffix>.json content, ready to push to an UNPUBLISHED theme (a Tier 2 action: a person approves)
    result.report     # direction (with reasons and contrast checks), sections built and omitted (with reasons), provenance, problems, lint findings

Nothing here talks to Shopify or to an AI. It is deterministic: the same brand and facts always give the same page."""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from jsonschema import Draft202012Validator

from . import direction as direction_mod
from . import rules, sections, styling
from .catalog import IMAGE_PREFIX, Catalog

HERE = Path(__file__).resolve().parent
BUY_BUTTONS = "buy_buttons_eYQEYi"
TITLE_GROUP = "group_icgrde"
DIVIDER = "divider_VJhene"
THEME_PRICE = "price_tVjtKg"

WRAP = {  # the theme's section wrapper: full width so a band reaches both screen edges
    "content_direction": "column", "vertical_on_mobile": True, "horizontal_alignment": "flex-start", "vertical_alignment": "center",
    "align_baseline": False, "horizontal_alignment_flex_direction_column": "flex-start", "vertical_alignment_flex_direction_column": "center",
    "gap": 0, "section_width": "full-width", "section_height": "", "section_height_custom": 50, "background_media": "none", "background_color": "",
    "video_position": "cover", "background_image_position": "cover", "toggle_overlay": False, "overlay_color": "#00000026", "overlay_style": "solid",
    "gradient_direction": "to top", "border": "none", "border_width": 1, "border_opacity": 100, "border_color": "", "border_radius": 0,
    "padding-block-start": 0, "padding-block-end": 0,
}


class InputError(Exception):
    pass


def _validate(instance: dict, name: str) -> None:
    schema = json.loads((HERE / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        raise InputError(f"{name}: " + "; ".join(f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in errors[:6]))


@dataclass
class PageModel:
    brand: dict
    facts: dict
    direction: direction_mod.Direction
    catalog: Catalog
    sections: list = field(default_factory=list)
    buybox_sections: list = field(default_factory=list)
    roles: dict = field(default_factory=dict)
    prov: dict = field(default_factory=dict)
    template: dict = field(default_factory=dict)
    demo: bool = False
    demo_items: list = field(default_factory=list)
    demo_pictures: list = field(default_factory=list)


@dataclass
class Result:
    template: dict
    report: dict
    model: PageModel

    @property
    def ok(self) -> bool:
        return not self.report["problems"] and not [f for f in self.report["lint"] if f["severity"] == "error"]


def picture_in_use(key: str, settings: dict, pictures: set[str]) -> bool:
    """A picture slot matters only when the item it belongs to is on the page: `image_4` needs something else numbered 4 (text_4,
    name_4), `review_image` needs another review_ setting; a plain `image` is the section's own picture."""
    digits = re.findall(r"\d+", key)
    if digits:
        return any(re.findall(r"\d+", k) == digits and v not in (None, "") for k, v in settings.items() if k not in pictures)
    prefix = key.rsplit("image", 1)[0].rstrip("_")
    if prefix:
        return any(k.startswith(prefix + "_") and v not in (None, "") for k, v in settings.items() if k not in pictures)
    return True


THEMES = ("horizon", "dawn")
DAWN_PRICE_TYPES = ("price",)
BUY_BUTTON_TYPES = ("buy-buttons", "buy_buttons")


def product_column(template: dict) -> dict:
    """The product section's column of blocks ({blocks, block_order}) whatever the theme: Horizon nests it in product-details,
    Dawn's main-product holds its blocks directly."""
    main = template["sections"]["main"]
    return main["blocks"]["product-details"] if main.get("type") == "product-information" else main


def _insert(order_list: list, keys: list, before: str | None = None, after: str | None = None) -> None:
    idx = order_list.index(before) if before else order_list.index(after) + 1
    for n, k in enumerate(keys):
        order_list.insert(idx + n, k)


def _horizon_template(built, flat, bb, cat) -> dict:
    template = copy.deepcopy(json.loads((HERE / "base" / "product-base.json").read_text(encoding="utf-8")))
    details = template["sections"]["main"]["blocks"]["product-details"]
    details["settings"]["gap"] = 10
    details["blocks"][TITLE_GROUP]["settings"]["gap"] = 4
    order_list = details["block_order"]
    group = details["blocks"][TITLE_GROUP]
    group["blocks"].pop(THEME_PRICE, None)
    group["block_order"] = [k for k in group["block_order"] if k != THEME_PRICE]
    for sec in flat:
        details["blocks"][_key(sec)] = _block_entry(sec, cat)
    _insert(order_list, [_key(s) for s in bb["before_title"]], before=TITLE_GROUP)
    _insert(order_list, [_key(s) for s in bb["after_title"]], after=TITLE_GROUP)
    _insert(order_list, [_key(s) for s in bb["before_picker"]], before=DIVIDER)
    _insert(order_list, [_key(s) for s in bb["before_buttons"]], before=BUY_BUTTONS)
    _insert(order_list, [_key(s) for s in bb["after_buttons"]], after=BUY_BUTTONS)
    for sec in built:
        key = _key(sec)
        template["sections"][sec.id] = {"type": "_blocks", "blocks": {key: _block_entry(sec, cat)}, "block_order": [key], "settings": dict(WRAP)}
        template["order"].append(sec.id)
    return template


def _dawn_template(base: dict, built, flat, bb, cat) -> dict:
    """Dawn (built 9 Oct 2026 for Harsh's Dawn 15.4.1 theme): keep the theme's own product template (its product section, custom blocks,
    related products), put the DTJ buy-box blocks into main-product (it accepts app blocks) in place of the theme's price block, and add
    each DTJ section as one of Dawn's own 'Apps' sections (no page margins: our blocks bring their own side space)."""
    template = copy.deepcopy(base)
    main = template["sections"]["main"]
    if main.get("type") != "main-product":
        raise InputError(f"the Dawn base template's main section is {main.get('type')!r}, not main-product")
    blocks, order_list = main.setdefault("blocks", {}), main.setdefault("block_order", list(main.get("blocks", {})))
    by_type = {}
    for k in order_list:
        by_type.setdefault(blocks[k]["type"], k)
    for k in [k for k in order_list if blocks[k]["type"] in DAWN_PRICE_TYPES]:  # the DTJ price block replaces the theme's price line
        order_list.remove(k)
        blocks.pop(k)
    title = by_type.get("title")
    buttons = next((by_type[t] for t in BUY_BUTTON_TYPES if t in by_type), None)
    picker = by_type.get("variant_picker") or buttons
    if not (title and buttons):
        raise InputError("the Dawn product section needs its title and buy buttons blocks")
    for sec in flat:
        blocks[_key(sec)] = _block_entry(sec, cat)
    _insert(order_list, [_key(s) for s in bb["before_title"]], before=title)
    _insert(order_list, [_key(s) for s in bb["after_title"]], after=title)
    _insert(order_list, [_key(s) for s in bb["before_picker"]], before=picker)
    _insert(order_list, [_key(s) for s in bb["before_buttons"]], before=buttons)
    _insert(order_list, [_key(s) for s in bb["after_buttons"]], after=buttons)
    rest = [sid for sid in template["order"] if sid != "main"]
    template["order"] = ["main"]
    for sec in built:
        key = _key(sec)
        template["sections"][sec.id] = {"type": "apps", "blocks": {key: _block_entry(sec, cat)}, "block_order": [key],
                                        "settings": {"include_margins": False}}
        template["order"].append(sec.id)
    template["order"] += rest  # the theme's own sections below the product (related products) stay last
    return template


def _block_entry(sec: sections.Section, cat: Catalog) -> dict:
    return {"type": cat.block_ref(sec.app, sec.block), "settings": dict(sec.settings)}


def _key(sec: sections.Section) -> str:
    return f"{sec.app.replace('-', '_')}_{sec.block.replace('-', '_')}_{sec.id}"


def _load_recipe(name: str = "pdp") -> dict:
    return json.loads((HERE / "recipes" / f"{name}.json").read_text(encoding="utf-8"))


def build_pdp(brand: dict, facts: dict, *, logo_path: Path | None = None, catalog: Catalog | None = None, copy_overrides: dict | None = None,
              plan: dict | None = None, theme: str = "horizon", base_template: dict | None = None) -> Result:
    """`plan` (from ai_plan.check_plan) replaces the recipe's section choice and order and may set the signature; without it the
    house rules in recipes/pdp.json decide. Either way every section is still built (or refused) by the same builders.
    `theme`: "horizon" (our base template) or "dawn" (then `base_template` is the Dawn theme's own templates/product.json, so its
    product section, custom blocks and other sections are kept)."""
    if theme not in THEMES:
        raise InputError(f"theme {theme!r} is not supported: {', '.join(THEMES)}")
    if theme == "dawn" and not base_template:
        raise InputError("a Dawn page needs the theme's own templates/product.json as base_template")
    _validate(brand, "brand-profile")
    _validate(facts, "product-facts")
    cat = catalog or Catalog()
    direction = direction_mod.derive(brand, logo_path)
    ctx = sections.Ctx(brand, facts, direction, cat, copy_overrides)
    recipe = _load_recipe()
    entries = {e["builder"]: e for e in recipe["sections"]}
    order = recipe.get("overrides", {}).get(brand["category"], {}).get("order") or [e["builder"] for e in recipe["sections"]]
    omitted = []
    if plan:
        if plan.get("signature"):
            direction.signature = plan["signature"]
            direction.why["signature"] = f"Chosen by the plan: {plan['signature']}."
        unknown = [n for n in plan["order"] if n not in sections.BUILDERS]
        if unknown:
            raise InputError(f"plan names unknown sections: {unknown}")
        order = list(plan["order"])
        omitted += [{"section": n, "reason": f"left out by the plan: {r}"} for n, r in plan.get("left_out", {}).items()]
        entries = {}  # the plan has already settled proof_panel vs facts_glance (ai_plan.check_plan)

    built = []
    for name in order:
        entry = entries.get(name, {})
        if entry.get("only_if_signature") and direction.signature not in entry["only_if_signature"]:
            omitted.append({"section": name, "reason": f"only used for the {entry['only_if_signature']} signature, this brand's is {direction.signature}"})
            continue
        if entry.get("unless_signature") and direction.signature in entry["unless_signature"]:
            omitted.append({"section": name, "reason": f"replaced by the {direction.signature} section for this brand"})
            continue
        res = sections.BUILDERS[name](ctx)
        if isinstance(res, sections.Omit):
            omitted.append({"section": name, "reason": res.reason})
        else:
            built.append(res)

    # ---- bands: alternate plain / band, a dark band only for the brand's signature section, story + how share one band
    roles, prev, prev_kind = {}, "band", ""
    for sec in built:
        if sec.role == "none":
            roles[sec.id] = "none"
            continue
        dark_ok = (sec.kind == "proof_panel" and direction.signature == "proof_panel") or (sec.kind == "free_from" and direction.signature == "free_from_band")
        if sec.role == "dark" and dark_ok:
            role = "dark"
        elif sec.kind == "how_split" and prev_kind == "story_split":
            role = prev
        else:
            role = "plain" if prev in ("band", "dark") else "band"
        roles[sec.id] = role
        prev, prev_kind = role, sec.kind
    first_done = False
    for i, sec in enumerate(built):
        styling.apply(sec, roles[sec.id], direction, cat, first=not first_done and roles[sec.id] != "none")
        if roles[sec.id] != "none":
            first_done = True
        if sec.kind == "how_split" and i and built[i - 1].kind == "story_split":  # two cards on one band sit close together
            sec.settings["padding_top"] = 10
            built[i - 1].settings["padding_bottom"] = 10

    # ---- buy box blocks
    bb = sections.buybox_blocks(ctx)
    flat = [s for group in bb.values() for s in group]
    for sec in flat:
        styling.apply(sec, "plain", direction, cat)
        for key in ("padding_top", "padding_bottom", "side_padding", "background"):
            sec.settings.pop(key, None)

    # ---- test pictures on a dev store (facts say demo: true; Harsh, 9 Oct 2026: "in every image option left empty add any image"):
    # every empty picture slot that belongs to something on the page gets one of the product's own pictures, each listed for replacement.
    # Icon slots keep the block's own icons (a photo in a 26 px icon slot only looks broken).
    demo_pictures = []
    pool = [f"{IMAGE_PREFIX}{m['file']}" for m in facts.get("media", [])] if ctx.demo else []
    for sec in built + flat if pool else []:
        specs = cat.settings(sec.app, sec.block)
        pictures = {k for k, spec in specs.items() if spec.get("type") == "image_picker"}
        for key in sorted(pictures, key=lambda k: [int(n) for n in re.findall(r"\d+", k)] or [0]):
            if sec.settings.get(key) or "icon" in key or "icon" in str(specs[key].get("label", "")).lower():
                continue
            if sec.block == "social-proof":  # always five round photos after the rating (rule L14)
                if not key.startswith("avatar_") or int(key.split("_")[1]) > sections.AVATARS:
                    continue
            elif not picture_in_use(key, sec.settings, pictures):
                continue
            sec.settings[key] = pool[len(demo_pictures) % len(pool)]
            demo_pictures.append(f"{sec.id}.{key}")

    # ---- the template, in the theme's own layout
    if theme == "dawn":
        template = _dawn_template(base_template, built, flat, bb, cat)
    else:
        template = _horizon_template(built, flat, bb, cat)

    model = PageModel(brand, facts, direction, cat, built, flat, roles, ctx.prov, template, ctx.demo, demo_pictures=demo_pictures)
    problems = []
    for sec in built + flat:
        problems += cat.validate(sec.app, sec.block, sec.settings)
    findings = rules.lint(model)
    why = (plan or {}).get("why", {})
    report = {
        "recipe": recipe["id"], "chosen_by": "plan" if plan else "house rules", "direction": direction.as_report(),
        "sections_built": [{"id": s.id, "block": f"{s.app}/{s.block}", "role": roles[s.id], "kind": s.kind,
                            **({"why": why[s.kind]} if s.kind in why else {})} for s in built],
        "buybox_blocks": [{"id": s.id, "block": f"{s.app}/{s.block}"} for s in flat],
        "sections_omitted": omitted,
        "needs_replacement": model.demo_items + model.demo_pictures,
        "demo_pictures": model.demo_pictures,
        "provenance": {f"{sid}.{key}": {"kind": v["kind"], "source": v["source"]} for (sid, key), v in ctx.prov.items()},
        "problems": problems,
        "lint": [{"rule": f.rule, "severity": f.severity, "message": f.message} for f in findings],
    }
    return Result(template, report, model)
