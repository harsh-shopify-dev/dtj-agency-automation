"""The cross-brand comparison of the home page study and the per-category target ranges, from code only (CLAUDE.md rule 4).

    python .claude/skills/dtj-home-page/scripts/study_compare.py --numbers <numbers.json from study_numbers.py>
        --ratings .work/home-page-reference/ratings.md --notes .claude/skills/dtj-home-page/references/study
        --md .claude/skills/dtj-home-page/references/study-comparison.md --profiles services/store-builder/page_builder/home_profiles.json

Groups by Harsh's rating (ratings.md, his judgement, not conversion data): TOP = 85 and up, MIDDLE = 75-84, LOW = 74 and under. A page measured
from one section only (its spacing files hold a single block) is left out of every spacing figure. Section order comes from the `order:` line
of each brand note (read from the screenshots by a person or an agent); a brand without a note has no order figure.

How the targets are set (written here so nobody has to guess):
- spacing (every profile): the TOP group's range of page medians, laptop and phone; the floor for one section = the 10th percentile of all
  single gaps on the TOP pages;
- per category: [min, max] of the category's pages rated 75 and up (none: the TOP group), with `n` and the brands named; the default
  profile is the TOP group;
- the order rule: shop_within = the latest first-shop place under the hero on a TOP page, plus one; first_proof_by = the latest first-proof
  place on a TOP page as a share of its length, rounded up to 0.05; faq_within_last = how far from the end a TOP page puts its FAQ (1 =
  last); story_after_shop = true when no page in the study tells its story before a way to shop.
- colour shares are APPROXIMATE: the band reader misreads photos on flat backdrops, gradients, pop-up shades and some footers (MISREADS
  below, found by reading the screenshots for the brand notes). Each brand's palette decides its colours (Harsh, 19 Oct 2026); the shares
  are guidance, never a target a page must hit."""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics as st
from pathlib import Path

CATEGORY = {  # brand -> profile (the study folder's own categories, with the round-two brands placed by what they sell)
    "blueland": "home-care", "branch-basics": "home-care", "grove": "home-care", "method": "home-care", "cooking-guild": "home-care",
    "boom-beauty": "beauty", "jones-road": "beauty", "mamaearth": "beauty", "minimalist": "beauty", "glossier": "beauty", "sugar-cosmetics": "beauty",
    "ag1": "supplements", "ritual": "supplements", "gfuel": "supplements",
    "carnivore-snax": "food", "whole-truth": "food",
    "grubbly-farms": "pets", "kittyspout": "pets",
    "dr-squatch": "personal-care", "allbirds": "fashion", "sullen": "fashion", "gymreapers": "fitness", "boat": "electronics",
}
PROFILE_FOR = {"home-care": "home care, cleaning, laundry, hygiene, kitchen", "beauty": "skincare, cosmetics, hair care, personal care",
               "supplements": "supplements, wellness, nutrition powders", "food": "snacks, food, beverages", "pets": "pet food and pet care",
               "default": "any other category: the pages rated 85 and up across the study (fewer measuring artefacts than the 75+ set)"}
SHOP = {"categories", "best-sellers", "bundle"}
PROOF = {"press", "reviews", "ugc", "proof-numbers"}


MISREADS = {  # seen in the screenshots while writing the brand notes (19 Oct 2026); these brands' colour shares are off by what is named
    "ag1": "the tint band #EDEBE4 is product cards, not a band",
    "blueland": "the closing sky photo is folded into the last white band",
    "branch-basics": "the first white band swallows the hero photo, the press strip and the product row; the cream ground #FDFAF4 reads as white",
    "boat": "the footer (from 4613 px) is not found: the real content is one white band",
    "carnivore-snax": "the band edges are shifted (the cream band runs into the dark section)",
    "cooking-guild": "the last dark band (873 px) is the footer; the dark hero photo reads as a flat dark band",
    "dr-squatch": "a pop-up's shade covers the first screen: the hero reads as dark and one solid band is the cream ground under the shade",
    "glossier": "the header cut clips the blue hero; grey product tiles read as off-white; the pink footer counts as content",
    "grove": "the last solid band (1096 px) is the footer: the page itself has 2 navy bands",
    "gymreapers": "its three full-width photos read as colour bands: the dark and solid shares are photos",
    "jones-road": "the hero and the second banner are photos on flat grey backdrops, read as tint",
    "kittyspout": "the closing photo's grey wall reads as tint",
    "mamaearth": "no footer found: the footer and 3,863 px of SEO text count as content",
    "method": "its 3 horizontal gradient bands are not detected; the reviews gradient reads as solid (its left edge's colour)",
    "minimalist": "every section is inset: the page reads as one white band, the colour lives in tiles and cards",
    "ritual": "no colour band at all: the yellow sits inside cards, photos and a glow that stop short of the side margins",
    "sugar-cosmetics": "the hero video's wall reads as tint, the violet-pink gradient as one solid band, an offer slide caught mid-fade as dark",
    "sullen": "one dark band is the black middle of a background photo",
}
WHY_DIFFERENT = {"kittyspout": "its review widget reports impossible gaps (-5113, -3642, -5501, -3330 px), which study_numbers.py leaves "
                               "out; the ratings figure included them"}


