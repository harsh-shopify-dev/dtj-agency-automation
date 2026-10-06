"""Tests for what is specific to the four DTJ Sections blocks (the generic ones, licence / escaping / defaults, live in
services/block-library/tests/test_generated_blocks.py and run against this app with DTJ_APP_ROOT set).

    cd services/block-library-sections
    DTJ_APP_ROOT=$PWD ../../.work/.venv/Scripts/python -m unittest discover -s tests -t .
"""
import json
import os
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
class WhatsInsideTests(unittest.TestCase):
    m = manifest("whats-inside")

    def test_a_card_only_shows_when_it_has_a_name(self):
        html = render(self.m, {"name_1": "One", "description_2": "no name here", "dose_2": "5 mg"})
        self.assertEqual(html.count("<article"), 1)
        self.assertNotIn("no name here", html)

    def test_at_most_six_cards_and_four_benefits_each(self):
        sample = {f"name_{i}": f"Item {i}" for i in range(1, 7)}
        sample["benefits_1"] = "\n".join(f"Benefit {n}" for n in range(1, 9))
        html = render(self.m, sample)
        self.assertEqual(html.count("<article"), 6)
        self.assertEqual(html.count("<li"), 4)
        self.assertNotIn("Benefit 5", html)

    def test_the_highlighted_part_is_wrapped_only_when_it_is_in_the_heading(self):
        self.assertIn('<span class="dtj-wi__hl">it does</span>', render(self.m, {"heading": "What it does", "highlight_word": "it does"}))
        self.assertNotIn("dtj-wi__hl", render(self.m, {"heading": "Something else", "highlight_word": "missing"}))

    def test_heading_and_names_are_escaped(self):
        html = render(self.m, {"heading": "<script>x</script>", "name_1": "<b>bold</b>"})
        self.assertNotIn("<script>", html)
        self.assertNotIn("<b>bold</b>", html)

    def test_columns_fall_back_to_three_for_unknown_values(self):
        self.assertIn("--wi-cols: 3;", render(self.m, {"name_1": "A", "columns": "9"}))
        self.assertIn("--wi-cols: 2;", render(self.m, {"name_1": "A", "columns": "2"}))

    def test_image_and_dose_are_optional(self):
        html = render(self.m, {"name_1": "A"})
        self.assertNotIn("<img", html)
        self.assertNotIn("dtj-wi__dose", html)
        self.assertIn("<img", render(self.m, {"name_1": "A", "image_1": "pic"}))


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class NotInsideTests(unittest.TestCase):
    m = manifest("whats-not-inside")

    def test_an_item_only_shows_when_it_has_a_name(self):
        self.assertEqual(render(self.m, {"name_1": "A", "image_2": "pic"}).count("dtj-wni__item"), 1)

    def test_up_to_twelve_items(self):
        sample = {f"name_{i}": f"Item {i}" for i in range(1, 13)}
        self.assertEqual(render(self.m, sample).count("dtj-wni__item"), 12)

    def test_the_underlined_word_is_wrapped_only_when_it_is_in_the_heading(self):
        self.assertIn('<em class="dtj-wni__em">not</em>', render(self.m, {"heading": "What is not inside", "highlight_word": "not"}))
        self.assertNotIn("dtj-wni__em", render(self.m, {"heading": "What is inside", "highlight_word": "not"}))

    def test_the_cross_badge_and_frame_are_options(self):
        self.assertIn("dtj-wni__x", render(self.m, {"name_1": "A", "show_x": True}))
        self.assertNotIn("dtj-wni__x", render(self.m, {"name_1": "A", "show_x": False}))
        self.assertIn("dtj-wni--frame-circle", render(self.m, {"name_1": "A", "frame_style": "circle"}))
        self.assertIn("dtj-wni--frame-none", render(self.m, {"name_1": "A", "frame_style": "bogus"}))


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class FaqTests(unittest.TestCase):
    m = manifest("faq")

    def test_a_question_only_shows_when_it_has_text(self):
        html = render(self.m, {"question_1": "Q one?", "answer_2": "orphan answer"})
        self.assertEqual(html.count("<details"), 1)
        self.assertNotIn("orphan answer", html)

    def test_up_to_ten_questions_and_answers_keep_their_formatting(self):
        sample = {f"question_{i}": f"Q{i}" for i in range(1, 11)}
        sample["answer_1"] = "<p>Answer with <strong>bold</strong></p>"
        html = render(self.m, sample)
        self.assertEqual(html.count("<details"), 10)
        self.assertIn("<strong>bold</strong>", html)

    def test_questions_are_escaped(self):
        self.assertNotIn("<script>", render(self.m, {"question_1": "<script>x</script>"}))

    def test_only_the_first_question_opens_by_default_when_asked(self):
        sample = {"question_1": "A", "question_2": "B"}
        self.assertEqual(render(self.m, {**sample, "first_open": True}).count(" open"), 1)
        self.assertEqual(render(self.m, {**sample, "first_open": False}).count(" open"), 0)

    def test_pills_need_the_switch_and_at_least_one_category(self):
        base = {"question_1": "A", "category_1": "Shipping"}
        self.assertIn("dtj-faq__pill", render(self.m, {**base, "show_filters": True}))
        self.assertNotIn("dtj-faq__pill", render(self.m, {**base, "show_filters": False}))
        self.assertNotIn("dtj-faq__pill", render(self.m, {"question_1": "A", "show_filters": True}))

    def test_the_all_pill_has_a_neutral_fallback_label_and_every_item_carries_its_category(self):
        html = render(self.m, {"question_1": "A", "category_2": "Usage", "cat_1": "2", "show_filters": True})
        self.assertIn("<span>All</span>", html)
        self.assertIn('data-cat="2"', html)
        self.assertIn(">Usage<", html)


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class ComparisonTableTests(unittest.TestCase):
    m = manifest("comparison-table")

    def test_a_row_shows_when_either_side_has_text(self):
        html = render(self.m, {"our_1": "ours only", "other_2": "theirs only"})
        self.assertEqual(html.count("<tr>"), 2)  # two body rows, no header row (no labels or images)

    def test_nothing_renders_without_any_row(self):
        self.assertEqual(render(self.m, {"heading": "Only a heading"}), "")

    def test_the_header_row_needs_a_label_or_an_image(self):
        self.assertNotIn("<thead", render(self.m, {"our_1": "A"}))
        self.assertIn("<thead", render(self.m, {"our_1": "A", "our_label": "Ours"}))

    def test_up_to_eight_rows(self):
        sample = {f"our_{i}": f"Row {i}" for i in range(1, 9)}
        self.assertEqual(render(self.m, sample).count("<tr>"), 8)

    def test_marks_and_highlight_are_options(self):
        base = {"our_1": "A", "other_1": "B"}
        self.assertIn("dtj-cmp__yes", render(self.m, {**base, "show_marks": True}))
        self.assertNotIn("dtj-cmp__yes", render(self.m, {**base, "show_marks": False}))
        self.assertIn("dtj-cmp--hl", render(self.m, {**base, "highlight_ours": True}))
        self.assertNotIn("dtj-cmp--hl", render(self.m, {**base, "highlight_ours": False}))

    def test_rich_text_cells_keep_their_formatting(self):
        self.assertIn("<strong>big</strong>", render(self.m, {"our_1": "a <strong>big</strong> win"}))


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class MarqueeTests(unittest.TestCase):
    m = manifest("marquee")

    def test_items_need_text_and_the_list_is_shown_twice_for_a_seamless_loop(self):
        html = render(self.m, {"text_1": "One", "image_2": "pic", "text_3": "Three"})
        self.assertEqual(html.count("One"), 2)
        self.assertEqual(html.count("Three"), 2)
        self.assertEqual(html.count('<div class="dtj-mq__set"'), 2)
        self.assertEqual(html.count('<div class="dtj-mq__set" aria-hidden="true">'), 1)  # only the copy is hidden from screen readers

    def test_up_to_ten_items(self):
        self.assertEqual(render(self.m, {f"text_{i}": f"Item {i}" for i in range(1, 11)}).count("dtj-mq__item"), 20)

    def test_icon_is_the_picture_else_the_tick_else_nothing(self):
        self.assertIn("dtj-mq__icon", render(self.m, {"text_1": "A", "image_1": "pic"}))
        self.assertIn("dtj-mq__tick", render(self.m, {"text_1": "A", "show_default_icon": True}))
        html = render(self.m, {"text_1": "A", "show_default_icon": False})
        self.assertNotIn("dtj-mq__tick", html)
        self.assertNotIn("dtj-mq__icon", html)

    def test_options_become_classes(self):
        html = render(self.m, {"text_1": "A", "pause_on_hover": True, "uppercase": True})
        self.assertIn("dtj-mq--pause", html)
        self.assertIn("dtj-mq--upper", html)
        self.assertNotIn("dtj-mq--pause", render(self.m, {"text_1": "A", "pause_on_hover": False}))

    def test_items_are_escaped(self):
        self.assertNotIn("<script>", render(self.m, {"text_1": "<script>x</script>"}))


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class StoriesTests(unittest.TestCase):
    m = manifest("stories")

    def test_a_card_only_shows_when_it_has_a_name(self):
        html = render(self.m, {"name_1": "A", "quote_2": "orphan quote"})
        self.assertEqual(html.count("<article"), 1)
        self.assertNotIn("orphan quote", html)

    def test_up_to_six_cards_and_three_tags(self):
        sample = {f"name_{i}": f"Person {i}" for i in range(1, 7)}
        sample.update({"tag_1_1": "T1", "tag_1_2": "T2", "tag_1_3": "T3"})
        html = render(self.m, sample)
        self.assertEqual(html.count("<article"), 6)
        self.assertEqual(html.count('class="dtj-st__tag"'), 3)

    def test_the_badge_text_comes_only_from_the_merchant_so_nothing_is_claimed_by_default(self):
        self.assertNotIn("dtj-st__badge", render(self.m, {"name_1": "A"}))
        self.assertIn(">Mine<", render(self.m, {"name_1": "A", "verified_label": "Mine"}).replace("</svg>", ">").replace(">>", ">"))

    def test_no_invented_star_line(self):
        self.assertNotIn("<svg", render(self.m, {"name_1": "A", "proof_line": "A line of my own", "heading": "H"}).split("<article")[0])

    def test_the_button_needs_text_and_gets_a_safe_default_link(self):
        self.assertNotIn("dtj-st__cta", render(self.m, {"name_1": "A"}))
        self.assertIn('href="#"', render(self.m, {"name_1": "A", "cta_text": "Go"}))
        self.assertIn('href="/shop"', render(self.m, {"name_1": "A", "cta_text": "Go", "cta_url": "/shop"}))

    def test_quotes_and_names_are_escaped(self):
        self.assertNotIn("<script>", render(self.m, {"name_1": "<script>", "quote_1": "<script>"}))


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class TestimonialsSliderTests(unittest.TestCase):
    m = manifest("testimonials-slider")

    def test_a_review_only_shows_when_it_has_text(self):
        html = render(self.m, {"text_1": "Real review", "author_2": "orphan author"})
        self.assertEqual(html.count("<figure"), 1)
        self.assertNotIn("orphan author", html)

    def test_up_to_eight_reviews(self):
        self.assertEqual(render(self.m, {f"text_{i}": f"Review {i}" for i in range(1, 10)}).count("<figure"), 8)

    def test_no_stars_unless_chosen_never_an_invented_five(self):
        self.assertNotIn("dtj-ts__stars", render(self.m, {"text_1": "A"}))
        html = render(self.m, {"text_1": "A", "stars_1": "3"})
        self.assertIn("dtj-ts__stars", html)
        self.assertEqual(html.count('fill="currentColor"'), 3)  # 3 filled, 2 outlined

    def test_cards_in_view_fall_back_to_sane_values(self):
        self.assertIn("--ts-per: 3;", render(self.m, {"text_1": "A", "per_view": "9"}))
        self.assertIn("--ts-per: 2;", render(self.m, {"text_1": "A", "per_view": "2"}))
        self.assertIn("--ts-per-m: 1;", render(self.m, {"text_1": "A", "per_view_mobile": "5"}))

    def test_controls_exist_only_with_more_than_one_review_and_when_switched_on(self):
        self.assertNotIn("data-nav", render(self.m, {"text_1": "A", "show_arrows": True}))
        self.assertIn("data-prev", render(self.m, {"text_1": "A", "text_2": "B", "show_arrows": True, "show_dots": False}))
        self.assertNotIn("data-dots", render(self.m, {"text_1": "A", "text_2": "B", "show_arrows": True, "show_dots": False}))
        self.assertNotIn("data-nav", render(self.m, {"text_1": "A", "text_2": "B", "show_arrows": False, "show_dots": False}))

    def test_reviews_are_escaped(self):
        self.assertNotIn("<script>", render(self.m, {"text_1": "<script>x</script>", "author_1": "<script>"}))


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class ScienceStatsTests(unittest.TestCase):
    m = manifest("science-stats")

    def test_a_card_only_shows_when_it_has_a_number(self):
        html = render(self.m, {"number_1": "N1", "description_2": "orphan"})
        self.assertEqual(html.count("<article"), 1)
        self.assertNotIn("orphan", html)

    def test_no_numbers_are_invented(self):
        self.assertEqual(render(self.m, {"heading": "Only a heading"}).count("dtj-ss__num"), 0)

    def test_up_to_six_cards_and_two_or_three_columns(self):
        self.assertEqual(render(self.m, {f"number_{i}": f"N{i}" for i in range(1, 8)}).count("<article"), 6)
        self.assertIn("--ss-cols: 3;", render(self.m, {"number_1": "N", "columns": "9"}))
        self.assertIn("--ss-cols: 2;", render(self.m, {"number_1": "N", "columns": "2"}))

    def test_the_gradient_needs_both_colours(self):
        self.assertNotIn("dtj-ss--grad", render(self.m, {"number_1": "N", "number_color": "rgb(1, 2, 3)"}))
        self.assertIn("dtj-ss--grad", render(self.m, {"number_1": "N", "number_color": "rgb(1, 2, 3)", "number_color_2": "rgb(4, 5, 6)"}))

    def test_image_description_is_the_screen_reader_text_and_is_escaped(self):
        html = render(self.m, {"number_1": "N", "image_1": "pic", "alt_1": 'Say "hi"'})
        self.assertIn('alt="Say &quot;hi&quot;"', html)
        self.assertIn('alt=""', render(self.m, {"number_1": "N", "image_1": "pic"}))


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class RootScienceTests(unittest.TestCase):
    m = manifest("root-science")

    def test_a_feature_only_shows_when_it_has_text(self):
        html = render(self.m, {"text_1": "Real", "icon_2": "brain"})
        self.assertEqual(html.count('class="dtj-rs__feature"'), 1)

    def test_up_to_six_features(self):
        self.assertEqual(render(self.m, {f"text_{i}": f"F{i}" for i in range(1, 8)}).count('class="dtj-rs__feature"'), 6)

    def test_preset_icons_come_from_the_shared_snippet_and_custom_uses_the_picture(self):
        self.assertIn("dtj-rs__svg", render(self.m, {"text_1": "A", "icon_1": "brain"}))
        html = render(self.m, {"text_1": "A", "icon_1": "custom", "custom_icon_1": "mine"})
        self.assertIn("dtj-rs__icon-img", html)
        self.assertNotIn("dtj-rs__svg", html)
        self.assertNotIn("dtj-rs__icon-img", render(self.m, {"text_1": "A", "icon_1": "custom"}))

    def test_every_preset_icon_in_the_manifest_has_a_drawing(self):
        snippet = (tg.SNIPPETS / "dtj-feature-icon.liquid").read_text(encoding="utf-8")
        options = [o["value"] for s in self.m["settings"] if s["id"] == "icon_1" for o in s["options"] if o["value"] != "custom"]
        for name in options:
            self.assertIn(f"when '{name}'", snippet)

    def test_image_position_and_description(self):
        self.assertIn("dtj-rs--img-start", render(self.m, {"text_1": "A", "image_side": "start"}))
        self.assertIn("dtj-rs--img-end", render(self.m, {"text_1": "A", "image_side": "bogus"}))
        self.assertIn('alt="Described"', render(self.m, {"text_1": "A", "image": "pic", "image_alt": "Described"}))


if __name__ == "__main__":
    unittest.main()
