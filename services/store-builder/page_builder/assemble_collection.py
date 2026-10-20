"""Collection page assembler (Harsh, 20 Oct 2026: "design the collection page adding that section and ensure all the ratings and everything
appears perfectly"): brand profile + the client's facts -> templates/collection.json + a report that explains every decision.

    from page_builder.assemble_collection import build_collection
    result = build_collection(brand, facts, page)   # page = collection-page.json (optional settings), facts = the client's home-facts.json
    result.template   # the templates/collection.json content, for an UNPUBLISHED theme (Tier 2: a person approves the write)
    result.report

The page, top to bottom (one template serves EVERY collection of the store):
  header    the collection's own title (H1) and description: the theme's text blocks reading {{ closest.collection.* }}, on the brand's
            soft tint, compact so the first products start inside the first phone screen (COLLECTION_TARGETS, from the 20 Oct 2026 study)
  products  DTJ Product List, the exact replica of Proeffex's product list, its collection left empty so it shows the page's own: up to 50 products (one
            Shopify page), the count and Sort above them, the card's real ratings (reviews.rating metafields only; a placeholder rating with
            0 reviews is never shown), shade swatches, % OFF from the real compare-at price, whole-tag badges only
  trust     optional: 3 to 6 STORE-WIDE points (shipping, payment, returns) from collection-page.json, each with its source; never a product claim
  faq       optional: the FAQ of the client's facts (the same questions as the home page)
The theme's own product grid (main-collection) and any older product-list copy stay in the file, switched OFF (reversible: switch them on).
Same rules as the other builders: deterministic, nothing talks to Shopify or an AI, every text has a recorded origin, a section whose facts
are missing is left out with the reason."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from . import direction as direction_mod
from . import home_sections, niches, sections, styling
from .assemble import WRAP, InputError, Result, _block_entry, _key, _validate
from .catalog import Catalog

HERE = Path(__file__).resolve().parent
PARTS = json.loads((HERE / "base" / "horizon-collection-parts.json").read_text(encoding="utf-8"))
COLLECTION_FILE = "templates/collection.json"
LIST_APP, LIST_BLOCK = "dtj-collection", "product-list"

# From the 20 Oct 2026 study of 12 public collection pages (.work/collection-page-reference/, 8 measured cleanly: Proeffex, Minimalist,
# Sugar, boAt, Bombay Shaving Company, Blueland, Gymreapers, KittySpout): every page shows ratings on the cards and a Sort control; the
# title area is compact, so the first product picture starts 282-413 px down a 390 px phone (median about 360) and 375-617 px down a
# 1280 px laptop (KittySpout's tall banner: 1360); 2 columns on phones, 3-4 on laptops, 10-16 px between phone cards.
# The numbers: .claude/skills/dtj-collection-page/references/study.md.
COLLECTION_TARGETS = {"phone_first_image_max": 420, "desktop_first_image_max": 620, "phone_columns": 2, "desktop_columns": 4}
# The title is the theme's own h3 size (32 px on elevate-with-harsh's draft): the study's titles are 24-50 px on a laptop (about 36 in the
# middle) and 20-34 on a phone; the theme's h2 (48 px there) pushed the first products further down for no gain.
# the theme wrapper's padding (Horizon scales it to 0.7 on phones, never under 20 px): a compact title band, then the products, then
# the page's usual section step (styling.HOME_SPACE) before anything else
COLLECTION_SPACE = {"header": (40, 28), "header_with_nav": (32, 12), "nav": (8, 24), "products": (24, 80)}
# Colour placement (Harsh, 19 Oct 2026: every brand has its own palette, placed where it does a job): the title and the collection links sit
# on the page colour; the products sit on the brand's soft tint (the palette's panel colour), so the replica's white framed cards stand
# out from their ground as they do on Proeffex's own collection page (white cards on #F5F5F5, measured in the study).
COLLECTION_COLOURS = {"header": "bg", "nav": "bg", "products": "panel"}
# the links row: small tiles to move between collections (navigation, not a headline), one swipeable row on phones
NAV = {"heading": "", "labels": "show", "mobile_layout": "scroll", "tile_size": 88, "tile_size_mobile": 64, "gap": 20, "label_size": 13,
       "container_width": 1200, "hover_zoom": True, "corner_radius": 12}
# the product grid around the replica's cards (the card itself stays exactly the original's): Proeffex's own collection page keeps 16 px
# between laptop cards and 12 between phone cards (the block caps phone gaps at 12)
PRODUCT_LIST = {"show_heading": False, "show_view_all": False, "show_sort": True, "max_products": 50, "layout_type": "grid",
                "columns": 4, "mobile_columns": "2", "columns_gap": 16, "rows_gap": 24, "gap": 16, "section_width": "page-width",
                "padding-block-start": 0, "padding-block-end": 0, "pf_hide_no_reviews": True}
PAGE_COLLECTION = ""  # empty: on a collection page the block shows that page's own collection (Shopify refused autofill on 20 Oct 2026)
OPTIONS = ("header", "nav", "products", "trust", "faq")
DEFAULT = ("header", "nav", "products", "trust")
# switched off where this page's product list takes over: the theme's own product grid and the earlier test copies of the Proeffex sections
# (a theme product-list section, e.g. "You may also like", is NOT this collection's grid and is left alone)
GRID_TYPES = {"main-collection", "proeffex-producttab-collection", "proeffex-collection", "proeffex-product-list"}


def _text_block(text: str, preset: str, align: str, color: str, max_width: str, font: str) -> dict:
    return {"type": "text", "settings": {
        "text": text, "width": "100%", "max_width": max_width, "alignment": align, "type_preset": preset, "font": font, "font_size": "",
        "line_height": "normal", "letter_spacing": "normal", "case": "none", "wrap": "balance", "text_color": color, "background": False,
        "background_color": "#00000026", "corner_radius": 0, "padding-block-start": 0, "padding-block-end": 0,
        "padding-inline-start": 0, "padding-inline-end": 0}, "blocks": {}}


def check_theme_settings(part: str, values: dict) -> list[str]:
    """The theme's own section / block settings checked against Horizon 4.2.0's schema (base/horizon-collection-parts.json)."""
    spec, problems = PARTS[part], []
    for key, value in values.items():
        s = spec.get(key)
        if s is None:
            problems.append(f"theme {part}: unknown setting {key!r}")
        elif s["type"] == "select" and value not in s["options"]:
            problems.append(f"theme {part}: {key}={value!r} is not one of {s['options']}")
        elif s["type"] == "range" and not (isinstance(value, (int, float)) and s["min"] <= value <= s["max"]):
            problems.append(f"theme {part}: {key}={value!r} is outside {s['min']}..{s['max']}")
        elif s["type"] == "checkbox" and not isinstance(value, bool):
            problems.append(f"theme {part}: {key} must be true or false")
    return problems


def _on(r: dict, role: str) -> str:
    """The text colour that belongs on a ground role."""
    return {"bg": r["text"], "panel": r["on_panel"], "band": r["on_band"]}[role]


def header_section(direction, with_nav: bool = False) -> dict:
    """The collection's own title and description: one template, every collection. Tighter at the bottom when the links row follows, so
    the two read as one header."""
    r, ground = direction.roles, COLLECTION_COLOURS["header"]
    wrap = {k: v for k, v in WRAP.items() if k in PARTS["section"]}
    top, bottom = COLLECTION_SPACE["header_with_nav" if with_nav else "header"]
    wrap.update({"horizontal_alignment_flex_direction_column": "center", "gap": 8, "section_width": "page-width",
                 "background_color": r[ground], "padding-block-start": top, "padding-block-end": bottom})
    title = _text_block("<h1>{{ closest.collection.title }}</h1>", "h3", "center", _on(r, ground), "normal", "var(--font-heading--family)")
    desc = _text_block("{{ closest.collection.description }}", "rte", "center", _on(r, ground), "narrow", "var(--font-body--family)")
    return {"type": "section", "blocks": {"title": title, "description": desc}, "block_order": ["title", "description"], "settings": wrap,
            "name": "Collection title"}


def products_section(direction, cat: Catalog) -> tuple[sections.Section, dict]:
    s = sections.Section("dtj_collection_products", LIST_APP, LIST_BLOCK, role="plain", kind="collection_products")
    s.settings.update(PRODUCT_LIST)
    if PAGE_COLLECTION:
        s.settings["collection"] = PAGE_COLLECTION
    top, bottom = COLLECTION_SPACE["products"]
    wrap = dict(WRAP)
    wrap.update({"padding-block-start": top, "padding-block-end": bottom, "background_color": direction.roles[COLLECTION_COLOURS["products"]]})
    return s, wrap


def nav_section(ctx: sections.Ctx):
    """A row of the store's own collections (their own pictures, names and links: DTJ Commerce circle-menu), the same list the home page's
    categories use (home-facts.json "categories"). 4 of the 8 measured collection pages have such a row above the grid."""
    c = ctx.facts.get("categories")
    items = (c or {}).get("items", [])
    if len(items) < 3:
        return sections.Omit("collection_nav", "needs 3 or more of the store's real collections in home-facts.json \"categories\"")
    r = ctx.direction.roles
    s = sections.Section("collection_nav", "dtj-commerce", "circle-menu", role="none", kind="collection_nav")
    s.settings.update(NAV)
    s.settings["collections"] = [it["collection"] for it in items[:8]]
    s.settings["variation"] = home_sections.CIRCLE_VERSION.get(niches.niche_of(ctx.brand["category"]), "square")
    top, bottom = COLLECTION_SPACE["nav"]
    s.settings.update({"padding_top": top, "padding_bottom": bottom, "background": r[COLLECTION_COLOURS["nav"]],
                       "text_color": _on(r, COLLECTION_COLOURS["nav"]), "frame_color": r["border"]})
    if s.settings["variation"] == "ring":  # the story rings in the brand's own colours (not the block's orange-pink-purple default)
        s.settings.update({"ring_color_1": r.get("accent_fill") or r["accent"], "ring_color_2": r.get("mark") or r["accent"]})
    for i, it in enumerate(items[:8], 1):
        ctx.prov[(s.id, f"collection_{i}")] = {"kind": "fact", "source": it["source"]}
    return s


def trust_section(ctx: sections.Ctx, page: dict):
    pts = page.get("store_points") or []
    if len(pts) < 3:
        return sections.Omit("collection_trust", "needs 3 to 6 STORE-WIDE points in collection-page.json (shipping, payment, returns), each with "
                                                 "its source; product claims do not belong on every collection")
    for p in pts:
        if not (isinstance(p, dict) and str(p.get("text", "")).strip() and str(p.get("source", "")).strip()):
            raise InputError("collection-page.json store_points: every point needs text and source")
    s = sections.Section("collection_trust", "dtj-commerce", "marquee-band", role="none", kind="trust_band_home")
    s.settings["variation"] = "line"
    return home_sections._strip(ctx, s, pts[:6])


def _wrapped(sec: sections.Section, cat: Catalog, wrap: dict, problems: list[str] | None = None) -> dict:
    try:
        entry = _block_entry(sec, cat)
    except KeyError as exc:  # an app released but never placed in a theme: its address is unknown, so the page can be looked at, not written
        if problems is None:
            raise
        entry = {"type": f"shopify://apps/{sec.app}/blocks/dtj-{sec.block}/pending", "settings": dict(sec.settings)}
        problems.append(f"PENDING ADDRESS {exc.args[0]}")
    return {"type": "_blocks", "blocks": {_key(sec): entry}, "block_order": [_key(sec)], "settings": wrap}


def build_collection(brand: dict, facts: dict, page: dict | None = None, *, chosen: tuple[str, ...] = DEFAULT, catalog: Catalog | None = None,
                     logo_path: Path | None = None) -> Result:
    _validate(brand, "brand-profile")
    _validate(facts, "home-facts")
    page = page or {}
    unknown = [c for c in chosen if c not in OPTIONS]
    if unknown:
        raise InputError(f"unknown collection page section(s) {unknown}; pick from: {', '.join(OPTIONS)}")
    if "products" not in chosen:
        raise InputError("a collection page needs its products: keep 'products' in the sections")
    cat = catalog or Catalog()
    direction = direction_mod.derive(brand, logo_path)
    ctx = sections.Ctx(brand, facts, direction, cat)
    template: dict = {"sections": {}, "order": []}
    built, omitted, problems = [], [], []

    nav = nav_section(ctx) if "nav" in chosen else None
    if isinstance(nav, sections.Omit):
        omitted.append({"section": nav.kind, "reason": nav.reason})
        nav = None
    if "header" in chosen:
        head = header_section(direction, with_nav=nav is not None)
        problems += check_theme_settings("section", head["settings"])
        for b in head["blocks"].values():
            problems += check_theme_settings("text", b["settings"])
        template["sections"]["dtj_collection_header"] = head
        template["order"].append("dtj_collection_header")
        ctx.prov[("dtj_collection_header", "title")] = {"kind": "structure", "source": "the collection's own title (Shopify admin)"}
        ctx.prov[("dtj_collection_header", "description")] = {"kind": "structure", "source": "the collection's own description (Shopify admin)"}

    if nav is not None:
        problems += cat.validate(nav.app, nav.block, nav.settings)
        template["sections"][nav.id] = _wrapped(nav, cat, dict(WRAP), problems)
        template["order"].append(nav.id)
        built.append(nav)

    prod, wrap = products_section(direction, cat)
    problems += cat.validate(prod.app, prod.block, {k: v for k, v in prod.settings.items() if k != "collection"})
    problems += check_theme_settings("_blocks", wrap)
    template["sections"][prod.id] = _wrapped(prod, cat, wrap, problems)
    template["order"].append(prod.id)
    built.append(prod)

    extra = []
    if "trust" in chosen:
        extra.append(trust_section(ctx, page))
    if "faq" in chosen:
        extra.append(sections.faq(ctx))
    rhythm_kinds = [x.kind for x in extra if not isinstance(x, sections.Omit)]
    for sec in extra:
        if isinstance(sec, sections.Omit):
            omitted.append({"section": sec.kind, "reason": sec.reason})
            continue
        role = "none" if sec.kind == "trust_band_home" else "plain"
        styling.apply(sec, role, direction, cat)
        styling.apply_home_type(sec, cat)
        w = dict(WRAP)
        if sec.kind != "trust_band_home":
            for key in ("padding_top", "padding_bottom"):
                if cat.has(sec.app, sec.block, key):
                    sec.settings[key] = 0
            step = styling.HOME_SPACE["section"]
            w.update({"padding-block-start": step if rhythm_kinds and sec.kind != rhythm_kinds[0] else 0, "padding-block-end": step,
                      "background_color": sec.settings.get("background") or ""})
        problems += cat.validate(sec.app, sec.block, sec.settings)
        template["sections"][sec.id] = _wrapped(sec, cat, w)
        template["order"].append(sec.id)
        built.append(sec)

    samples = sorted(f"{sid}.{key}" for (sid, key), v in ctx.prov.items() if v["kind"] == "sample")
    report = {
        "page": "collection", "file": COLLECTION_FILE, "category": brand["category"], "direction": direction.as_report(),
        "targets": COLLECTION_TARGETS, "space": {k: {"top": v[0], "bottom": v[1]} for k, v in COLLECTION_SPACE.items()},
        "chosen": [c for c in OPTIONS if c in chosen],
        "sections_built": [{"id": "dtj_collection_header", "block": "theme/section + text", "kind": "collection_header"}] * ("header" in chosen)
                          + [{"id": s.id, "block": f"{s.app}/{s.block}", "kind": s.kind} for s in built],
        "page_order": list(template["order"]),
        "sections_omitted": omitted,
        "samples": samples,
        "needs_replacement": samples,
        "provenance": {f"{sid}.{key}": {"kind": v["kind"], "source": v["source"]} for (sid, key), v in ctx.prov.items()},
        "problems": problems,
        "pending_address": any(p.startswith("PENDING ADDRESS") for p in problems),
        "lint": [],
    }
    return Result(template, report, None)


def merge(current: dict, page: dict) -> tuple[dict, list[dict]]:
    """The designed page into the collection template as it is now: our sections replace their old copies where they stand (or go first, in
    page order), the theme's own product grid and any other product list are switched OFF (kept in the file, so undo = switch them on),
    every other section is kept exactly as it is."""
    out = copy.deepcopy(current)
    out.setdefault("sections", {})
    out.setdefault("order", [])
    changes = []
    ours = page["order"]
    for sid in ours:
        if sid in out["sections"]:
            out["sections"][sid] = copy.deepcopy(page["sections"][sid])
            changes.append({"section": sid, "change": "replaced"})
    new = [sid for sid in ours if sid not in out["order"]]
    first = next((i for i, sid in enumerate(out["order"]) if sid in ours), None)
    pos = first if first is not None else 0
    for sid in new:  # new sections go together, in page order, where ours already are (or at the top of the page)
        idx = ours.index(sid)
        before = next((s for s in reversed(ours[:idx]) if s in out["order"]), None)
        at = out["order"].index(before) + 1 if before else pos
        out["order"].insert(at, sid)
        out["sections"][sid] = copy.deepcopy(page["sections"][sid])
        changes.append({"section": sid, "change": "added"})
    for sid in out["order"]:
        if sid in ours:
            continue
        sec = out["sections"][sid]
        is_grid = sec.get("type") in GRID_TYPES or any(  # also a DTJ Product List placed by hand (e.g. the one placed to learn the app's address)
            f"/blocks/dtj-{LIST_BLOCK}/" in str(b.get("type", "")) for b in (sec.get("blocks") or {}).values())
        is_old_title = "dtj_collection_header" in ours and sec.get("type") == "section" and \
            any("closest.collection.title" in json.dumps(b) for b in sec.get("blocks", {}).values())
        if (is_grid or is_old_title) and not sec.get("disabled"):
            sec["disabled"] = True
            why = "the old title (ours replaces it)" if not is_grid else ("the theme's own product grid" if sec.get("type") in GRID_TYPES
                                                                            else "another DTJ Product List (ours replaces it)")
            changes.append({"section": sid, "change": "switched off", "why": why})
    return out, changes