def ratings(path: Path) -> dict[str, tuple[int, str]]:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^|]*?)\s*\|", line)
        if m:
            out[re.sub(r"[^a-z0-9]", "", m.group(1).lower())] = (int(m.group(4)), m.group(3))
    return out


def orders(notes: Path) -> dict[str, list[str]]:
    out = {}
    for f in sorted(notes.glob("*.md")):
        m = re.search(r"^`?order:\s*([^`\n]+)`?\s*$", f.read_text(encoding="utf-8"), re.M)
        if m:
            out[f.stem] = [w.strip() for w in m.group(1).split(",") if w.strip()]
    return out


def rng(vals):
    vals = [v for v in vals if v is not None]
    return [min(vals), max(vals)] if vals else None


def med(vals):
    vals = [v for v in vals if v is not None]
    return round(st.median(vals), 2) if vals else None


def pct(vals, p):
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return None
    k = (len(vals) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return round(vals[lo] + (vals[hi] - vals[lo]) * (k - lo))


def metrics(b: dict) -> dict:
    sh = b["bands"]["share"]
    one = b["sections_spacing"]["desktop"] <= 1
    return {"pad_desktop": None if one else b["pad_desktop"]["median"], "pad_phone": None if one else b["pad_phone"]["median"],
            "sections": None if one else b["sections_spacing"]["desktop"], "page_px_desktop": b["page_px"]["desktop"],
            "page_px_phone": b["page_px"]["phone"], "ground_share": round(sh["white"] + sh["offwhite"], 2), "tint_share": sh["tint"],
            "strong_share": round(sh["solid"] + sh["dark"], 2), "picture_share": sh["picture"],
            "strong_bands": b["bands"]["counts_150px"]["solid"] + b["bands"]["counts_150px"]["dark"],
            "h1_desktop": b["h1_px"]["desktop"], "h1_phone": b["h1_px"]["phone"],
            "h2_desktop": b["section_heading_px"]["desktop"]["median"], "h2_phone": b["section_heading_px"]["phone"]["median"],
            "button_radius": b["button"]["radius"], "one_section": one}


def order_stats(o: list[str]) -> dict:
    content = o[1:] if o and o[0] == "hero" else o
    shop = next((i for i, k in enumerate(content) if k in SHOP), None)
    proof = next((i for i, k in enumerate(o) if k in PROOF), None)
    return {"first_shop_under_hero": shop, "first_proof_share": round(proof / max(1, len(o) - 1), 2) if proof is not None else None,
            "story_before_shop": ("story" in content and shop is not None and content.index("story") < shop),
            "faq_last": (o[-1] == "faq") if "faq" in o else None, "faq_place": (o.index("faq") + 1, len(o)) if "faq" in o else None}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for a in ("--numbers", "--ratings", "--notes", "--md", "--profiles"):
        ap.add_argument(a, required=True)
    a = ap.parse_args(argv)
    nums = json.loads(Path(a.numbers).read_text(encoding="utf-8"))
    rat = ratings(Path(a.ratings))
    ords = orders(Path(a.notes))
    rows = {}
    for brand, b in nums.items():
        score, rated_pad = rat.get(re.sub(r"[^a-z0-9]", "", brand), (None, None))
        rows[brand] = {"rating": score, "ratings_pad": rated_pad, "category": CATEGORY.get(brand, "other"), **metrics(b),
                       "order": ords.get(brand), **(order_stats(ords[brand]) if brand in ords else {})}
    group = {"TOP": [k for k, r in rows.items() if (r["rating"] or 0) >= 85], "MIDDLE": [k for k, r in rows.items() if 75 <= (r["rating"] or 0) < 85],
             "LOW": [k for k, r in rows.items() if r["rating"] is not None and r["rating"] < 75]}
    top = [rows[k] for k in group["TOP"]]
    all_top_gaps = {"desktop": [], "phone": []}
    for k in group["TOP"]:
        for view in ("desktop", "phone"):
            key = "pad_by_section_desktop" if view == "desktop" else "pad_by_section_phone"
            for sec in nums[k][key]:
                if not sec[2]:
                    all_top_gaps[view] += [v for v in sec[:2] if v is not None]
    spacing = {"pad_desktop": rng([r["pad_desktop"] for r in top]), "pad_phone": rng([r["pad_phone"] for r in top]),
               "pad_floor_desktop": pct(all_top_gaps["desktop"], 0.10), "pad_floor_phone": pct(all_top_gaps["phone"], 0.10)}
    top_orders = [rows[k] for k in group["TOP"] if rows[k].get("order")]
    rule = {"_how": "from the order lines of the TOP pages (rated 85+) that have a note; see scripts/study_compare.py",
            "pages": [k for k in group["TOP"] if rows[k].get("order")],
            "shop_within": (max(r["first_shop_under_hero"] for r in top_orders if r["first_shop_under_hero"] is not None) + 1) if top_orders else 2,
            "first_proof_by": (math.ceil(max(r["first_proof_share"] for r in top_orders if r["first_proof_share"] is not None) * 20) / 20) if top_orders else 0.5,
            "proof_kinds": ["press_home", "video_reviews_home", "before_after_home"],
            "faq_within_last": max([r["faq_place"][1] - r["faq_place"][0] + 1 for r in top_orders if r.get("faq_place")] or [1]),
            "story_after_shop": not any(r.get("story_before_shop") for r in rows.values() if r.get("order"))}
    profiles = {}
    keys = ("sections", "page_px_desktop", "page_px_phone", "ground_share", "tint_share", "strong_share", "picture_share", "strong_bands",
            "h1_desktop", "h1_phone", "h2_desktop", "h2_phone")
    for prof in ("home-care", "beauty", "supplements", "food", "pets", "default"):
        refs = group["TOP"] if prof == "default" else [k for k, r in rows.items() if r["category"] == prof and (r["rating"] or 0) >= 75]
        basis = "the pages rated 85+ (all categories)" if prof == "default" else "pages rated 75+ in this category"
        if not refs:
            refs, basis = group["TOP"], "no page in this category is rated 75+: the TOP group"
        t = {**spacing}
        for key in keys:
            t[key] = rng([rows[k][key] for k in refs])
        profiles[prof] = {"for": PROFILE_FOR[prof], "basis": basis, "references": sorted(refs), "n": len(refs),
                          "confidence": "usable" if len(refs) >= 3 else "low: one or two references; lean on the default profile and the brand's own palette",
                          "targets": t,
                          "all_in_category": sorted(k for k, r in rows.items() if r["category"] == prof) if prof != "default" else None}
    out = {"_comment": ("Home page targets per category, made by .claude/skills/dtj-home-page/scripts/study_compare.py from 23 reference home pages "
                        "measured on 19 Oct 2026 (study_numbers.py). Ranges are inclusive [min, max]. Spacing = the pages Harsh rated 85+ "
                        "(the same for every category). Colour shares and band counts are what the good references DO, for guidance only: each "
                        "brand's own palette decides its colours (Harsh, 19 Oct 2026). Re-run the script after a new study; record verdicts in "
                        "the home skill's calibration log."),
           "metrics": {"pad_desktop / pad_phone": "median empty space between a section's edge and its first or last words or buttons (px), full-width photo sections left out, at 1440/1280 and 390 px",
                       "pad_floor_desktop / pad_floor_phone": "the smallest such gap one section may have: the 10th percentile of all single gaps on the 85+ pages",
                       "sections": "sections measured on the desktop page (strips under 80 px not counted)",
                       "page_px_desktop / page_px_phone": "page length in px",
                       "ground_share, tint_share, strong_share, picture_share": "share of the page between header and footer that is white or off-white, a light tint, a solid or dark band, a photo",
                       "strong_bands": "solid or dark bands of 150 px or more",
                       "h1_desktop / h1_phone": "the page's H1 size in px", "h2_desktop / h2_phone": "the median section heading size in px"},
           "order": rule, "profiles": profiles}
    Path(a.profiles).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    Path(a.md).write_text(markdown(rows, group, spacing, rule, profiles, nums), encoding="utf-8")
    print(json.dumps({"groups": group, "spacing": spacing, "order_rule": rule}, indent=1))
    return 0


def markdown(rows, group, spacing, rule, profiles, nums) -> str:
    def f(v):
        return "not measured" if v is None else (f"{v:.2f}" if isinstance(v, float) else str(v))

    L = ["# Home page study: comparison across brands (19 Oct 2026)",
         "Made by `scripts/study_compare.py` from `scripts/study_numbers.py` (the saved captures in the private study folder), Harsh's ratings in "
         "ratings.md (his judgement, not conversion data) and the `order:` lines of the brand notes in `study/`. TOP = rated 85+, MIDDLE = 75-84, "
         "LOW = 74 and under. Pad = the median empty space between a section's edge and its first or last words, full-width photo sections left out.", ""]
    L += ["## Every brand", "", "| Brand | Rating | Category | Pad desktop / phone | Sections | Page px desktop / phone | Ground / tint / strong / photo share | Strong bands | H1 / H2 desktop | H2 phone | Order (from the note) |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, r in sorted(rows.items(), key=lambda kv: -(kv[1]["rating"] or 0)):
        L.append(f"| {k} | {f(r['rating'])} | {r['category']} | {f(r['pad_desktop'])} / {f(r['pad_phone'])} | {f(r['sections'])} | "
                 f"{r['page_px_desktop']} / {f(r['page_px_phone'])} | {r['ground_share']:.2f} / {r['tint_share']:.2f} / {r['strong_share']:.2f} / {r['picture_share']:.2f} | "
                 f"{r['strong_bands']} | {f(r['h1_desktop'])} / {f(r['h2_desktop'])} | {f(r['h2_phone'])} | {', '.join(r['order']) if r.get('order') else 'no note yet'} |")
    L += ["", "## Ranges by group", "", "| Measure | TOP | MIDDLE | LOW |", "|---|---|---|---|"]
    for key in ("pad_desktop", "pad_phone", "sections", "page_px_desktop", "page_px_phone", "ground_share", "tint_share", "strong_share", "picture_share",
                "strong_bands", "h1_desktop", "h1_phone", "h2_desktop", "h2_phone"):
        cells = []
        for g in ("TOP", "MIDDLE", "LOW"):
            vals = [rows[k][key] for k in group[g]]
            r_, m_ = rng(vals), med(vals)
            cells.append(f"{r_[0]}-{r_[1]} (median {m_}, n {len([v for v in vals if v is not None])})" if r_ else "not measured")
        L.append(f"| {key} | " + " | ".join(cells) + " |")
    L += ["", f"Groups: TOP {', '.join(group['TOP'])}; MIDDLE {', '.join(group['MIDDLE'])}; LOW {', '.join(group['LOW'])}.",
          f"Spacing targets (TOP range): desktop {spacing['pad_desktop']}, phone {spacing['pad_phone']}; one section's floor (10th percentile of the TOP "
          f"pages' single gaps): desktop {spacing['pad_floor_desktop']}, phone {spacing['pad_floor_phone']}.", ""]
    L += ["## Section order", ""]
    with_order = [k for k in rows if rows[k].get("order")]
    L.append(f"Brands with a note: {len(with_order)} of {len(rows)}.")
    for k in sorted(with_order, key=lambda x: -(rows[x]["rating"] or 0)):
        r = rows[k]
        L.append(f"- {k} ({f(r['rating'])}): first way to shop {f(r['first_shop_under_hero'])} sections under the hero; first proof at "
                 f"{f(r['first_proof_share'])} of the page; story before the shop: {r['story_before_shop']}; FAQ: "
                 f"{'last' if r['faq_last'] else ('place ' + str(r['faq_place'][0]) + ' of ' + str(r['faq_place'][1]) if r['faq_place'] else 'none')}")
    L += ["", f"Order rule written to home_profiles.json (from {', '.join(rule['pages']) or 'no TOP page with a note yet'}): a way to shop within "
          f"{rule['shop_within']} sections under the hero; the first proof by {rule['first_proof_by']} of the page; the FAQ within the last "
          f"{rule['faq_within_last']} sections; the story after the first way to shop: {rule['story_after_shop']}.", ""]
    L += ["## Per-category profiles", "", "| Profile | References (rated 75+) | Confidence | Sections | Page px desktop | H2 desktop / phone | Ground share | Strong share |", "|---|---|---|---|---|---|---|---|"]
    for p, v in profiles.items():
        t = v["targets"]
        L.append(f"| {p} | {', '.join(v['references'])} (n {v['n']}) | {v['confidence'].split(':')[0]} | {t['sections']} | {t['page_px_desktop']} | {t['h2_desktop']} / {t['h2_phone']} | {t['ground_share']} | {t['strong_share']} |")
    L += ["", "## Colour shares: known misreads (seen in the screenshots)", "",
          "The shares above come from the band reader and are approximate. These pages were checked by eye while writing their notes:"]
    L += [f"- {k}: {v}" for k, v in sorted(MISREADS.items())]
    L += ["", "## Where the ratings file and the measurements disagree", ""]
    for k, r in sorted(rows.items()):
        rp = r["ratings_pad"] or ""
        m = re.match(r"\s*(\d+)\s*/\s*(\d+)", rp)
        if r["one_section"]:
            L.append(f"- {k}: ratings.md gives pad {rp.strip()}, but its spacing files hold ONE section (the page is not built from separate "
                     f"Shopify sections), so that figure is one measurement, not a page median.")
        elif m and (int(m.group(1)), int(m.group(2))) != (r["pad_desktop"], r["pad_phone"]):
            why = WHY_DIFFERENT.get(k, "not explained by the saved files")
            L.append(f"- {k}: ratings.md gives pad {rp.strip()}, the saved spacing files give {r['pad_desktop']} / {r['pad_phone']} ({why}).")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
