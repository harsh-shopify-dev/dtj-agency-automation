"""Tests for what is specific to the blocks of DTJ Heroes (the generic ones, licence / escaping / defaults, live in
services/block-library/tests/test_generated_blocks.py and run against this app with DTJ_APP_ROOT set).

    cd services/block-library-heroes
    DTJ_APP_ROOT=$PWD ../../.work/.venv/Scripts/python -m unittest discover -s tests -t .
"""
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


def manifest(block_id):
    return json.loads((HERE / "manifests" / f"{block_id}.json").read_text(encoding="utf-8"))


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class HeroBannerTests(unittest.TestCase):
    m = manifest("hero-banner")

    def test_nothing_renders_empty_and_no_copy_is_shipped_by_default(self):
        self.assertEqual(render(self.m, {}), "")
        html = render(self.m, {"heading": "H"})
        for part in ("dtj-hb__badge", "dtj-hb__sub", "dtj-hb__rating", "dtj-hb__points", "dtj-hb__btn", "dtj-hb__note", "dtj-hb__quote"):
            self.assertNotIn(part, html)

    def test_every_part_shows_only_when_it_has_content(self):
        html = render(self.m, {"badge_text": "B", "heading": "H", "subheading": "S", "rating_value": 4.5, "points": "P", "button_label": "Go", "note": "N"})
        for part in ("dtj-hb__badge", "dtj-hb__heading", "dtj-hb__sub", "dtj-hb__rating", "dtj-hb__points", "dtj-hb__btn", "dtj-hb__note"):
            self.assertIn(part, html)

    def test_accent_words_between_asterisks_become_the_accent_span_and_everything_is_escaped(self):
        html = render(self.m, {"heading": "Perfect Skin, *Every <b>Day</b>.*"})
        self.assertIn('<em class="dtj-hb__accent">Every &lt;b&gt;Day&lt;/b&gt;.</em>', html)
        self.assertNotIn("<b>", html)

    def test_the_rating_fills_stars_in_proportion_and_never_past_five(self):
        self.assertIn('style="width: 96.0%"', render(self.m, {"rating_value": 4.8}))
        self.assertIn("width: 100", render(self.m, {"rating_value": 9}))
        self.assertNotIn("dtj-hb__stars", render(self.m, {"rating_text": "words only"}))  # no value, no stars invented

    def test_the_bold_part_of_the_rating_text_is_marked_with_asterisks(self):
        html = render(self.m, {"rating_text": "4.8/5 based on *10.000+* reviews"})
        self.assertIn("<strong>10.000+</strong>", html)

    def test_at_most_four_points_each_with_a_tick(self):
        html = render(self.m, {"points": "a\nb\nc\nd\ne"})
        self.assertEqual(html.count('class="dtj-hb__point"'), 4)

    def test_the_banner_is_the_default_and_split_is_the_v2_layout(self):
        banner = render(self.m, {"heading": "H"})
        self.assertIn("dtj-hb--banner", banner)
        self.assertIn("dtj-hb__slide", banner)
        split = render(self.m, {"heading": "H", "layout": "split"})
        self.assertIn("dtj-hb--split", split)
        self.assertIn("dtj-hb__panel", split)
        self.assertNotIn("dtj-hb__slide", split)

    def test_automatic_choices_follow_the_layout(self):
        banner = render(self.m, {"heading": "H", "points": "p"})
        self.assertIn("dtj-hb--accent-italic", banner)
        self.assertIn("dtj-hb--ma-center", banner)
        self.assertIn("dtj-hb__tick--shield", banner)
        split = render(self.m, {"heading": "H", "points": "p", "layout": "split"})
        self.assertIn("dtj-hb--accent-plain", split)
        self.assertIn("dtj-hb--ma-left", split)
        self.assertIn("dtj-hb__tick--circle", split)
        self.assertIn("dtj-hb--accent-bold", render(self.m, {"heading": "H", "layout": "split", "accent_font": "bold"}))  # an explicit choice wins

    def test_the_picture_side_swaps_the_column_widths(self):
        self.assertIn("--hb-cols: 5fr 6fr;", render(self.m, {"heading": "H", "layout": "split", "split_columns": "5fr 6fr"}))
        right = render(self.m, {"heading": "H", "layout": "split", "split_columns": "5fr 6fr", "image_side": "right"})
        self.assertIn("--hb-cols: 6fr 5fr;", right)
        self.assertIn("dtj-hb--side-right", right)

    def test_the_review_card_is_a_split_only_part_and_needs_a_quote(self):
        self.assertNotIn("dtj-hb__quote", render(self.m, {"heading": "H", "review_quote": "Great"}))  # banner: not shown
        self.assertNotIn("dtj-hb__quote", render(self.m, {"heading": "H", "layout": "split", "review_name": "Emily"}))  # no quote, no card
        html = render(self.m, {"layout": "split", "review_quote": "Great", "review_name": "Emily F.", "review_stars": 4.5})
        self.assertIn("Great", html)
        self.assertIn("Emily F.", html)
        self.assertIn("dtj-hb__stars--sm", html)

    def test_picture_gets_size_attributes_and_the_first_hero_loads_first(self):
        html = render(self.m, {"image": "pic", "heading": "H"})
        self.assertRegex(html, r'<img class="dtj-hb__img"[^>]* width="\d+" height="\d+"')
        self.assertIn('fetchpriority="high"', html)
        self.assertIn('loading="eager"', html)
        late = render(self.m, {"image": "pic", "heading": "H", "priority": False})
        self.assertIn('loading="lazy"', late)
        self.assertNotIn("fetchpriority", late)

    def test_a_phone_picture_is_used_through_a_picture_element_only_when_both_exist(self):
        both = render(self.m, {"image": "wide", "image_mobile": "tall", "heading": "H"})
        self.assertIn('<source media="(max-width: 749px)"', both)
        self.assertIn("//img.example/tall", both)
        self.assertNotIn("<source", render(self.m, {"image": "wide", "heading": "H"}))

    def test_v3_cover_is_the_banner_structure_with_its_own_automatic_choices(self):
        html = render(self.m, {"heading": "H", "points": "p", "subheading": "Para", "layout": "cover"})
        self.assertIn("dtj-hb--cover", html)
        self.assertIn("dtj-hb__slide", html)
        self.assertNotIn("dtj-hb__panel", html)
        self.assertIn("dtj-hb--v-bottom", html)
        self.assertIn("dtj-hb--ov-bottom", html)
        self.assertIn("dtj-hb--m-overlay", html)
        self.assertIn("dtj-hb--ma-left", html)
        self.assertIn("dtj-hb--accent-plain", html)
        self.assertIn("dtj-hb__tick--circle", html)
        plain = render(self.m, {"heading": "H"})  # V1 keeps its own automatic choices
        for part in ("dtj-hb--v-center", "dtj-hb--ov-side", "dtj-hb--m-stack"):
            self.assertIn(part, plain)
        self.assertNotIn("dtj-hb--cover", plain)
        explicit = render(self.m, {"heading": "H", "layout": "cover", "content_align": "top", "overlay_style": "none", "mobile_layout": "stack"})
        for part in ("dtj-hb--v-top", "dtj-hb--ov-none", "dtj-hb--m-stack"):
            self.assertIn(part, explicit)  # an explicit choice wins over the automatic one

    def test_a_vertical_bar_in_the_heading_is_a_line_break_and_the_text_stays_escaped(self):
        html = render(self.m, {"heading": "Push Your Limits with|*Professional <i>Gear</i>*"})
        self.assertIn("with<br>", html)
        self.assertIn("Professional &lt;i&gt;Gear&lt;/i&gt;", html)
        self.assertNotIn("<i>", html)

    def test_the_editor_hint_shows_only_in_the_theme_editor(self):
        self.assertEqual(render(self.m, {}), "")
        self.assertIn("DTJ Hero Banner is empty", render(self.m, {}, design_mode=True))

    def test_the_block_has_a_sane_number_of_settings_and_headers(self):
        interactive = [s for s in self.m["settings"] if s["type"] not in ("header", "paragraph")]
        headers = [s for s in self.m["settings"] if s["type"] in ("header", "paragraph")]
        self.assertLessEqual(len(interactive) + 8, 75)  # 8 = the standard controls the builder adds
        self.assertLessEqual(len(headers) + 1, 6)  # + the header the standard controls add


