"""Home page SHOWCASE (Harsh, 13 Oct 2026: "add all the blocks yourself and also design the page").

Builds a templates/index.json for the test store's UNPUBLISHED theme out of our own app blocks, one full-width `_blocks` section per block, so each block keeps
its own background. It is a layout and look demo with clearly marked SAMPLE words: nothing in it is a claim, an offer, a price or a review (the product
cards read the store's own products; ratings in the theme editor are marked samples; shoppers see no rating without real reviews).

    python home_showcase.py --heroes-from <pulled templates/index.json> --commerce-uuid <uuid> --shop-uuid <uuid> --out <folder>/templates/index.json

The extension uuid of an app is the last part of a block reference (shopify://apps/<handle>/blocks/<block>/<uuid>) and only exists once a block of that
app has been placed in a theme. Every setting written here is checked against the block's manifest (id exists, select value is an option, range is in
bounds), so a typo fails here and not in the theme editor. Run from the repo root.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SERVICES = ROOT / "services"
APP_DIRS = {"dtj-commerce": "block-library-commerce", "dtj-shop": "block-library-shop", "dtj-heroes": "block-library-heroes"}
IMG = "shopify://shop_images/toiletcleaningfoampowder-toilova_{}.webp"  # pictures already on the test store (the TOILOVA sample set)
# NOTE: the test store has only ONE collection with visible products ("all"; "Home page" is empty), so the tabs of Best Sellers and the dropdown of
# Shop by Concern (one choice per collection) do not show here. With two or more real collections they appear.
TINT = "#f5f2fd"  # the soft purple behind Shop by Concern; the wave above it carries the same color

SECTION_SETTINGS = {
    "content_direction": "column", "vertical_on_mobile": True, "horizontal_alignment": "flex-start", "vertical_alignment": "center", "align_baseline": False,
    "horizontal_alignment_flex_direction_column": "flex-start", "vertical_alignment_flex_direction_column": "center", "gap": 0, "section_width": "full-width",
    "section_height": "", "section_height_custom": 50, "background_media": "none", "background_color": "", "video_position": "cover",
    "background_image_position": "cover", "toggle_overlay": False, "overlay_color": "#00000026", "overlay_style": "solid", "gradient_direction": "to top",
    "border": "none", "border_width": 1, "border_opacity": 100, "border_color": "", "border_radius": 0, "padding-block-start": 0, "padding-block-end": 0,
}


def pic(n: int) -> str:
    return IMG.format(n)


class Page:
    def __init__(self, uuids: dict[str, str]):
        self.uuids = uuids
        self.sections: dict[str, dict] = {}
        self.order: list[str] = []
        self._manifests: dict[tuple[str, str], dict] = {}

    def manifest(self, app: str, block: str) -> dict:
        key = (app, block)
        if key not in self._manifests:
            path = SERVICES / APP_DIRS[app] / "manifests" / f"{block}.json"
            self._manifests[key] = json.loads(path.read_text(encoding="utf-8"))
        return self._manifests[key]

    def check(self, app: str, block: str, settings: dict) -> None:
        """Fail on a typo: every setting must exist in the block's manifest, a select needs one of its options, a range must be inside its bounds."""
        by_id = {s["id"]: s for s in self.manifest(app, block)["settings"] if "id" in s}
        standard = {"padding_top", "padding_bottom", "padding_left", "padding_right", "margin_top", "margin_bottom", "side_padding", "text_color", "background"}
        for key, value in settings.items():
            if key in standard and key not in by_id:
                continue
            if key not in by_id:
                raise SystemExit(f"{app}/{block}: unknown setting {key!r}")
            s = by_id[key]
            if s["type"] == "select" and value not in [o["value"] for o in s["options"]]:
                raise SystemExit(f"{app}/{block}: {key}={value!r} is not one of {[o['value'] for o in s['options']]}")
            if s["type"] == "range" and not (s["min"] <= value <= s["max"]):
                raise SystemExit(f"{app}/{block}: {key}={value} is outside {s['min']}..{s['max']}")

    def add(self, name: str, app: str, block: str, **settings) -> None:
        self.check(app, block, settings)
        uuid = self.uuids[app]
        key = f"{app.replace('-', '_')}_{block.replace('-', '_')}_{name}"
        section = {"type": "_blocks", "blocks": {key: {"type": f"shopify://apps/{app}/blocks/dtj-{block}/{uuid}", "settings": settings}},
                   "block_order": [key], "settings": dict(SECTION_SETTINGS)}
        self.sections[name] = section
        self.order.append(name)

    def add_existing(self, name: str, section: dict) -> None:
        self.sections[name] = section
        self.order.append(name)

    def template(self) -> dict:
        return {"sections": self.sections, "order": self.order}


