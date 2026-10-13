"""Tests for the blocks of DTJ Shop (the generic ones, licence / escaping / defaults, live in services/block-library/tests/test_generated_blocks.py
and run against this app with DTJ_APP_ROOT set).

    cd services/block-library-shop
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

MANIFEST = json.loads((HERE / "manifests" / "concern-slider.json").read_text(encoding="utf-8"))
ASSETS = HERE / "extensions" / "dtj-shop" / "assets"
SAMPLE = MANIFEST["test"]["sample"]


def product(**extra):
    base = {"id": 7, "handle": "serum", "title": "Purple serum", "url": "/products/serum", "price": 88700, "compare_at_price": 109800,
            "featured_image": {"src": "pic", "width": 600, "height": 600}, "images": [], "tags": [], "available": True, "has_only_default_variant": False,
            "description": "<p>A <b>gentle</b> daily routine.</p>", "options": ["Pack"], "metafields": {"judgeme": {"badge": ""}},
            "variants": [{"id": 1, "title": "Pack of 2", "price": 88700, "compare_at_price": 109800, "available": True, "option1": "Pack of 2", "featured_image": {"src": "v1"}},
                         {"id": 2, "title": "Pack of 4", "price": 150000, "compare_at_price": 0, "available": False, "option1": "Pack of 4", "featured_image": None}]}
    base.update(extra)
    base["selected_or_first_available_variant"] = base["variants"][0]
    return base


def settings(**extra):
    s = {**SAMPLE, **extra}
    return s


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class ConcernSliderTests(unittest.TestCase):
    m = MANIFEST

    def r(self, products=None, design_mode=False, **extra):
        s = copy.deepcopy(settings(**extra))
        if products is not None:
            s["collections"] = [{"title": "Yellow", "url": "/collections/yellow", "products": products}]
        return render(self.m, s, design_mode=design_mode)

    def test_it_ships_empty_and_the_editor_says_so(self):
        self.assertEqual(render(self.m, {}), "")
        self.assertIn("DTJ Shop by Concern is empty", render(self.m, {}, design_mode=True))

    def test_two_collections_give_a_dropdown_with_one_panel_each_and_the_first_shows(self):
        html = self.r()
        self.assertEqual(html.count('class="dtj-cs__panel"'), 2)
        self.assertEqual(len(re.findall(r'<option value="\d+"(?: selected)?>', html)), 2)
        self.assertIn(">Yellow Teeth</option>", html)  # a words override
        self.assertIn(">Coll two</option>", html)  # else the collection's own title
        self.assertRegex(html, r'class="dtj-cs__panel" data-total="\d+" hidden')
        self.assertEqual(len(re.findall(r'class="dtj-cs__panel" data-total="\d+">', html)), 1)
        self.assertIn('data-total="4"', html)

    def test_one_collection_has_no_dropdown(self):
        html = self.r(products=[product()])
        self.assertNotIn("dtj-cs__concern", html)
        self.assertIn("dtj-cs--one", html)

    def test_the_heading_has_two_lines_and_the_second_takes_the_accent(self):
        html = self.r()
        self.assertIn('<span class="dtj-cs__line">Shop by</span>', html)
        self.assertIn('dtj-cs__line dtj-cs__accent">Concern', html)
        self.assertIn("<h2", html)
        self.assertIn("<h3", self.r(heading_tag="h3"))
        self.assertNotIn("dtj-cs__heading", self.r(heading="", heading_accent=""))

    def test_the_card_shows_price_old_price_and_the_percent_off_pill(self):
        html = self.r(products=[product()])
        self.assertIn("88700", html)  # the test engine prints money as Rs. + cents
        self.assertIn("109800", html)
        self.assertIn(">19% OFF<", html)
        self.assertIn("20% OFF", self.r(products=[product(variants=[{"id": 1, "title": "x", "price": 80000, "compare_at_price": 100000, "available": True, "option1": "x", "featured_image": None}])], off_label="OFF"))
        no_sale = self.r(products=[product(price=5000, compare_at_price=0, variants=[{"id": 1, "title": "x", "price": 5000, "compare_at_price": 0, "available": True, "option1": "x", "featured_image": None}])])
        self.assertIn('class="dtj-cs__off" hidden>', no_sale)
        self.assertNotIn("% OFF<", no_sale.replace('hidden></span>', ''))
        self.assertNotIn("dtj-cs__old", self.r(products=[product()], show_compare_price=False))
        self.assertNotIn("dtj-cs__off", self.r(products=[product()], show_discount=False))
        self.assertIn(">19% Off<", self.r(products=[product()], off_label="Off"))

    def test_the_option_dropdown_is_the_form_field_so_it_works_without_a_script(self):
        html = self.r(products=[product()])
        self.assertIn('<select class="dtj-cs__var" name="id"', html)
        self.assertIn('<option value="1" selected', html)
        self.assertIn('data-available="false"', html)
        self.assertIn("(Sold out)", html)
        self.assertIn('data-price="', html)
        self.assertRegex(html, r'data-img="[^"]*v1')
        single = self.r(products=[product(has_only_default_variant=True)])
        self.assertNotIn("dtj-cs__var", single)
        self.assertIn('<input type="hidden" name="id" value="1">', single)
        self.assertNotIn("dtj-cs__var", self.r(products=[product()], show_variants=False))

    def test_a_sold_out_first_variant_disables_the_button(self):
        sold = product(variants=[{"id": 9, "title": "Only", "price": 100, "compare_at_price": 0, "available": False, "option1": "Only", "featured_image": None}], available=False)
        html = self.r(products=[sold])
        self.assertRegex(html, r'<button type="submit" class="dtj-cs__add" disabled><span class="dtj-cs__add-label">Sold out</span>')

    def test_the_rating_comes_from_judgeme_then_nothing_and_samples_only_in_the_editor(self):
        jm = "<div class='jdgm-prev-badge' data-average-rating='4.77' data-number-of-reviews='6113'></div>"
        html = self.r(products=[product(metafields={"judgeme": {"badge": jm}})])
        self.assertIn("4.77", html)
        self.assertIn("(6113 reviews)", html)
        none = self.r(products=[product()])
        self.assertNotIn("dtj-cs__rating", none)
        shop_sample = self.r(products=[product()], demo_ratings=True)
        self.assertNotIn("dtj-cs__rating", shop_sample)  # never to shoppers
        editor = self.r(products=[product()], design_mode=True, demo_ratings=True)
        self.assertIn("dtj-cs__rating--demo", editor)
        self.assertIn("Sample rating, shown only in the theme editor", editor)
        self.assertNotIn("dtj-cs__rating", self.r(products=[product(metafields={"judgeme": {"badge": jm}})], show_rating=False))

    def test_the_short_line_uses_the_subtitle_then_the_description_and_is_escaped(self):
        html = self.r(products=[product(metafields={"custom": {"subtitle": "Apple Peach | 30ml"}, "judgeme": {"badge": ""}})])
        self.assertIn("Apple Peach | 30ml", html)
        self.assertIn("A gentle daily routine.", self.r(products=[product()]))
        self.assertNotIn("<b>gentle", self.r(products=[product()]))
        self.assertNotIn("dtj-cs__blurb", self.r(products=[product()], show_blurb=False))
        self.assertIn("&lt;script&gt;", self.r(products=[product(title="<script>x</script>")]))

    def test_view_collection_goes_to_each_collection_and_can_be_switched_off(self):
        html = self.r()
        self.assertIn('href="/collections/one">View Collection', html)
        self.assertIn('href="/collections/two">View Collection', html)
        self.assertIn(">See all<", self.r(view_label="See all"))
        self.assertNotIn('class="dtj-cs__view"', self.r(show_view=False))

    def test_the_counter_starts_at_one_and_counts_the_products_shown(self):
        html = self.r(products_per_concern=2)
        self.assertIn("01 / 02", html)
        self.assertIn('data-total="2"', html)
        self.assertNotIn("dtj-cs__progress", self.r(progress=False))

    def test_products_per_concern_limits_the_cards(self):
        self.assertEqual(self.r(products_per_concern=4).count('class="dtj-cs__card"'), 4 + 1)  # 4 products in the first collection, 1 in the second

    def test_colors_and_layout_are_passed_as_variables_and_empty_colors_keep_the_look(self):
        html = self.r(accent_color="#7c5cf0", button_color="#1a0b3b", card_bg="#eee8fb", text_column=30, visible_desktop=4, gap=20)
        for part in ("--cs-accent: #7c5cf0", "--cs-btn: #1a0b3b", "--cs-card: #eee8fb", "--cs-col: 30%", "--cs-n: 4", "--cs-gap: 20px"):
            self.assertIn(part, html)
        plain = self.r()
        for var in ("--cs-accent", "--cs-btn:", "--cs-card", "--cs-pill"):
            self.assertNotIn(var, plain)

    def test_cart_attributes_and_shape_classes(self):
        html = self.r(after_add="cart", button_shape="square", fade_edge=False, arrows="none")
        for part in ('data-after="cart"', "dtj-cs--btn-square", "dtj-cs--arrows-none", "data-cart-add="):
            self.assertIn(part, html)
        self.assertNotIn("dtj-cs--fade", html)
        self.assertNotIn("dtj-cs__arrow", html)

    def test_the_css_is_a_native_snap_row_with_no_hard_coded_colors(self):
        css = (ASSETS / "dtj-concern-slider.css").read_text(encoding="utf-8")
        self.assertIn("scroll-snap-type: x mandatory", css)
        self.assertIn("prefers-reduced-motion: reduce", css)
        self.assertNotRegex(css, r"#[0-9a-fA-F]{3,8}\b")
        self.assertRegex(css, r"(?m)^\.dtj-cs \{[^}]*width: 100%")

    def test_the_script_is_small_and_keeps_the_form_working_without_it(self):
        js = (ASSETS / "dtj-concern-slider.js").read_text(encoding="utf-8")
        self.assertLess(len(js.encode("utf-8")), 10000)
        self.assertIn("customElements.define('dtj-concern-slider'", js)
        self.assertIn(".catch(() => form.submit())", js)
        self.assertNotIn("innerHTML", js)

    def test_no_default_copy_and_sane_setting_counts(self):
        for s in self.m["settings"]:
            if s["type"] in ("text", "textarea"):
                self.assertNotIn("default", s, s["id"])
        self.assertEqual(sum(1 for s in self.m["settings"] if s["type"] == "collection_list"), 1)
        headers = [s for s in self.m["settings"] if s["type"] == "header"]
        self.assertLessEqual(len(headers) + 2, 6)


BA = json.loads((HERE / "manifests" / "before-after.json").read_text(encoding="utf-8"))
BA_SAMPLE = BA["test"]["sample"]


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class BeforeAfterTests(unittest.TestCase):
    m = BA

    def r(self, design_mode=False, **extra):
        return render(self.m, {**BA_SAMPLE, **extra}, design_mode=design_mode)

    def test_it_ships_empty_and_the_editor_says_so(self):
        self.assertEqual(render(self.m, {}), "")
        self.assertIn("DTJ Before After is empty", render(self.m, {}, design_mode=True))

    def test_the_picture_is_a_real_slider_with_both_pictures_and_the_start_position(self):
        html = self.r(start_position=30)
        self.assertEqual(html.count("<img "), 2)
        self.assertIn("before-pic", html)
        self.assertIn("after-pic", html)
        self.assertIn('<input class="dtj-ba__range" type="range" min="0" max="100" step="1" value="30"', html)
        self.assertIn("--ba-pos: 30%", html)
        self.assertIn('aria-label="Before / After"', html)
        self.assertIn('alt="Before picture alt"', html)  # the picture's own alt text when it has one
        self.assertIn('alt="After"', html)  # else the tag word

    def test_one_picture_alone_shows_no_slider(self):
        html = self.r(after_image="")
        self.assertNotIn("dtj-ba__range", html)
        self.assertIn("dtj-ba--text-only", html)
        self.assertIn("From mess to", html)

    def test_pictures_only_works_with_no_words(self):
        html = render(self.m, {"before_image": BA_SAMPLE["before_image"], "after_image": BA_SAMPLE["after_image"]})
        self.assertIn("dtj-ba--pic-only", html)
        self.assertNotIn("dtj-ba__text", html)

    def test_three_versions_and_their_own_icons(self):
        for v in ("card", "circle", "square"):
            self.assertIn(f"dtj-ba--{v}", self.r(variation=v))
        card = self.r(point_3_bold="Third")
        self.assertEqual(card.count('stroke-width="2.200"'), 3)  # ticks
        circle = self.r(variation="circle", point_3_bold="Third")
        self.assertEqual(circle.count("<svg class=\"dtj-ba__ico\""), 3)
        self.assertNotIn('stroke-width="2.200"', circle)  # heart, leaf and smile are filled
        self.assertEqual(self.r(variation="square", point_3_bold="Third").count('fill="currentColor" d="M12 2.500'), 3)  # the badge
        self.assertIn("M12 21l-1.400", self.r(point_1_icon="heart"))  # a chosen icon wins over the version's own

    def test_the_heading_has_an_accent_part_and_a_choice_of_tag(self):
        html = self.r()
        self.assertIn('dtj-ba__hl dtj-ba__accent">effortlessly clean', html)
        self.assertIn("<h3", self.r(heading_tag="h3"))
        self.assertNotIn("dtj-ba__heading", self.r(heading="", heading_accent=""))

    def test_stars_are_off_by_default_so_no_rating_is_claimed(self):
        self.assertNotIn("dtj-ba__stars", self.r())
        self.assertEqual(self.r(show_stars=True, eyebrow_bold="Loved").count("<svg viewBox=\"0 0 24 24\" focusable=\"false\"><path d=\"M12 2.500l2.900"), 5)
        self.assertNotIn("dtj-ba__eyebrow", self.r())  # no small line without words or stars

    def test_the_paragraph_keeps_bold_and_the_words_are_escaped(self):
        self.assertIn("<strong>concentrated</strong>", self.r())
        html = self.r(point_1_bold="<b>x</b>", heading="<i>h</i>", button_label="<u>b</u>")
        for raw in ("<b>x</b>", "<i>h</i>", "<u>b</u>"):
            self.assertNotIn(raw, html)

    def test_tags_follow_the_settings(self):
        self.assertIn("Before</span>", self.r())
        self.assertNotIn("dtj-ba__tag", self.r(show_labels=False))
        html = self.r(before_label="Day 0", after_label="Day 14")
        self.assertIn(">Day 0<", html)
        self.assertIn(">Day 14<", html)
        self.assertIn("dtj-ba--tags-bottom", self.r(tag_place="bottom"))

    def test_the_button_is_a_link_with_an_optional_arrow(self):
        html = self.r()
        self.assertIn('href="/collections/all"', html)
        self.assertIn("<path d=\"M5 12h14", html)
        self.assertNotIn("<path d=\"M5 12h14", self.r(button_arrow=False))
        self.assertNotIn("dtj-ba__button", self.r(button_label=""))

    def test_side_shape_and_colors_are_passed_on_and_empty_colors_keep_the_look(self):
        html = self.r(picture_side="left", picture_shape="0.8", accent_color="#112233", accent_color_2="#445566", button_color="#778899", panel_color="#aabbcc")
        for part in ("dtj-ba--side-left", "--ba-ratio: 0.8", "--ba-accent: #112233", "--ba-accent-2: #445566", "--ba-btn: #778899", "--ba-tint: #aabbcc", "dtj-ba--grad"):
            self.assertIn(part, html)
        plain = self.r()
        for var in ("--ba-accent", "--ba-btn", "--ba-tint", "--ba-ratio:", "dtj-ba--grad"):
            self.assertNotIn(var, plain)

    def test_the_css_clips_the_after_picture_with_the_position_and_has_no_hard_coded_colors(self):
        css = (ASSETS / "dtj-before-after.css").read_text(encoding="utf-8")
        self.assertIn("clip-path: inset(0 0 0 var(--ba-pos, 50%))", css)
        self.assertIn("touch-action: pan-y", css)
        self.assertNotRegex(css, r"#[0-9a-fA-F]{3,8}")
        self.assertRegex(css, r"(?m)^\.dtj-ba \{[^}]*width: 100%")

    def test_the_script_is_tiny_and_only_copies_the_value(self):
        js = (ASSETS / "dtj-before-after.js").read_text(encoding="utf-8")
        self.assertLess(len(js.encode("utf-8")), 1500)
        self.assertIn("customElements.define('dtj-before-after'", js)
        self.assertNotIn("fetch", js)

    def test_no_default_copy_and_sane_setting_counts(self):
        for s in self.m["settings"]:
            if s["type"] in ("text", "textarea", "richtext"):
                self.assertNotIn("default", s, s["id"])
        self.assertLessEqual(sum(1 for s in self.m["settings"] if s["type"] == "header") + 2, 6)


if __name__ == "__main__":
    unittest.main()