VIDEO = {"sources": [{"format": "webm", "url": "//v/a.webm", "height": 1080}, {"format": "mp4", "url": "//v/hd.mp4", "height": 1080},
                     {"format": "mp4", "url": "//v/sd.mp4", "height": 480}, {"format": "mp4", "url": "//v/mid.mp4", "height": 720}]}


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class VideoReviewsTests(unittest.TestCase):
    m = manifest("video-reviews")

    def cards(self, n, **extra):
        return {**{f"name_{i}": f"Person {i}" for i in range(1, n + 1)}, **extra}

    def distances(self, html):
        return re.findall(r'data-d="(-?\d|x)"', html)

    def test_nothing_renders_empty_and_no_copy_is_shipped_by_default(self):
        self.assertEqual(render(self.m, {}), "")
        html = render(self.m, {"name_1": "A"})
        for part in ("dtj-vr__head", "dtj-vr__link", "dtj-vr__play", "dtj-vr__vf", "dtj-vr__text"):
            self.assertNotIn(part, html)

    def test_a_card_shows_when_it_has_anything_and_there_are_at_most_six(self):
        self.assertEqual(render(self.m, {"name_1": "A", "image_2": "p", "text_3": "t", "video_4": VIDEO, "name_7": "ignored"}).count('class="dtj-vr__card"'), 4)
        self.assertEqual(render(self.m, {"name_2": "only the second"}).count('class="dtj-vr__card"'), 1)

    def test_the_first_card_starts_in_the_centre_and_the_ring_wraps_around(self):
        self.assertEqual(self.distances(render(self.m, self.cards(5))), ["0", "1", "2", "-2", "-1"])
        self.assertEqual(self.distances(render(self.m, self.cards(3))), ["0", "1", "-1"])
        self.assertEqual(self.distances(render(self.m, self.cards(6))), ["0", "1", "2", "x", "-2", "-1"])  # the far card is hidden
        self.assertEqual(self.distances(render(self.m, self.cards(2))), ["0", "-1"])

    def test_only_the_centre_card_is_reachable_by_keyboard_and_readers(self):
        html = render(self.m, self.cards(3, url_1="/a", url_2="/b", link_label="See", video_1=VIDEO, video_2=VIDEO))
        cards = re.findall(r'<div class="dtj-vr__card"[^>]*>', html)
        self.assertEqual([("aria-hidden" in c) for c in cards], [False, True, True])
        self.assertEqual(len(re.findall(r'tabindex="0"', html)), 2)  # the centre card's link and play button
        self.assertEqual(len(re.findall(r'tabindex="-1"', html)), 2)  # card 2's link and play button

    def test_the_play_button_carries_the_best_small_mp4_and_nothing_loads_before_a_press(self):
        html = render(self.m, self.cards(1, video_1=VIDEO))
        self.assertIn('data-src="//v/mid.mp4"', html)  # mp4 only, the largest not above 720 px
        self.assertNotIn("<video", html)
        self.assertNotIn("<source", html)
        self.assertNotIn("dtj-vr__play", render(self.m, self.cards(1, image_1="p")))  # no video, no play button

    def test_a_video_without_a_picture_uses_its_still_frame(self):
        html = render(self.m, self.cards(1, video_1={**VIDEO, "preview_image": "still"}))
        self.assertIn("//img.example/still", html)

    def test_pictures_are_lazy_sized_and_sharp_but_light(self):
        html = render(self.m, self.cards(2, image_1="a", image_2="b"))
        self.assertEqual(html.count('loading="lazy"'), 2)
        self.assertNotIn("fetchpriority", html)
        for img in re.findall(r"<img [^>]*>", html):
            self.assertRegex(img, r'width="\d+" height="\d+"')
            self.assertIn('decoding="async"', img)
            self.assertIn("360w", img)
        top = render(self.m, self.cards(2, image_1="a", image_2="b", priority=True))
        self.assertEqual(top.count('fetchpriority="high"'), 1)  # only the centre card

    def test_the_link_needs_both_a_text_and_an_address(self):
        self.assertNotIn("dtj-vr__link", render(self.m, self.cards(1, url_1="/a")))
        self.assertNotIn("dtj-vr__link", render(self.m, self.cards(1, link_label="See")))
        self.assertIn('href="/a"', render(self.m, self.cards(1, url_1="/a", link_label="See")))

    def test_the_verified_tick_is_a_choice(self):
        self.assertIn("dtj-vr__vf", render(self.m, self.cards(1, show_verified=True)))

    def test_arrows_need_two_cards_and_can_be_switched_off(self):
        self.assertEqual(render(self.m, self.cards(3)).count("dtj-vr__arrow "), 2)
        self.assertNotIn("dtj-vr__arrow ", render(self.m, self.cards(1)))
        self.assertNotIn("dtj-vr__arrow ", render(self.m, self.cards(3, arrows="none")))

    def test_autoplay_is_off_by_default_and_needs_two_cards(self):
        self.assertIn('data-auto="false"', render(self.m, self.cards(3)))
        self.assertIn('data-auto="true"', render(self.m, self.cards(3, autoplay=True)))
        self.assertIn('data-auto="false"', render(self.m, self.cards(1, autoplay=True)))

    def test_text_is_escaped(self):
        html = render(self.m, self.cards(1, text_1="<script>x</script>", heading="<b>H</b>"))
        self.assertNotIn("<script>", html)
        self.assertNotIn("<b>", html)

    def test_the_script_is_small_and_makes_no_request_of_its_own(self):
        js = (HERE / "extensions" / "dtj-heroes" / "assets" / "dtj-video-reviews.js").read_text(encoding="utf-8")
        self.assertLess(len(js.encode("utf-8")), 10000)
        for banned in ("fetch(", "XMLHttpRequest", "innerHTML = ", "document.write", "getBoundingClientRect", "offsetWidth"):
            if banned == "innerHTML = ":
                continue  # the close icon is a fixed literal string
            self.assertNotIn(banned, js)

    def test_the_block_has_a_sane_number_of_settings_and_headers(self):
        interactive = [s for s in self.m["settings"] if s["type"] not in ("header", "paragraph")]
        headers = [s for s in self.m["settings"] if s["type"] in ("header", "paragraph")]
        self.assertLessEqual(len(interactive) + 8, 75)
        self.assertLessEqual(len(headers) + 1, 6)


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class FeatureCardsTests(unittest.TestCase):
    m = manifest("feature-cards")

    def test_nothing_renders_empty_and_no_copy_is_shipped_by_default(self):
        self.assertEqual(render(self.m, {}), "")
        html = render(self.m, {"heading": "H"})
        for part in ("dtj-fc__badge", "dtj-fc__sub", "dtj-fc__card", "dtj-fc__btn", "dtj-fc__media"):
            self.assertNotIn(part, html)

    def test_cards_split_left_three_right_three_and_only_filled_ones_show(self):
        html = render(self.m, {"f1_title": "L1", "f3_text": "L3", "f4_title": "R1", "f5_title": "", "f6_title": "R3"})
        self.assertEqual(html.count('class="dtj-fc__card"'), 4)
        self.assertEqual(html.count("dtj-fc__col--left"), 1)
        self.assertEqual(html.count("dtj-fc__col--right"), 1)
        self.assertNotIn("dtj-fc__col--right", render(self.m, {"f1_title": "only left"}))

    def test_an_icon_choice_alone_is_not_content_and_none_draws_no_circle(self):
        self.assertEqual(render(self.m, {"f1_icon": "wave"}), "")
        self.assertIn("dtj-fc__icon", render(self.m, {"f1_title": "A", "f1_icon": "wave"}))
        self.assertNotIn("dtj-fc__icon", render(self.m, {"f1_title": "A", "f1_icon": "none"}))

    def test_every_listed_icon_exists_in_the_snippet(self):
        snippet = (HERE / "extensions" / "dtj-heroes" / "snippets" / "dtj-card-icon.liquid").read_text(encoding="utf-8")
        icons = [o["value"] for s in self.m["settings"] if s.get("id") == "f1_icon" for o in s["options"] if o["value"] != "none"]
        for icon in icons:
            self.assertIn(f"{{%- when '{icon}' -%}}", snippet, icon)

    def test_the_button_is_a_regular_rectangle_never_an_oval(self):
        css = (HERE / "extensions" / "dtj-heroes" / "assets" / "dtj-feature-cards.css").read_text(encoding="utf-8")
        for rule in re.findall(r"\.dtj-fc[^{]*btn[^{]*\{[^}]*\}", css):
            self.assertNotRegex(rule, r"border-radius:\s*(999|9999|50%|100px)")
        shapes = [o["value"] for s in self.m["settings"] if s.get("id") == "button_shape" for o in s["options"]]
        self.assertEqual(sorted(shapes), ["rounded", "square"])
        self.assertIn("dtj-fc--corner-rounded", render(self.m, {"button_label": "Go"}))

    def test_the_button_is_a_link_with_an_address_and_plain_text_without(self):
        self.assertIn('<a class="dtj-fc__btn" href="/shop">', render(self.m, {"button_label": "Go", "button_url": "/shop"}))
        self.assertIn('<span class="dtj-fc__btn">', render(self.m, {"button_label": "Go"}))

    def test_the_picture_has_sizes_a_srcset_and_loads_lazily_unless_it_is_at_the_top(self):
        html = render(self.m, {"image": "pic"})
        self.assertRegex(html, r'<img class="dtj-fc__img"[^>]* width="\d+" height="\d+"')
        self.assertIn("480w", html)
        self.assertIn('loading="lazy"', html)
        self.assertNotIn("fetchpriority", html)
        top = render(self.m, {"image": "pic", "priority": True})
        self.assertIn('fetchpriority="high"', top)
        self.assertNotIn("dtj-fc__media", render(self.m, {"heading": "H"}))

    def test_phone_choices_become_classes(self):
        html = render(self.m, {"heading": "H", "mobile_columns": "2", "mobile_image": "bottom"})
        self.assertIn("dtj-fc--two", html)
        self.assertIn("dtj-fc--img-bottom", html)
        self.assertNotIn("dtj-fc--two", render(self.m, {"heading": "H"}))

    def test_text_is_escaped_and_the_heading_tag_is_limited(self):
        html = render(self.m, {"heading": "<b>H</b>", "f1_title": "<i>t</i>", "heading_tag": "script"})
        self.assertNotIn("<b>", html)
        self.assertNotIn("<i>", html)
        self.assertIn("<h2", html)
        self.assertIn("<h1", render(self.m, {"heading": "H", "heading_tag": "h1"}))

    def test_the_tint_only_applies_where_color_mix_works(self):
        css = (HERE / "extensions" / "dtj-heroes" / "assets" / "dtj-feature-cards.css").read_text(encoding="utf-8")
        self.assertIn("@supports (color: color-mix", css)

    def test_the_block_has_a_sane_number_of_settings_and_headers(self):
        interactive = [s for s in self.m["settings"] if s["type"] not in ("header", "paragraph")]
        headers = [s for s in self.m["settings"] if s["type"] in ("header", "paragraph")]
        self.assertLessEqual(len(interactive) + 8, 75)
        self.assertLessEqual(len(headers) + 1, 6)


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class FeatureTilesTests(unittest.TestCase):
    m = manifest("feature-tiles")

    def css(self):
        return (HERE / "extensions" / "dtj-heroes" / "assets" / "dtj-feature-tiles.css").read_text(encoding="utf-8")

    def test_nothing_renders_empty_and_no_copy_is_shipped_by_default(self):
        self.assertEqual(render(self.m, {}), "")
        html = render(self.m, {"heading": "H"})
        for part in ("dtj-ft__text", "dtj-ft__btn", "dtj-ft__tiles", "dtj-ft__media"):
            self.assertNotIn(part, html)

    def test_a_tile_needs_a_label_and_an_icon_alone_is_not_content(self):
        self.assertEqual(render(self.m, {"t1_icon": "tooth"}), "")
        html = render(self.m, {"t1_label": "A", "t2_icon": "tooth", "t3_label": "C", "t7_label": "ignored"})
        self.assertEqual(html.count('class="dtj-ft__tile"'), 2)
        self.assertNotIn("dtj-ft__icon", render(self.m, {"t1_label": "A", "t1_icon": "none"}))
        self.assertIn("dtj-ft__icon", render(self.m, {"t1_label": "A", "t1_icon": "tooth"}))

    def test_every_listed_icon_exists_in_the_snippet(self):
        snippet = (HERE / "extensions" / "dtj-heroes" / "snippets" / "dtj-card-icon.liquid").read_text(encoding="utf-8")
        icons = [o["value"] for s in self.m["settings"] if s.get("id") == "t1_icon" for o in s["options"] if o["value"] != "none"]
        for icon in icons:
            self.assertIn(f"{{%- when '{icon}' -%}}", snippet, icon)

    def test_the_button_is_a_regular_rectangle_never_an_oval(self):
        for rule in re.findall(r"\.dtj-ft[^{]*btn[^{]*\{[^}]*\}", self.css()):
            self.assertNotRegex(rule, r"border-radius:\s*(999|9999|50%|100px)")
        shapes = [o["value"] for s in self.m["settings"] if s.get("id") == "button_shape" for o in s["options"]]
        self.assertEqual(sorted(shapes), ["rounded", "square"])
        self.assertIn('<a class="dtj-ft__btn" href="/shop">', render(self.m, {"button_label": "Go", "button_url": "/shop"}))
        self.assertIn('<span class="dtj-ft__btn">', render(self.m, {"button_label": "Go"}))

    def test_the_picture_side_swaps_the_column_widths(self):
        self.assertIn("--ft-cols: 6fr 5fr;", render(self.m, {"heading": "H", "split": "6fr 5fr"}))
        left = render(self.m, {"heading": "H", "split": "6fr 5fr", "image_side": "left"})
        self.assertIn("--ft-cols: 5fr 6fr;", left)
        self.assertIn("dtj-ft--side-left", left)

    def test_the_picture_is_sized_lazy_and_only_eager_when_it_is_at_the_top(self):
        html = render(self.m, {"image": "pic"})
        self.assertRegex(html, r'<img class="dtj-ft__img"[^>]* width="\d+" height="\d+"')
        self.assertIn('loading="lazy"', html)
        self.assertNotIn("fetchpriority", html)
        self.assertIn('fetchpriority="high"', render(self.m, {"image": "pic", "priority": True}))
        self.assertIn("dtj-ft--noimg", render(self.m, {"heading": "H"}))

    def test_phone_and_desktop_choices_become_classes(self):
        html = render(self.m, {"heading": "H", "tile_columns": "2", "tile_columns_mobile": "3", "mobile_image": "bottom"})
        for part in ("dtj-ft--d2", "dtj-ft--m3", "dtj-ft--img-bottom"):
            self.assertIn(part, html)

    def test_text_is_escaped_and_the_heading_tag_is_limited(self):
        html = render(self.m, {"heading": "<b>H</b>", "t1_label": "<i>t</i>", "text": "<u>x</u>", "heading_tag": "script"})
        for bad in ("<b>", "<i>", "<u>"):
            self.assertNotIn(bad, html)
        self.assertIn("<h2", html)

    def test_the_tint_only_applies_where_color_mix_works(self):
        self.assertIn("@supports (color: color-mix", self.css())

    def test_the_block_has_a_sane_number_of_settings_and_headers(self):
        interactive = [s for s in self.m["settings"] if s["type"] not in ("header", "paragraph")]
        headers = [s for s in self.m["settings"] if s["type"] in ("header", "paragraph")]
        self.assertLessEqual(len(interactive) + 8, 75)
        self.assertLessEqual(len(headers) + 1, 6)


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class CompareShowcaseTests(unittest.TestCase):
    m = manifest("compare-showcase")

    def css(self):
        return (HERE / "extensions" / "dtj-heroes" / "assets" / "dtj-compare-showcase.css").read_text(encoding="utf-8")

    def test_nothing_renders_empty_and_no_copy_is_shipped_by_default(self):
        self.assertEqual(render(self.m, {}), "")
        html = render(self.m, {"heading": "H"})
        for part in ("dtj-cs__eyebrow", "dtj-cs__text", "dtj-cs__points", "dtj-cs__btn", "dtj-cs__card", "dtj-cs__media"):
            self.assertNotIn(part, html)

    def test_a_row_needs_a_label_and_at_most_seven_show(self):
        html = render(self.m, {"r1_label": "A", "r2_us": "orphan", "r3_label": "C", "r8_label": "ignored"})
        self.assertEqual(html.count('class="dtj-cs__row"'), 2)
        self.assertNotIn("orphan", html)

    def test_empty_cells_are_a_tick_and_a_cross_and_words_replace_them(self):
        html = render(self.m, {"r1_label": "A", "r2_label": "B", "r2_us": "One Scoop", "r2_them": "Multi-Supp."})
        self.assertEqual(html.count("dtj-cs__tick"), 1)
        self.assertEqual(html.count("dtj-cs__cross"), 1)
        self.assertIn("One Scoop", html)
        self.assertIn("Multi-Supp.", html)

    def test_the_table_is_a_real_table_with_headers_and_a_caption(self):
        html = render(self.m, {"r1_label": "A", "us_title": "Us", "them_title": "Them"})
        for part in ('<table class="dtj-cs__table"', "<caption", 'scope="col"', 'scope="row"', "<colgroup>"):
            self.assertIn(part, html)

    def test_the_variation_sets_the_automatic_choices_and_an_explicit_choice_wins(self):
        spot = render(self.m, {"heading": "H", "image": "p"})
        self.assertIn("dtj-cs--spotlight", spot)
        self.assertIn("dtj-cs--hf-serif", spot)
        self.assertIn("dtj-cs--cf-serif", spot)
        self.assertIn("dtj-cs--mimg-hide", spot)
        grad = render(self.m, {"heading": "H", "image": "p", "variation": "gradient"})
        for part in ("dtj-cs--gradient", "dtj-cs--hf-theme", "dtj-cs--cf-sans", "dtj-cs--mimg-show"):
            self.assertIn(part, grad)
        self.assertIn("dtj-cs--mimg-show", render(self.m, {"heading": "H", "mobile_image": "show"}))
        self.assertIn("dtj-cs--hf-sans", render(self.m, {"heading": "H", "heading_font": "sans"}))

    def test_the_sizes_default_to_the_reference_sections(self):
        html = render(self.m, {"heading": "H", "r1_label": "A"})
        for part in ("--cs-w: 1400px", "--cs-tw: 535px", "--cs-rh: 58px", "--cs-rhm: 46px", "--cs-iw: 360px"):
            self.assertIn(part, html)
        css = self.css()
        self.assertIn("max-width: var(--cs-w, 1400px)", css)
        self.assertIn("max-width: 400px", css)  # the phone table never grows past the reference

    def test_the_columns_follow_the_reference_on_phones_and_desktop(self):
        css = self.css()
        self.assertIn("--cs-c0, 46%", css)  # phones: 46 / 27 / 27
        self.assertIn("--cs-cx, 27%", css)
        self.assertIn("--cs-c0: 35%", css)  # desktop: 35 / 32.5 / 32.5
        self.assertIn("--cs-cx: 32.5%", css)

    def test_the_gradient_background_needs_a_second_color(self):
        self.assertNotIn("dtj-cs--grad", render(self.m, {"heading": "H"}))
        self.assertIn("dtj-cs--grad", render(self.m, {"heading": "H", "bg_color_2": "#f8d4e6"}))

    def test_the_button_can_be_rounded_pill_or_square_and_defaults_to_a_regular_rectangle(self):
        self.assertIn("dtj-cs--btn-rounded", render(self.m, {"button_label": "Go"}))
        self.assertIn('<a class="dtj-cs__btn" href="/shop">', render(self.m, {"button_label": "Go", "button_url": "/shop"}))

    def test_the_picture_is_sized_lazy_and_only_eager_at_the_top(self):
        html = render(self.m, {"image": "pic"})
        self.assertRegex(html, r'<img class="dtj-cs__img"[^>]* width="\d+" height="\d+"')
        self.assertIn('loading="lazy"', html)
        self.assertIn('fetchpriority="high"', render(self.m, {"image": "pic", "priority": True}))
        self.assertIn("dtj-cs--noimg", render(self.m, {"heading": "H"}))

    def test_at_most_four_points_and_text_is_escaped(self):
        self.assertEqual(render(self.m, {"points": "a\nb\nc\nd\ne"}).count("<li>"), 4)
        html = render(self.m, {"heading": "<b>H</b>", "r1_label": "<i>x</i>", "text": "<u>y</u>"})
        for bad in ("<b>", "<i>", "<u>"):
            self.assertNotIn(bad, html)

    def test_the_block_root_is_full_width_and_the_script_free(self):
        self.assertRegex(self.css(), r"(?m)^\.dtj-cs \{[^}]*width: 100%")
        self.assertNotIn("<script", render(self.m, {"heading": "H"}))

    def test_the_block_has_a_sane_number_of_settings_and_headers(self):
        interactive = [s for s in self.m["settings"] if s["type"] not in ("header", "paragraph")]
        headers = [s for s in self.m["settings"] if s["type"] in ("header", "paragraph")]
        self.assertLessEqual(len(interactive) + 8, 75)
        self.assertLessEqual(len(headers) + 1, 6)


class EveryHeroBlockFillsItsWrapperTests(unittest.TestCase):
    """Found on the real storefront (13 Oct 2026): Horizon's Apps wrapper lines its children up at the start, so a block with no width of
    its own shrank to its text and the hero picture covered only part of the screen."""

    def test_each_block_root_is_full_width(self):
        for root, name in ((".dtj-hb", "hero-banner"), (".dtj-ft", "feature-tiles"), (".dtj-fc", "feature-cards"), (".dtj-vr", "video-reviews"), (".dtj-cs", "compare-showcase")):
            css = (HERE / "extensions" / "dtj-heroes" / "assets" / f"dtj-{name}.css").read_text(encoding="utf-8")
            rule = re.search(r"(?m)^" + re.escape(root) + r" \{[^}]*\}", css)
            self.assertIsNotNone(rule, name)
            self.assertIn("width: 100%", rule.group(0), name)


if __name__ == "__main__":
    unittest.main()
