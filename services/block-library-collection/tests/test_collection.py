"""Tests for DTJ Product List (the replica of Proeffex's product list section). The generic ones (licence, escaping, defaults, standard controls,
no hand-edited generated files) live in services/block-library/tests/test_generated_blocks.py and run against this app with DTJ_APP_ROOT set.

    cd services/block-library-collection
    DTJ_APP_ROOT=$PWD ../../.work/.venv/Scripts/python -m unittest discover -s tests -t .
"""
import copy
import json
import os
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
os.environ["DTJ_APP_ROOT"] = str(HERE)  # must be set before the shared helpers are imported
sys.path.insert(0, str(HERE.parent / "block-library" / "tests"))
import test_generated_blocks as tg  # noqa: E402

render = tg.render
from test_generated_blocks import EveryBlockTests, GeneratedFilesTests  # noqa: E402,F401

MANIFEST = json.loads((HERE / "manifests" / "product-list.json").read_text(encoding="utf-8"))
ASSETS = HERE / "extensions" / "dtj-collection" / "assets"
SAMPLE = MANIFEST["test"]["sample"]


def render_on_page(page_collection, page_type="collection", **extra):
    """The block as Shopify renders it on a page: request.page_type and the page's own `collection` object are there."""
    env = tg.Environment(loader=tg.DictLoader({s.stem: s.read_text(encoding="utf-8") for s in tg.SNIPPETS.glob("*.liquid")}))
    env.add_filter("image_url", lambda value, **kw: f"//img.example/{value}")
    env.add_filter("money", lambda value: f"Rs. {value}")
    template = env.from_string(tg.cl.strip_schema(tg.block_text(MANIFEST)),
                               globals={"request": {"design_mode": False, "page_type": page_type}, "collection": page_collection})
    block = {"id": "b1", "settings": {**tg.defaults(MANIFEST), **settings(**extra)}, "shopify_attributes": ""}
    return re.sub(r"<!--.*?-->", "", template.render(app={"metafields": {"dtj": {"licence": {"value": "active"}}}}, block=block), flags=re.S).strip()


