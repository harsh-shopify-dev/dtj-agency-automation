"""Tests for what is specific to the blocks of DTJ Sections 2 (the generic ones, licence / escaping / defaults, live in
services/block-library/tests/test_generated_blocks.py and run against this app with DTJ_APP_ROOT set).

    cd services/block-library-sections-2
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
# the generic tests (licence off = nothing shipped, escaping, standard controls, no stale generated files) run for this app too
from test_generated_blocks import EveryBlockTests, GeneratedFilesTests  # noqa: E402,F401


def manifest(block_id):
    return json.loads((HERE / "manifests" / f"{block_id}.json").read_text(encoding="utf-8"))


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class FeatureShowcaseTests(unittest.TestCase):
    m = manifest("feature-showcase")

    def test_a_feature_shows_when_it_has_a_title_text_or_own_icon_and_nothing_renders_empty(self):
        html = render(self.m, {"f1_title": "A", "f2_text": "only text", "f3_image": "icon", "f5_icon": "leaf"})
        self.assertEqual(html.count('class="dtj-fs__feature"'), 3)
        self.assertEqual(render(self.m, {"f1_icon": "leaf"}), "")  # an icon choice alone is not content

    def test_left_features_use_column_1_and_right_features_column_3_with_their_own_row_numbers(self):
        html = render(self.m, {"f1_title": "L1", "f3_title": "L2", "f5_title": "R1"})
        self.assertIn("--fs-col: 1; --fs-row: 1;", html)
        self.assertIn("--fs-col: 1; --fs-row: 2;", html)  # the second FILLED left feature, whatever its slot number
        self.assertIn("--fs-col: 3; --fs-row: 1;", html)

    def test_on_phones_left_and_right_are_interleaved(self):
        html = render(self.m, {"f1_title": "L1", "f2_title": "L2", "f4_title": "R1", "f5_title": "R2"})
        self.assertEqual(re.findall(r"--fs-ord: (\d+);", html), ["1", "3", "2", "4"])  # L1=1, L2=3, R1=2, R2=4

    def test_the_image_spans_as_many_rows_as_the_longer_side(self):
        html = render(self.m, {"image": "pic", "f1_title": "A", "f2_title": "B", "f3_title": "C", "f4_title": "D"})
        self.assertIn("--fs-span: 3;", html)
        self.assertIn('class="dtj-fs__media"', html)

    def test_without_an_image_the_block_still_works_and_says_so(self):
        html = render(self.m, {"f1_title": "A"})
        self.assertIn("dtj-fs--noimg", html)
        self.assertNotIn("dtj-fs__media", html)

    def test_the_built_in_icon_is_the_choice_and_none_hides_it_and_an_own_icon_replaces_it(self):
        self.assertIn("<svg", render(self.m, {"f1_title": "A", "f1_icon": "leaf"}))
        self.assertNotIn("dtj-fs__icon", render(self.m, {"f1_title": "A", "f1_icon": "none"}))
        own = render(self.m, {"f1_title": "A", "f1_icon": "leaf", "f1_image": "icon"})
        self.assertIn("dtj-fs__icon-img", own)
        self.assertNotIn("<svg", own)

    def test_an_icon_circle_colour_puts_every_icon_in_a_round_badge(self):
        # icons in the same colour as the text blended in on a brand-colour band (Harsh, 10 Oct 2026)
        html = render(self.m, {"f1_title": "A", "f1_icon": "leaf", "icon_bg": "#FFFFFF"})
        self.assertIn("dtj-fs--chip", html)
        self.assertIn("--fs-ib: #FFFFFF", html)
        plain = render(self.m, {"f1_title": "A", "f1_icon": "leaf"})
        self.assertNotIn("dtj-fs--chip", plain)
        self.assertNotIn("--fs-ib", plain)
        css = (HERE / "extensions/dtj-sections-2/assets/dtj-feature-showcase.css").read_text(encoding="utf-8")
        self.assertIn(".dtj-fs--chip .dtj-fs__icon", css)
        self.assertIn("border-radius: 50%", css)

    def test_nothing_is_claimed_by_default(self):
        html = render(self.m, {"f1_title": "A"})
        self.assertNotIn("dtj-fs__heading", html)
        self.assertNotIn("dtj-fs__sub", html)
        self.assertNotIn("dtj-fs__text", html)

    def test_the_heading_tag_is_a_safe_choice_and_titles_follow_it(self):
        self.assertIn("<h2 class=\"dtj-fs__heading\">", render(self.m, {"heading": "H", "f1_title": "A"}))
        self.assertIn("<h3 class=\"dtj-fs__title\">", render(self.m, {"heading": "H", "f1_title": "A"}))
        h3 = render(self.m, {"heading": "H", "heading_tag": "h3", "f1_title": "A"})
        self.assertIn("<h3 class=\"dtj-fs__heading\">", h3)
        self.assertIn("<p class=\"dtj-fs__title\">", h3)  # no skipped or repeated heading levels
        self.assertIn("<h2 class=\"dtj-fs__heading\">", render(self.m, {"heading": "H", "heading_tag": "script", "f1_title": "A"}))

    def test_text_is_escaped(self):
        html = render(self.m, {"heading": "<script>", "subheading": "<script>", "f1_title": "<script>", "f1_text": "<script>"})
        self.assertNotIn("<script>", html)

    def test_phone_choices_become_classes_and_variables(self):
        html = render(self.m, {"f1_title": "A", "mobile_image": "bottom", "mobile_columns": "1"})
        self.assertIn("dtj-fs--img-last", html)
        self.assertIn("--fs-mc: 1;", html)
        self.assertIn("--fs-mc: 2;", render(self.m, {"f1_title": "A"}))



@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class SplitStoryTests(unittest.TestCase):
    m = manifest("split-story")

    def test_the_check_mark_can_take_its_own_colour_for_light_markers(self):
        # a white check vanished on a yellow marker inside a navy card (Go Mints v3, 10 Oct 2026)
        html = render(self.m, {"heading": "A", "bullet_1": "x", "tick_color": "#082A45"})
        self.assertIn("--ss-tick-c: #082A45", html)
        self.assertNotIn("--ss-tick-c", render(self.m, {"heading": "A", "bullet_1": "x"}))
        css = (HERE / "extensions/dtj-sections-2/assets/dtj-split-story.css").read_text(encoding="utf-8")
        self.assertIn("color: var(--ss-tick-c, Canvas)", css)

    def test_nothing_renders_empty_and_nothing_is_claimed_by_default(self):
        self.assertEqual(render(self.m, {}), "")
        html = render(self.m, {"heading": "H"})
        for part in ("dtj-ss__review", "dtj-ss__stars", "dtj-ss__points", "dtj-ss__body", "dtj-ss__media"):
            self.assertNotIn(part, html)

    def test_the_heading_has_two_parts_with_a_space_between_and_one_tag(self):
        html = render(self.m, {"heading": "First", "heading_accent": "Second"})
        self.assertEqual(html.count("<h2"), 1)
        self.assertIn("</span> <span class=\"dtj-ss__h2\">", html)
        self.assertNotIn(" <span class=\"dtj-ss__h2\">", render(self.m, {"heading_accent": "Only second"}).replace("<span class=\"dtj-ss__h2\">Only", "").replace("</span>", ""))

    def test_up_to_five_points_each_needs_text(self):
        html = render(self.m, {**{f"bullet_{i}": f"Point {i}" for i in range(1, 8)}, "bullet_2": ""})
        self.assertEqual(html.count('class="dtj-ss__point"'), 4)

    def test_the_review_card_needs_a_review_or_a_name(self):
        self.assertNotIn("dtj-ss__review", render(self.m, {"heading": "H", "review_stars": "5"}))
        self.assertIn("dtj-ss__review", render(self.m, {"review_text": "A review"}))
        self.assertIn("dtj-ss__review", render(self.m, {"review_name": "A name"}))

    def test_stars_are_exactly_the_chosen_rating_and_none_by_default(self):
        base = {"review_text": "R", "review_name": "N"}
        self.assertNotIn("dtj-ss__stars", render(self.m, base))
        for n in (1, 3, 5):
            html = render(self.m, {**base, "review_stars": str(n)})
            self.assertEqual(html.count("<path d=\"M12 2l2.9"), n)

    def test_the_photo_and_avatar_are_optional(self):
        self.assertIn("dtj-ss__avatar", render(self.m, {"review_text": "R", "review_image": "pic"}))
        self.assertNotIn("dtj-ss__avatar", render(self.m, {"review_text": "R"}))
        self.assertIn("dtj-ss__card--noimg", render(self.m, {"heading": "H"}))
        self.assertIn("dtj-ss__card--notext", render(self.m, {"image": "pic"}))

    def test_adapt_shows_the_whole_picture_and_fill_stays_the_default(self):
        # Harsh, 9 Oct 2026, on the live book page: "make it adapt to the image size, the image is getting trimmed"
        pic = {"width": 1080, "height": 1350, "alt": "cover"}
        fill = render(self.m, {"heading": "H", "image": pic})
        self.assertNotIn("dtj-ss__card--adapt", fill)
        self.assertNotIn("--ss-img-ratio", fill)  # existing pages keep their look
        adapt = render(self.m, {"heading": "H", "image": pic, "image_fit": "adapt"})
        self.assertIn("dtj-ss__card--adapt", adapt)
        self.assertIn("--ss-img-ratio: 1080 / 1350;", adapt)  # the picture's own shape
        self.assertNotIn("dtj-ss__card--adapt", render(self.m, {"heading": "H", "image_fit": "adapt"}))  # no picture, nothing to adapt
        css = (HERE / "src" / "split-story.css").read_text(encoding="utf-8")
        self.assertIn(".dtj-ss__card--adapt .dtj-ss__img { object-fit: contain; }", css)  # never cropped
        self.assertIn(".dtj-ss__card--adapt .dtj-ss__media { min-height: 0; aspect-ratio: var(--ss-img-ratio, 4 / 3); }", css)

    def test_the_image_side_the_focus_and_the_phone_shape_are_safe_choices(self):
        self.assertIn("dtj-ss__card--flip", render(self.m, {"heading": "H", "image_side": "end"}))
        self.assertNotIn("dtj-ss__card--flip", render(self.m, {"heading": "H", "image_side": "start"}))
        self.assertIn("--ss-focus: top;", render(self.m, {"heading": "H", "image_focus": "top"}))
        self.assertIn("--ss-focus: center;", render(self.m, {"heading": "H", "image_focus": "evil;"}))
        self.assertIn("--ss-ratio: 1 / 1;", render(self.m, {"heading": "H", "image_ratio_mobile": "1 / 1"}))
        self.assertIn("<h2", render(self.m, {"heading": "H", "heading_tag": "script"}))

    def test_text_is_escaped(self):
        html = render(self.m, {"heading": "<script>", "heading_accent": "<script>", "body": "<script>", "bullet_1": "<script>",
                               "review_text": "<script>", "review_name": "<script>"})
        self.assertNotIn("<script>", html)


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class StatCardsTests(unittest.TestCase):
    m = manifest("stat-cards")

    def test_nothing_renders_empty_and_nothing_is_claimed_by_default(self):
        self.assertEqual(render(self.m, {}), "")
        html = render(self.m, {"heading": "H"})
        for part in ("dtj-sc__card", "dtj-sc__number", "dtj-sc__note", "dtj-sc__grid"):
            self.assertNotIn(part, html)

    def test_a_card_shows_when_it_has_a_figure_a_line_or_a_footnote(self):
        html = render(self.m, {"number_1": "1", "label_2": "only a line", "note_3": "only a note", "number_5": ""})
        self.assertEqual(html.count('class="dtj-sc__card"'), 3)

    def test_up_to_six_cards(self):
        self.assertEqual(render(self.m, {f"number_{i}": f"N{i}" for i in range(1, 9)}).count('class="dtj-sc__card"'), 6)

    def test_columns_follow_the_number_of_cards_up_to_four_then_three(self):
        for n, cols in ((1, 1), (3, 3), (4, 4), (5, 3), (6, 3)):
            html = render(self.m, {f"number_{i}": f"N{i}" for i in range(1, n + 1)})
            self.assertIn(f"--sc-cols: {cols};", html, f"{n} cards")
        self.assertIn("--sc-cols: 2;", render(self.m, {"number_1": "A", "number_2": "B", "number_3": "C", "columns": "2"}))
        self.assertIn("--sc-cols: 3;", render(self.m, {"number_1": "A", "columns": "evil"}) .replace("--sc-cols: 1;", "--sc-cols: 3;"))

    def test_the_heading_has_two_parts_with_a_space_between_one_tag_and_an_optional_underline(self):
        html = render(self.m, {"heading": "First", "heading_accent": "Second", "underline": True})
        self.assertEqual(html.count("<h2"), 1)
        self.assertIn("</span> <span class=\"dtj-sc__accent\">", html)
        self.assertIn("dtj-sc__underline", html)
        self.assertNotIn("dtj-sc__underline", render(self.m, {"heading": "First", "heading_accent": "Second", "underline": False}))
        self.assertNotIn("dtj-sc__underline", render(self.m, {"heading": "First", "underline": True}))  # nothing to underline

    def test_the_phone_layout_and_the_shadow_are_options(self):
        base = {"number_1": "A"}
        self.assertIn("dtj-sc--swipe", render(self.m, {**base, "mobile_layout": "swipe"}))
        self.assertNotIn("dtj-sc--swipe", render(self.m, {**base, "mobile_layout": "stack"}))
        self.assertIn("dtj-sc--shadow", render(self.m, {**base, "card_shadow": True}))
        self.assertNotIn("dtj-sc--shadow", render(self.m, {**base, "card_shadow": False}))

    def test_the_heading_tag_is_a_safe_choice(self):
        self.assertIn("<h3", render(self.m, {"heading": "H", "heading_tag": "h3"}))
        self.assertIn("<h2", render(self.m, {"heading": "H", "heading_tag": "script"}))

    def test_text_is_escaped(self):
        html = render(self.m, {"heading": "<script>", "heading_accent": "<script>", "number_1": "<script>", "label_1": "<script>", "note_1": "<script>"})
        self.assertNotIn("<script>", html)


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class MeasuredResultsTests(unittest.TestCase):
    m = manifest("measured-results")

    def test_nothing_renders_empty_and_no_claim_is_shipped_by_default(self):
        self.assertEqual(render(self.m, {}), "")
        html = render(self.m, {"heading": "H"})
        for part in ("dtj-mr__row", "dtj-mr__card", "dtj-mr__note", "dtj-mr__figure"):
            self.assertNotIn(part, html)

    def test_a_row_shows_when_it_has_a_figure_a_title_or_a_text(self):
        html = render(self.m, {"figure_1": "1", "title_2": "only a title", "text_3": "only a text", "figure_5": ""})
        self.assertEqual(html.count('class="dtj-mr__row"'), 3)

    def test_up_to_five_rows(self):
        self.assertEqual(render(self.m, {f"figure_{i}": f"F{i}" for i in range(1, 9)}).count('class="dtj-mr__row"'), 5)

    def test_both_headings_have_two_parts_with_a_space_between_them(self):
        html = render(self.m, {"heading": "First", "heading_accent": "Second", "card_heading": "Card", "card_heading_accent": "Italic"})
        self.assertEqual(html.count("<h2"), 1)
        self.assertRegex(html, r"First</span> <span[^>]*>Second")
        self.assertRegex(html, r"Card</span> <em>Italic")

    def test_heading_tag_only_allows_known_tags(self):
        self.assertIn("<h3", render(self.m, {"heading": "H", "heading_tag": "h3"}))
        self.assertIn("<h2", render(self.m, {"heading": "H", "heading_tag": "script"}))

    def test_card_only_and_side_only_each_render_without_the_other(self):
        card = render(self.m, {"card_figure": "48h"})
        self.assertIn("dtj-mr__card", card)
        self.assertNotIn("dtj-mr__side", card)
        self.assertIn("dtj-mr--single", card)
        side = render(self.m, {"figure_1": "5 sec"})
        self.assertIn("dtj-mr__side", side)
        self.assertNotIn("dtj-mr__card", side)

    def test_picture_shows_only_when_set_and_is_decorative(self):
        self.assertNotIn("<img", render(self.m, {"card_figure": "1"}))
        html = render(self.m, {"image": "photo-file"})
        self.assertIn("dtj-mr__img", html)
        self.assertIn('alt=""', html)

    def test_picture_sits_below_the_text_unless_overlay_is_chosen(self):
        html = render(self.m, {"card_heading": "Card", "image": "photo-file"})
        self.assertNotIn("dtj-mr__card--over", html)
        self.assertLess(html.index("dtj-mr__card-text"), html.index("dtj-mr__img"))  # text first, picture after it: they never overlap
        over = render(self.m, {"card_heading": "Card", "image": "photo-file", "image_overlay": True, "card_scrim": True})
        self.assertIn("dtj-mr__card--over", over)
        self.assertIn("dtj-mr__card--scrim", over)
        self.assertNotIn("dtj-mr__card--scrim", render(self.m, {"card_heading": "Card", "image": "photo-file", "card_scrim": True}))  # a haze only makes sense over the picture

    def test_footnote_has_an_icon_and_is_escaped(self):
        html = render(self.m, {"footnote": "<b>Source</b>"})
        self.assertIn("dtj-mr__note-icon", html)
        self.assertIn("&lt;b&gt;Source&lt;/b&gt;", html)

    def test_colours_are_set_only_when_chosen(self):
        plain = render(self.m, {"heading": "H"})
        for var in ("--mr-accent", "--mr-card-color", "--mr-card-accent", "--mr-card-bg"):
            self.assertNotIn(var, plain)
        html = render(self.m, {"heading": "H", "accent_color": "rgb(1, 2, 3)", "card_text_color": "rgb(4, 5, 6)"})
        self.assertIn("--mr-accent: rgb(1, 2, 3)", html)
        self.assertIn("--mr-card-color: rgb(4, 5, 6)", html)


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class SideSpaceTests(unittest.TestCase):
    """Every full-width section keeps off the screen edges by default (16 px a side) and the merchant can change it."""

    def test_default_is_16px_each_side_and_it_can_be_changed(self):
        for block in ("stat-cards", "split-story", "feature-showcase", "measured-results"):
            m = manifest(block)
            html = render(m, m["test"]["sample"])
            self.assertIn("--dtj-pad-left: 16px; --dtj-pad-right: 16px;", html, block)
            self.assertIn("--dtj-pad-left: 4px; --dtj-pad-right: 4px;", render(m, {**m["test"]["sample"], "side_padding": 4}), block)
            self.assertIn("--dtj-pad-left: 0px; --dtj-pad-right: 0px;", render(m, {**m["test"]["sample"], "side_padding": 0}), block)


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class SlideshowProTests(unittest.TestCase):
    m = manifest("slideshow-pro")

    def two(self, **extra):
        return {"heading_1": "One", "heading_2": "Two", **extra}

    def test_nothing_renders_empty_and_no_copy_is_shipped_by_default(self):
        self.assertEqual(render(self.m, {}), "")
        html = render(self.m, {"heading_1": "H"})
        for part in ("dtj-sl__rating", "dtj-sl__chips", "dtj-sl__btn", "dtj-sl__note", "dtj-sl__eyebrow", "dtj-sl__desc"):
            self.assertNotIn(part, html)

    def test_a_slide_shows_when_it_has_anything_and_there_are_at_most_three(self):
        self.assertEqual(render(self.m, {"heading_1": "A", "chips_2": "x", "image_3": "pic", "heading_4": "ignored"}).count('class="dtj-sl__slide'), 3)
        self.assertEqual(render(self.m, {"heading_2": "only the second"}).count('class="dtj-sl__slide'), 1)

    def test_only_the_first_slide_is_active_and_the_others_are_hidden_from_everyone(self):
        html = render(self.m, self.two())
        self.assertEqual(html.count("is-active"), 1)
        self.assertEqual(html.count("inert"), 1)
        self.assertIn('aria-label="1 / 2"', html)

    def test_arrows_only_with_two_or_more_slides_and_never_when_hidden(self):
        self.assertEqual(render(self.m, self.two()).count("dtj-sl__arrow "), 2)
        self.assertNotIn("dtj-sl__arrow", render(self.m, {"heading_1": "Solo"}))
        self.assertNotIn("dtj-sl__arrow", render(self.m, self.two(arrows_position="none")))
        single = render(self.m, {"heading_1": "Solo"})
        self.assertIn("dtj-sl--single", single)
        self.assertIn('data-auto="false"', single)

    def test_autoplay_needs_two_slides_and_can_be_switched_off(self):
        self.assertIn("dtj-sl--auto", render(self.m, self.two()))
        self.assertIn('data-auto="true"', render(self.m, self.two()))
        self.assertNotIn("dtj-sl--auto", render(self.m, self.two(autoplay=False)))
        self.assertIn("--sl-dur: 9s", render(self.m, self.two(autoplay_seconds=9)))

    def test_heading_accent_words_sit_between_asterisks_and_are_escaped(self):
        html = render(self.m, {"heading_1": "A calming *botanical* reset"})
        self.assertRegex(html, r'<span>A calming </span><em class="dtj-sl__accent">botanical</em><span> reset</span>')
        self.assertIn("&lt;b&gt;", render(self.m, {"heading_1": "x *<b>*"}))
        self.assertNotIn("dtj-sl__accent", render(self.m, {"heading_1": "No accent here"}))

    def test_chips_one_per_line_up_to_four_with_an_optional_known_icon(self):
        html = render(self.m, {"heading_1": "H", "chips_1": "leaf: One\nTwo\n\nunknown: Three\nFour\nFive"})
        self.assertEqual(html.count('dtj-sl__chip"'), 4)
        self.assertEqual(html.count("dtj-sl__icon"), 1)  # only the known icon is drawn
        self.assertIn("<span>One</span>", html)
        self.assertIn("<span>unknown: Three</span>", html)  # an unknown key is just text
        self.assertNotIn("Five", html)

    def test_note_takes_an_optional_icon_and_a_colon_in_the_text_survives(self):
        html = render(self.m, {"heading_1": "H", "note_1": "shield: Open 9:00 daily"})
        self.assertIn("dtj-sl__icon", html)
        self.assertIn("<span>Open 9:00 daily</span>", html)
        self.assertNotIn("dtj-sl__icon", render(self.m, {"heading_1": "H", "note_1": "Plain note"}))

    def test_button_is_a_link_only_with_a_url_and_the_arrow_is_optional(self):
        self.assertIn('<a class="dtj-sl__btn" href="/shop">', render(self.m, {"heading_1": "H", "button_label_1": "Go", "button_url_1": "/shop"}))
        self.assertIn('<span class="dtj-sl__btn">', render(self.m, {"heading_1": "H", "button_label_1": "Go"}))
        self.assertNotIn("dtj-sl__btn", render(self.m, {"heading_1": "H", "button_url_1": "/shop"}))
        self.assertNotIn("dtj-sl__btn-arrow", render(self.m, {"heading_1": "H", "button_label_1": "Go"}))
        self.assertIn("dtj-sl__btn-arrow", render(self.m, {"heading_1": "H", "button_label_1": "Go", "button_arrow": True}))

    def test_rating_shows_five_stars_with_its_text_only_when_typed(self):
        html = render(self.m, {"heading_1": "H", "rating_1": "Rated by us"})
        self.assertEqual(html.count('<svg viewBox="0 0 24 24" focusable="false">'), 5)
        self.assertIn("Rated by us", html)
        self.assertIn("dtj-sl--rating-plain", html)
        self.assertIn("dtj-sl--rating-chip", render(self.m, {"heading_1": "H", "rating_style": "chip"}))

    def test_aspect_ratio_fixed_or_adapting_to_the_first_picture(self):
        self.assertIn("--sl-rd: 3 / 2;", render(self.m, {"heading_1": "H"}))
        self.assertIn("--sl-rd: 16 / 9;", render(self.m, {"heading_1": "H", "ratio_desktop": "16 / 9"}))
        pic = {"aspect_ratio": 1.25, "width": 1000, "height": 800, "alt": ""}
        adapt = render(self.m, {"image_1": pic, "ratio_desktop": "adapt", "ratio_mobile": "adapt"})
        self.assertIn("--sl-rd: 1.25;", adapt)
        self.assertIn("--sl-rm: 1.25;", adapt)
        self.assertIn("--sl-rd: 3 / 2;", render(self.m, {"heading_1": "H", "ratio_desktop": "adapt"}))  # nothing to adapt to: the default shape

    def test_pictures_are_responsive_first_is_eager_and_alt_comes_from_the_picture(self):
        pic = {"aspect_ratio": 1.0, "width": 1000, "height": 1000, "alt": 'A "quoted" alt'}
        html = render(self.m, {"image_1": pic, "image_2": pic})
        self.assertEqual(html.count("srcset="), 2)
        self.assertEqual(html.count('loading="eager"'), 1)
        self.assertEqual(html.count('loading="lazy"'), 1)
        self.assertIn("&quot;quoted&quot;", html)
        self.assertIn('width="1000" height="1000"', html)

    def test_look_choices_become_classes_and_unknown_content_position_falls_back(self):
        html = render(self.m, self.two(content_position="right", overlay_style="solid", transition="fade", arrows_position="edges",
                                       chip_style="glass", button_style="square", accent_font="bold", heading_font="serif", eyebrow_style="mono"))
        for cls in ("pos-right", "ov-solid", "tr-fade", "arrows-edges", "chips-glass", "btn-square", "accent-bold", "hf-serif", "eyebrow-mono"):
            self.assertIn(f"dtj-sl--{cls}", html)
        self.assertIn("dtj-sl--pos-left", render(self.m, {"heading_1": "H", "content_position": "evil"}))

    def test_colours_are_set_only_when_chosen(self):
        plain = render(self.m, {"heading_1": "H"})
        for var in ("--sl-ov-c", "--sl-accent", "--sl-star", "--sl-btn-bg", "--sl-btn-c", "--sl-ab", "--sl-ac", "--sl-pc"):
            self.assertNotIn(var, plain)
        html = render(self.m, {"heading_1": "H", "overlay_color": "rgb(1, 2, 3)", "accent_color": "rgb(4, 5, 6)", "button_bg": "rgb(7, 8, 9)"})
        for var, val in (("--sl-ov-c", "rgb(1, 2, 3)"), ("--sl-accent", "rgb(4, 5, 6)"), ("--sl-btn-bg", "rgb(7, 8, 9)")):
            self.assertIn(f"{var}: {val}", html)

    def test_overlay_numbers_reach_the_css(self):
        html = render(self.m, {"heading_1": "H", "overlay_opacity": 40, "overlay_size": 55, "overlay_blur": 12, "content_width": 500})
        for part in ("--sl-ov-pct: 40%", "--sl-ov-size: 55%", "--sl-blur: 12px", "--sl-cw: 500px"):
            self.assertIn(part, html)

    def test_the_slider_stays_within_75_settings(self):
        settings = tg.cl.extract_schema(tg.block_text(self.m))["settings"]
        self.assertLessEqual(len([s for s in settings if s.get("type") not in ("header", "paragraph")]), 75)


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class CtaTests(unittest.TestCase):
    m = manifest("cta")
    ON_SALE = {"selected_or_first_available_variant": {"id": 4242, "available": True}}
    SOLD_OUT = {"selected_or_first_available_variant": {"id": 4242, "available": False}}

    def test_a_button_needs_only_a_label_and_scrolls_to_the_buy_button_by_default(self):
        html = render(self.m, {"button_label": "Get my pack"}, product={})
        self.assertIn("data-dtj-cta-scroll", html)
        self.assertIn("Get my pack", html)
        self.assertNotIn("dtj-cta__heading", html)

    def test_the_button_style_never_shows_banner_words(self):
        html = render(self.m, {"button_label": "Go", "heading": "Hidden heading", "text": "Hidden text", "seal_text": "SEAL"}, product={})
        for word in ("Hidden heading", "Hidden text", "SEAL"):
            self.assertNotIn(word, html)

    def test_a_banner_shows_seal_heading_and_terms_and_may_have_no_button(self):
        html = render(self.m, {"style": "banner", "heading": "Love it or your money back", "text": "30 days.\nNo questions.", "seal_text": "30-day promise"}, product={})
        self.assertIn("dtj-cta--banner", html)
        self.assertIn("Love it or your money back", html)
        self.assertIn("30 days.<br", html)
        self.assertIn("30-day promise", html)
        self.assertNotIn("dtj-cta__btn", html)

    def test_add_to_cart_posts_the_available_variant_and_a_sold_out_product_falls_back_to_scrolling(self):
        html = render(self.m, {"button_label": "Add", "action": "cart"}, product=self.ON_SALE)
        self.assertIn('name="id" value="4242"', html)
        self.assertNotIn("data-dtj-cta-scroll", html)
        html = render(self.m, {"button_label": "Add", "action": "cart"}, product=self.SOLD_OUT)
        self.assertNotIn('name="id"', html)
        self.assertIn("data-dtj-cta-scroll", html)

    def test_a_link_opens_the_link_and_an_empty_link_falls_back_to_scrolling(self):
        self.assertIn('href="/pages/guarantee"', render(self.m, {"button_label": "Read", "action": "link", "link": "/pages/guarantee"}, product={}))
        self.assertIn("data-dtj-cta-scroll", render(self.m, {"button_label": "Read", "action": "link"}, product={}))

    def test_button_shape_and_colours_are_settings_not_hard_coded(self):
        html = render(self.m, {"button_label": "Go", "button_style": "square", "button_bg": "#E9EF12", "button_color": "#082A45"}, product={})
        self.assertIn("dtj-cta__btn--square", html)
        self.assertIn("--cta-bg: #E9EF12;", html)
        self.assertIn("--cta-fg: #082A45;", html)
        self.assertIn("dtj-cta__btn--pill", render(self.m, {"button_label": "Go", "button_style": "weird"}, product={}))

    def test_the_script_stays_small_and_respects_reduced_motion(self):
        js = (HERE / "src" / "cta.js").read_text(encoding="utf-8")
        self.assertLess(len(js.encode()), 10000)
        self.assertIn("prefers-reduced-motion", js)