def build(heroes_template: dict, uuids: dict[str, str]) -> dict:
    heroes_section = heroes_template["sections"][heroes_template["order"][0]]
    by_kind = {}
    for key, block in heroes_section["blocks"].items():
        kind = re.search(r"/blocks/dtj-([a-z-]+)/", block["type"]).group(1)
        by_kind[kind] = (key, block)

    def hero_section(kind: str) -> dict:
        key, block = by_kind[kind]
        return {"type": "_blocks", "blocks": {key: block}, "block_order": [key], "settings": dict(SECTION_SETTINGS)}

    uuids = dict(uuids, **{"dtj-heroes": re.search(r"/blocks/dtj-[a-z-]+/([0-9a-f-]+)$", by_kind["hero-banner"][1]["type"]).group(1)})
    p = Page(uuids)
    p.add("strip_top", "dtj-commerce", "marquee-band", variation="bold", icon_1="e-gift", text_1="Sample message one", icon_2="e-bolt", text_2="Sample message two",
          icon_3="e-star", text_3="Sample message three", icon_4="e-party", text_4="Sample message four", speed=30, padding_top=0, padding_bottom=0)
    p.add_existing("hero", hero_section("hero-banner"))
    # stand-in "logos" are the store's own product pictures: nothing here says the brand was featured anywhere (test of the layout only)
    p.add("press", "dtj-commerce", "press-strip", heading="Sample heading: logo strip (stand-in pictures, not real press)", layout="row", logo_1=pic(1), name_1="Sample logo 1",
          logo_2=pic(2), name_2="Sample logo 2", logo_3=pic(3), name_3="Sample logo 3", logo_4=pic(5), name_4="Sample logo 4", logo_height=56, logo_tone="original", padding_top=24, padding_bottom=8)
    p.add("categories", "dtj-commerce", "circle-menu", variation="ring", heading="Sample heading: shop by category", image_1=pic(1), title_1="Sample category one",
          link_1="/collections/all", image_2=pic(2), title_2="Sample category two", link_2="/collections/all", image_3=pic(3), title_3="Sample category three",
          link_3="/collections/all", image_4=pic(5), title_4="Sample category four", link_4="/collections/all", padding_top=40, padding_bottom=24)
    p.add("category_grid", "dtj-commerce", "category-grid", heading="Sample heading: category grid", subheading="Sample line under the heading", layout="bento_left",
          image_1=pic(2), title_1="Sample tile one", button_1="Sample button", link_1="/collections/all", image_2=pic(3), title_2="Sample tile two", button_2="Sample button",
          link_2="/collections/all", image_3=pic(5), title_3="Sample tile three", button_3="Sample button", link_3="/collections/all", image_4=pic(1), title_4="Sample tile four", button_4="Sample button", link_4="/collections/all", image_5=pic(4), title_5="Sample tile five",
          button_5="Sample button", link_5="/collections/all", padding_top=24, padding_bottom=24)
    p.add("bestsellers", "dtj-commerce", "best-sellers", heading="Sample heading: our best sellers", collections=["all"], products_per_tab=8, card_style="soft", quick_add="button", button_shape="rounded", padding_top=24, padding_bottom=48)
    p.add("category_slider", "dtj-commerce", "category-slider", heading="Sample heading: category slider", subheading="Sample line under the heading", shape="slant",
          image_1=pic(1), title_1="Sample one", link_1="/collections/all", image_2=pic(2), title_2="Sample two", link_2="/collections/all", image_3=pic(3), title_3="Sample three",
          link_3="/collections/all", image_4=pic(5), title_4="Sample four", link_4="/collections/all", image_5=pic(4), title_5="Sample five", link_5="/collections/all",
          image_6=pic(2), title_6="Sample six", link_6="/collections/all", padding_top=24, padding_bottom=40)
    p.add_existing("why", hero_section("feature-tiles"))
    p.add("before_after", "dtj-shop", "before-after", variation="card", before_image=pic(2), after_image=pic(1), eyebrow_bold="Sample", eyebrow_rest="small line",
          heading="Sample heading to", heading_accent="show the accent words", body="<p>Sample paragraph. This is stand-in text so the layout can be checked; "
          "replace it with the <strong>real copy</strong> for the store.</p>", point_1_bold="Sample point one", point_1_rest="with its detail", point_2_bold="Sample point two",
          point_2_rest="with its detail", point_3_bold="Sample point three", point_3_rest="with its detail", button_label="Sample button", button_link="/collections/all")
    p.add("compare", "dtj-heroes", "compare-showcase", variation="spotlight", eyebrow="Sample small line", heading="Sample heading for the comparison",
          text="Sample paragraph. Stand-in words so the layout can be checked; the ticks and crosses below are placeholders, not claims about any product.",
          points="Sample point one\nSample point two\nSample point three", button_label="Sample button", button_url="/collections/all", us_title="Sample brand",
          us_sub="sample line", them_title="Others (sample)", r1_label="Sample row one", r2_label="Sample row two", r3_label="Sample row three", r4_label="Sample row four",
          r5_label="Sample row five", image=pic(3))
    p.add_existing("cards", hero_section("feature-cards"))
    p.add("wave", "dtj-commerce", "wave-divider", wave_color=TINT, style="layered", layers=3, wave_height=120, wave_height_mobile=70)
    p.add("concern", "dtj-shop", "concern-slider", heading="Sample heading", heading_accent="second line", subtext="Sample line under the heading",
          collections=["all"], background=TINT, accent_color="#7c5cf0", padding_top=24,
          padding_bottom=56)
    p.add_existing("reviews", hero_section("video-reviews"))
    p.add("strip_bottom", "dtj-commerce", "marquee-band", variation="dark", icon_1="check", text_1="Sample message one", icon_2="shield", text_2="Sample message two",
          icon_3="truck", text_3="Sample message three", speed=40)
    return p.template()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--heroes-from", required=True, help="a pulled templates/index.json that already holds the DTJ Heroes sample blocks")
    ap.add_argument("--commerce-uuid", required=True)
    ap.add_argument("--shop-uuid", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    raw = Path(args.heroes_from).read_text(encoding="utf-8")
    heroes = json.loads(re.sub(r"^/\*.*?\*/", "", raw, flags=re.S))
    template = build(heroes, {"dtj-commerce": args.commerce_uuid, "dtj-shop": args.shop_uuid})
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(template, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", out, "with", len(template["order"]), "sections")


if __name__ == "__main__":
    main()