def settings(**extra):
    s = copy.deepcopy(SAMPLE)
    s.update(extra)
    return s


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class ProductListTests(unittest.TestCase):
    m = MANIFEST

    def r(self, design_mode=False, **extra):
        return render(self.m, settings(**extra), design_mode=design_mode)

    def test_it_ships_empty_and_the_editor_says_so(self):
        self.assertEqual(render(self.m, {}), "")
        self.assertIn("DTJ Product List: pick a collection", render(self.m, {}, design_mode=True))

    def test_it_has_every_setting_of_the_original_with_the_same_ids_and_defaults(self):
        # the 34 settings of proeffex-producttab-collection.liquid (color_scheme becomes the standard Text / Background colours)
        original = {"collection": None, "layout_type": "grid", "carousel_on_mobile": False, "max_products": 4, "columns": 4, "mobile_columns": "2", "columns_gap": 8,
                    "rows_gap": 8, "icons_style": "arrow", "icons_shape": "none", "section_width": "page-width", "horizontal_alignment": "flex-start", "gap": 12,
                    "padding-block-start": 0, "padding-block-end": 0, "pf_mobile_layout": "default", "pf_compact_cards": True, "pf_compact_rating": True,
                    "pf_card_frame": True, "pf_card_padding": 8, "pf_show_tag_badges": True, "pf_hide_sale_badge": True, "pf_offer_text": True,
                    "pf_image_ratio": "1 / 1", "pf_image_fit": "contain", "pf_title_lines": 2, "pf_button_height": 34, "pf_swatch_size": 22,
                    "pf_swatch_gap": 8, "pf_swatch_align": "left", "pf_swatch_show_all": True}
        by_id = {s["id"]: s for s in MANIFEST["settings"] if "id" in s}
        for key, default in original.items():
            self.assertIn(key, by_id, key)
            if default is not None:
                self.assertEqual(by_id[key]["default"], default, key)
        for key in ("pf_compare_color", "pf_review_color"):
            self.assertEqual(by_id[key]["type"], "color")
        # 1-16 in the original; 50 since 20 Oct 2026 so the block can fill a whole collection page (Shopify gives one page up to 50 products)
        self.assertEqual((by_id["max_products"]["min"], by_id["max_products"]["max"]), (1, 50))
        self.assertEqual((by_id["pf_button_height"]["min"], by_id["pf_button_height"]["max"], by_id["pf_button_height"]["step"]), (28, 52, 2))
        self.assertEqual([o["value"] for o in by_id["pf_image_ratio"]["options"]], ["1 / 1", "4 / 5", "3 / 4", "4 / 3"])

    def test_the_card_is_the_proeffex_compact_card(self):
        html = self.r()
        for part in ("pl-card__frame", "pl-gallery", "pl-rating", "pl-title", "pl-price", "pl-swatches", "pl-buy", "pl-add"):
            self.assertIn(part, html)
        self.assertIn("4.5", html)
        self.assertIn("252 reviews", html)  # one star, the rating and the review count
        self.assertEqual(html.count('class="pl-star pl-star--on"'), 1)
        self.assertEqual(html.count('class="pl-swatch-item"'), 3)  # every shade
        self.assertIn("Add to cart", html)

    def test_the_offer_text_is_x_percent_off_or_save_x_percent(self):
        self.assertIn("25% OFF", self.r())
        self.assertIn("SAVE 25%", self.r(pf_offer_text=False))

    def test_badges_come_from_whole_product_tags_only(self):
        # Harsh, 20 Oct 2026: "whatever added in tags of product it should apply it there": the product's own tags, whole tags (the original matched
        # any tag CONTAINING "new", so "renewal" or "new-deal" showed "New Launches": a false claim on a client store)
        html = self.r()
        self.assertEqual(html.count("pl-badge--best"), 1)  # the sale product carries best-seller (and new: best-seller wins)
        self.assertNotIn("pl-badge--new", html)  # "renewal" is not "new"
        self.assertIn("Best Seller", html)
        for tags, expected in ((["New"], "pl-badge--new"), (["new-deal"], None), (["Best-Seller"], "pl-badge--best"), ([" new "], "pl-badge--new")):
            s = settings()
            s["collection"]["products"][0]["tags"] = tags
            s["collection"]["products"][1]["tags"] = []
            out = render(self.m, s)
            if expected:
                self.assertIn(expected, out, tags)
            else:
                self.assertNotIn("pl-badge", out, tags)
        self.assertNotIn("pl-badge", self.r(pf_show_tag_badges=False))

    def test_sample_badges_show_only_inside_the_theme_editor(self):
        s = settings(pf_badge_source="sample")
        for p in s["collection"]["products"]:
            p["tags"] = []
        self.assertNotIn("pl-badge", render(self.m, s))  # shoppers never see a badge the product's data does not carry
        self.assertIn("pl-badge", render(self.m, s, design_mode=True))

    def test_the_heading_is_the_collection_title_unless_typed_and_view_all_is_optional(self):
        self.assertIn(">Concealers</h4>", self.r())
        self.assertIn(">Iconic Cover Concealer</h4>", self.r(heading=""))
        self.assertIn('href="/collections/iconic"', self.r())
        self.assertNotIn("pl__viewall", self.r(show_view_all=False))
        self.assertIn(">See all</a>", self.r(view_all_label="See all"))

    def test_the_layouts_and_phone_variants(self):
        self.assertIn("pl-list--grid", self.r())
        self.assertIn("data-pl-carousel", self.r(layout_type="carousel"))
        self.assertIn("pl-editorial__item-0", self.r(layout_type="editorial"))
        self.assertIn("pl-list--mobile-carousel", self.r(carousel_on_mobile=True))
        grid2 = self.r(pf_mobile_layout="grid2")
        self.assertIn("pl-list--mobile-grid2", grid2)
        self.assertIn("pl-list--hide-mobile", grid2)
        self.assertNotIn("pl-list--mobile-carousel", self.r(pf_mobile_layout="grid2", carousel_on_mobile=True))  # grid2 wins, as in the original

    def test_padding_and_gap_scale_down_on_phones_like_horizon(self):
        html = self.r(**{"padding-block-start": 13, "padding-block-end": 48, "gap": 28})
        self.assertIn("--pl-pt: 13px;", html)  # 20 px or less stays as typed
        self.assertIn("--pl-pb: max(20px, calc(var(--pl-scale) * 48px));", html)
        self.assertIn("--pl-gap-eff: max(24px, calc(var(--pl-scale) * 28px));", html)

    def test_text_is_escaped_and_no_rating_is_shown_without_review_data(self):
        html = render(self.m, settings(heading="<b>x</b>"))
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", html)
        self.assertEqual(html.count("pl-rating__count"), 1)  # only the product that has review metafields: nothing is ever invented

    def test_on_a_collection_page_an_empty_collection_setting_means_that_pages_collection(self):
        page = copy.deepcopy(SAMPLE["collection"])
        page["title"] = "Page collection"
        html = render_on_page(page, collection=None, heading="")
        self.assertIn(">Page collection</h4>", html)
        self.assertEqual(html.count('class="pl-card"'), len(page["products"]))
        self.assertEqual(render_on_page(page, page_type="product", collection=None), "")  # anywhere else it still needs a picked collection
        self.assertNotIn("Page collection", render_on_page(page, heading=""))  # a picked collection always wins
        by_id = {s["id"]: s for s in MANIFEST["settings"] if "id" in s}
        self.assertNotIn("autofill", by_id["collection"])  # Shopify refused it on a collection setting (20 Oct 2026); the empty setting does the job

    def test_a_placeholder_rating_with_zero_reviews_is_never_shown(self):
        # elevate-with-harsh (20 Oct 2026): many products hold rating 1.0 with rating_count 0 (no reviews behind it); the original would show "1.0 | 0 reviews"
        s = settings()
        s["collection"]["products"][0]["metafields"]["reviews"]["rating_count"] = 0
        self.assertNotIn("pl-rating", render(self.m, s))
        s["pf_hide_no_reviews"] = False
        self.assertIn("0 reviews", render(self.m, s))  # the exact original, when someone asks for it
        self.assertIn("252 reviews", self.r())

    def test_the_collection_page_row_has_the_count_and_sort_and_the_heading_can_go(self):
        page = copy.deepcopy(SAMPLE["collection"])
        page.update(products_count=17, sort_by="price-ascending", default_sort_by="manual",
                    sort_options=[{"value": "manual", "name": "Featured"}, {"value": "price-ascending", "name": "Price, low to high"}])
        html = render_on_page(page, collection=None, show_sort=True, show_heading=False)
        self.assertNotIn("pl__heading", html)
        self.assertIn(">17 products</p>", html)
        self.assertIn('<option value="price-ascending" selected>Price, low to high</option>', html)
        self.assertIn('name="sort_by"', html)
        self.assertNotIn("pl-tools", self.r())  # off unless asked: the replica is unchanged
        page["sort_options"] = []
        self.assertNotIn("<select", render_on_page(page, collection=None, show_sort=True))  # no sort options, no empty menu
        page["products_count"] = 1
        self.assertIn(">1 product</p>", render_on_page(page, collection=None, show_sort=True))

    def test_the_script_is_small_and_has_no_confetti_remover(self):
        js = (ASSETS / "dtj-product-list.js").read_text(encoding="utf-8")
        self.assertLess(len(js.encode("utf-8")), 10000)
        self.assertNotIn("confetti", js)
        self.assertNotIn("innerHTML", js)
        self.assertIn("form.submit()", js)  # a failed request falls back to the normal form post
        self.assertIn("CartLinesUpdateEvent", js)  # the add tells the theme through Shopify's standard cart event (its icon and drawer update without a reload)

    def test_the_css_carries_the_measured_numbers_of_the_original(self):
        css = (ASSETS / "dtj-product-list.css").read_text(encoding="utf-8")
        for part in ("border: 1px solid var(--pl-frame)", "border-radius: 6px", "padding: var(--pl-card-pad, 8px) var(--pl-card-pad, 8px) calc(var(--pl-card-pad, 8px) + 7px)",
                     "margin-bottom: 14px", "margin: 11px 0 0", "--pl-btn-bg: rgb(36 36 36)", "--f-title: 12px", "--f-title: 13px", "--f-title: 14px",
                     "--f-price: 15px", "padding: 8.3px 4.3px 4.3px 5.05px", "width: 60px", "height: 44px"):
            self.assertIn(part, css)


if __name__ == "__main__":
    unittest.main()
