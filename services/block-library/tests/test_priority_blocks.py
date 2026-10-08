"""Tests for what is specific to hero-points, rotating-text and social-proof (the generic tests cover licence, escaping, defaults)."""
import html as htmllib
import json
import re
import shutil
import subprocess
import sys
import unittest
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
import check_library as cl  # noqa: E402
from tests.test_generated_blocks import Environment, generated, render  # noqa: E402


def manifest(block_id):
    return next(m for m in generated() if m["id"] == block_id)


def product(qty=3, tracked="shopify", rating=None):
    return {"selected_or_first_available_variant": {"inventory_quantity": qty, "inventory_management": tracked},
            "metafields": {"reviews": {"rating": {"value": {"rating": rating}}}} if rating is not None else {}}


@unittest.skipIf(Environment is None, "python-liquid not installed (use .work/.venv)")
class HeroPointsTests(unittest.TestCase):
    m = manifest("hero-points")

    def test_benefits_one_per_line_blank_lines_skipped_max_eight(self):
        lines = "\n".join(f"Benefit {i}" if i != 3 else "" for i in range(1, 11))
        html = render(self.m, {"benefits": lines})
        self.assertEqual(html.count("<li"), 8)
        self.assertIn("Benefit 1", html)
        self.assertNotIn("Benefit 10", html)

    def test_benefit_lines_are_escaped(self):
        self.assertNotIn("<script>", render(self.m, {"benefits": "<script>alert(1)</script>"}))

    def test_eyebrow_star_is_optional_and_accent_only_when_set(self):
        self.assertIn("dtj-hero-points__star", render(self.m, {"eyebrow": "New", "show_star": True}))
        self.assertNotIn("dtj-hero-points__star", render(self.m, {"eyebrow": "New", "show_star": False}))
        self.assertNotIn("--hp-accent", render(self.m, {"eyebrow": "New"}))
        self.assertIn("--hp-accent: rgb(1, 2, 3)", render(self.m, {"eyebrow": "New", "accent_color": "rgb(1, 2, 3)"}))

    def test_one_column_is_the_default_and_two_columns_is_opt_in(self):
        self.assertIn("--hp-cols: 1;", render(self.m, {"benefits": "A\nB"}))
        html = render(self.m, {"benefits": "A\nB\nC", "columns": "2"})
        self.assertIn("--hp-cols: 2;", html)
        self.assertIn('data-columns="2"', html)
        self.assertEqual(html.count("<li"), 3)  # same items, only the layout changes

    def test_an_unknown_column_value_falls_back_to_one(self):
        self.assertIn("--hp-cols: 1;", render(self.m, {"benefits": "A\nB", "columns": "7"}))

    def test_stacking_on_phones_only_applies_to_two_columns(self):
        self.assertIn("dtj-hero-points--stack", render(self.m, {"benefits": "A\nB", "columns": "2", "stack_mobile": True}))
        self.assertNotIn("dtj-hero-points--stack", render(self.m, {"benefits": "A\nB", "columns": "2", "stack_mobile": False}))
        self.assertNotIn("dtj-hero-points--stack", render(self.m, {"benefits": "A\nB", "columns": "1", "stack_mobile": True}))

    def test_each_part_is_optional(self):
        self.assertNotIn("dtj-hero-points__list", render(self.m, {"eyebrow": "Only eyebrow"}))
        self.assertNotIn("dtj-hero-points__eyebrow", render(self.m, {"subheading": "Only sub"}))


@unittest.skipIf(Environment is None, "python-liquid not installed (use .work/.venv)")
class RotatingTextTests(unittest.TestCase):
    m = manifest("rotating-text")

    def phrases(self, html):
        raw = re.search(r'data-phrases="([^"]*)"', html).group(1)
        return json.loads(htmllib.unescape(raw))

    def test_phrases_in_order_skipping_blanks_and_quotes_survive(self):
        html = render(self.m, {"phrase_1": "One", "phrase_2": "", "phrase_3": 'Say "hi"', "phrase_4": "   ", "phrase_5": "Five"})
        self.assertEqual(self.phrases(html), ["One", 'Say "hi"', "Five"])

    def test_the_first_non_empty_phrase_is_the_visible_start(self):
        html = render(self.m, {"phrase_2": "Second only"})
        self.assertIn('data-typed>Second only</span>', html)
        self.assertEqual(self.phrases(html), ["Second only"])

    def test_speeds_are_passed_to_the_script(self):
        html = render(self.m, {"phrase_1": "A", "type_speed": 80, "delete_speed": 40, "pause_time": 2500})
        for attribute in ('data-type-speed="80"', 'data-delete-speed="40"', 'data-pause="2500"'):
            self.assertIn(attribute, html)

    def test_prefix_is_optional_and_escaped(self):
        self.assertNotIn("dtj-rotating-text__prefix", render(self.m, {"phrase_1": "A"}))
        self.assertIn("&lt;b&gt;", render(self.m, {"phrase_1": "A", "prefix_text": "<b>"}))


@unittest.skipIf(Environment is None, "python-liquid not installed (use .work/.venv)")
class SocialProofTests(unittest.TestCase):
    m = manifest("social-proof")
    TEXTS = {"low_stock_text": "Only {count} left", "in_stock_text": "{count} in stock", "stock_threshold": 10}

    def test_real_low_stock_uses_the_real_number(self):
        html = render(self.m, self.TEXTS, product=product(qty=3))
        self.assertIn("Only 3 left", html)

    def test_higher_stock_uses_the_other_text(self):
        html = render(self.m, self.TEXTS, product=product(qty=40))
        self.assertIn("40 in stock", html)
        self.assertNotIn("Only", html)

    def test_no_stock_line_without_real_tracked_stock_or_text(self):
        for p in (product(qty=0), product(tracked=""), product(qty=3, tracked=None)):
            self.assertEqual(render(self.m, self.TEXTS, product=p), "")
        self.assertEqual(render(self.m, {**self.TEXTS, "show_stock": False}, product=product()), "")
        self.assertEqual(render(self.m, {"stock_threshold": 10}, product=product()), "")  # no text = hidden, never an invented sentence

    def test_stars_use_the_real_review_rating(self):
        html = render(self.m, {}, product=product(rating="4.5"))
        self.assertIn("dtj-social-proof__stars", html)
        self.assertIn(">4.5<", html)
        self.assertEqual(html.count("&#9733;"), 5)  # 4.5 rounds up to five filled stars, like the pack block

    def test_manual_rating_is_only_a_fallback_and_empty_means_no_stars(self):
        self.assertIn(">4.0<", render(self.m, {"rating_value": "4"}, product=product()))
        self.assertIn(">4.5<", render(self.m, {"rating_value": "2"}, product=product(rating="4.5")))  # review data wins
        self.assertEqual(render(self.m, {}, product=product()), "")
        self.assertEqual(render(self.m, {"rating_value": "0"}, product=product()), "")

    def test_stars_can_be_turned_off(self):
        self.assertEqual(render(self.m, {"show_stars": False}, product=product(rating="4.5")), "")

    def test_badge_is_optional_escaped_and_can_drop_its_shield(self):
        self.assertEqual(render(self.m, {}, product=product()), "")
        html = render(self.m, {"badge_text": "<b>Tag</b>", "badge_icon": True})
        self.assertIn("dtj-social-proof__badge", html)
        self.assertIn("&lt;b&gt;Tag&lt;/b&gt;", html)
        self.assertIn("<svg", html)
        self.assertNotIn("<svg", render(self.m, {"badge_text": "Tag", "badge_icon": False}))

    def test_single_star_style_shows_one_star_and_the_number(self):
        html = render(self.m, {"rating_style": "single", "show_rating_number": False}, product=product(rating="4.5"))
        self.assertEqual(html.count("&#9733;"), 1)
        self.assertNotIn("&#9734;", html)
        self.assertIn(">4.5<", html)
        self.assertEqual(render(self.m, {"rating_style": "single"}, product=product()), "")  # still no invented rating

    def test_customer_photos_show_only_when_set_and_are_decorative(self):
        self.assertNotIn("dtj-social-proof__avatar", render(self.m, {"proof_text_1": "Line"}))
        html = render(self.m, {"avatar_1": "face-1", "avatar_3": "face-3", "avatar_size": 32})
        self.assertEqual(html.count("dtj-social-proof__avatar\""), 2)
        self.assertIn('alt=""', html)
        self.assertIn('aria-hidden="true"', html)

    def test_badge_or_photos_keep_the_row_on_one_line(self):
        self.assertIn("dtj-social-proof--one-line", render(self.m, {"badge_text": "Tag"}))
        self.assertIn("dtj-social-proof--one-line", render(self.m, {"avatar_1": "face-1"}))
        self.assertNotIn("dtj-social-proof--one-line", render(self.m, {"proof_text_1": "Line"}))  # plain lines may still wrap

    def test_works_off_the_product_page(self):
        self.assertIn("Proof line", render(self.m, {"proof_text_1": "Proof line"}))  # no product object at all

    def test_count_placeholder_text_is_escaped(self):
        html = render(self.m, {**self.TEXTS, "low_stock_text": "<b>{count}</b>"}, product=product(qty=2))
        self.assertIn("&lt;b&gt;2&lt;/b&gt;", html)


def priced(price, compare=None):
    variant = {"price": price}
    if compare is not None:
        variant["compare_at_price"] = compare
    return {"selected_or_first_available_variant": variant}


@unittest.skipIf(Environment is None, "python-liquid not installed (use .work/.venv)")
class PriceTests(unittest.TestCase):
    m = manifest("price")

    def test_shows_the_real_price_compare_price_and_worked_out_percentage(self):
        html = render(self.m, {}, product=priced(3800, 4800))
        self.assertIn("Rs. 3800", html)
        self.assertIn("Rs. 4800", html)
        self.assertIn("-21%", html)  # (4800 - 3800) / 4800 = 20.8 % rounds to 21, like the reference screenshot

    def test_no_discount_means_no_compare_price_and_no_badge(self):
        for compare in (None, 0, 3800, 2000):
            html = render(self.m, {}, product=priced(3800, compare))
            self.assertIn("dtj-price__now", html)
            self.assertNotIn("dtj-price__was", html)
            self.assertNotIn("dtj-price__badge", html)

    def test_a_tiny_discount_never_shows_as_zero_percent(self):
        self.assertIn("-1%", render(self.m, {}, product=priced(99999, 100000)))

    def test_amount_badge_uses_the_real_difference(self):
        html = render(self.m, {"badge_type": "amount"}, product=priced(3800, 4800))
        self.assertIn("-Rs. 1000", html)
        self.assertNotIn("%", html)

    def test_parts_can_be_switched_off(self):
        html = render(self.m, {"show_compare": False, "show_badge": False}, product=priced(3800, 4800))
        self.assertNotIn("dtj-price__was", html)
        self.assertNotIn("dtj-price__badge", html)
        self.assertIn("dtj-price__now", html)

    def test_suffix_is_optional_and_escaped(self):
        self.assertIn("-21% OFF", render(self.m, {"badge_suffix": "OFF"}, product=priced(3800, 4800)))
        self.assertNotIn("OFF", render(self.m, {"badge_suffix": ""}, product=priced(3800, 4800)))
        self.assertIn("&lt;b&gt;", render(self.m, {"badge_suffix": "<b>"}, product=priced(3800, 4800)))

    def test_colours_are_set_only_when_chosen(self):
        plain = render(self.m, {}, product=priced(3800, 4800))
        for var in ("--pr-badge-bg", "--pr-badge-color", "--pr-was"):
            self.assertNotIn(var, plain)
        html = render(self.m, {"badge_bg": "rgb(1, 2, 3)", "badge_color": "rgb(4, 5, 6)", "compare_color": "rgb(7, 8, 9)"}, product=priced(3800, 4800))
        self.assertIn("--pr-badge-bg: rgb(1, 2, 3)", html)
        self.assertIn("--pr-badge-color: rgb(4, 5, 6)", html)
        self.assertIn("--pr-was: rgb(7, 8, 9)", html)

    def test_nothing_without_a_product_and_a_placeholder_in_the_editor(self):
        self.assertEqual(render(self.m, {}, product={}), "")
        self.assertIn("DTJ Price shows", render(self.m, {}, product={}, design_mode=True))


@unittest.skipIf(Environment is None, "python-liquid not installed (use .work/.venv)")
class TestimonialsTests(unittest.TestCase):
    m = manifest("testimonials")

    def test_only_reviews_with_text_become_slides(self):
        html = render(self.m, {"quote_1": "One", "quote_3": "Three", "quote_5": "  ", "name_2": "Ghost name only"})
        self.assertEqual(html.count("data-slide"), 2)
        self.assertNotIn("Ghost name only", html)

    def test_up_to_five_reviews(self):
        html = render(self.m, {f"quote_{i}": f"Review {i}" for i in range(1, 6)})
        self.assertEqual(html.count("data-slide"), 5)

    def test_a_single_review_has_no_next_button_or_progress_bar(self):
        html = render(self.m, {"quote_1": "Only one"})
        self.assertIn("Only one", html)
        self.assertNotIn("data-next", html)
        self.assertNotIn("data-progress", html)

    def test_two_reviews_get_the_next_button_and_progress_bar_can_be_turned_off(self):
        two = {"quote_1": "A", "quote_2": "B"}
        self.assertIn("data-next", render(self.m, two))
        self.assertIn("data-progress", render(self.m, {**two, "show_progress": True}))
        self.assertNotIn("data-progress", render(self.m, {**two, "show_progress": False}))

    def test_stars_only_when_a_rating_is_chosen_and_the_count_is_right(self):
        self.assertNotIn("dtj-testimonials__stars", render(self.m, {"quote_1": "A", "rating_1": "none"}))  # never an invented 5 stars
        for chosen in (1, 3, 5):
            html = render(self.m, {"quote_1": "A", "rating_1": str(chosen)})
            self.assertEqual(html.count('fill="currentColor"'), chosen, f"rating {chosen}")
            self.assertEqual(html.count('fill="none"'), 5 - chosen, f"empty stars for rating {chosen}")

    def test_badge_is_only_what_the_brand_typed(self):
        self.assertNotIn("dtj-testimonials__badge", render(self.m, {"quote_1": "A"}))
        html = render(self.m, {"quote_1": "A", "badge_1": "Brand wrote this"})
        self.assertIn("Brand wrote this", html)

    def test_avatar_is_the_first_letter_unless_an_image_is_set(self):
        self.assertIn(">R<", render(self.m, {"quote_1": "A", "name_1": "Riya"}).replace("\n", "").replace(" ", ""))
        html = render(self.m, {"quote_1": "A", "name_1": "Riya", "avatar_1": "avatar-file"})
        self.assertIn("//img.example/avatar-file", html)

    def test_review_photo_only_when_set(self):
        self.assertNotIn("dtj-testimonials__photo", render(self.m, {"quote_1": "A"}))
        self.assertIn("dtj-testimonials__photo", render(self.m, {"quote_1": "A", "image_1": "photo-file"}))

    def test_review_text_is_escaped(self):
        self.assertNotIn("<script>", render(self.m, {"quote_1": "<script>alert(1)</script>", "name_1": "<b>x</b>"}))


@unittest.skipIf(Environment is None, "python-liquid not installed (use .work/.venv)")
class ShoppableReelsTests(unittest.TestCase):
    m = manifest("shoppable-reels")
    PRODUCT = {"title": "Sample product", "url": "/products/sample", "price": 69900}

    def test_empty_cards_are_hidden_and_up_to_six_show(self):
        html = render(self.m, {f"image_{i}": f"img-{i}" for i in range(1, 7)})
        self.assertEqual(html.count("dtj-reels__slide"), 6)
        self.assertEqual(render(self.m, {"image_1": "a", "image_3": "c"}).count("dtj-reels__slide"), 2)

    def test_video_cards_use_the_video_and_get_a_play_button(self):
        html = render(self.m, {"media_type_1": "video", "video_1": "video-file", "image_1": "ignored-image"})
        self.assertIn("video-file", html)
        self.assertIn("data-toggle", html)
        self.assertNotIn("ignored-image", html)

    def test_a_video_card_without_a_video_falls_back_to_its_image(self):
        html = render(self.m, {"media_type_1": "video", "image_1": "fallback-image"})
        self.assertIn("fallback-image", html)
        self.assertNotIn("data-toggle", html)

    def test_an_image_card_never_shows_a_play_button(self):
        self.assertNotIn("data-toggle", render(self.m, {"media_type_1": "image", "image_1": "x", "video_1": "unused-video"}))

    def test_product_overlay_links_to_the_product_with_title_and_price(self):
        html = render(self.m, {"image_1": "x", "products": [self.PRODUCT]})
        for needle in ('href="/products/sample"', "Sample product", "Rs. 69900"):
            self.assertIn(needle, html)
        self.assertNotIn("dtj-reels__product", render(self.m, {"image_1": "x"}))

    def test_a_product_with_no_media_does_not_make_a_card(self):
        self.assertEqual(render(self.m, {"products": [self.PRODUCT]}), "")

    def test_each_card_links_to_the_product_in_the_same_position(self):
        second = {"title": "Second product", "url": "/products/second", "price": 100}
        html = render(self.m, {"image_1": "a", "image_2": "b", "products": [self.PRODUCT, second]})
        self.assertLess(html.index("Sample product"), html.index("Second product"))
        self.assertEqual(html.count("dtj-reels__product"), 2)
        only_second = render(self.m, {"image_1": "a", "image_2": "b", "products": [self.PRODUCT]})
        self.assertEqual(only_second.count("dtj-reels__product"), 1)  # card 2 has no product: no overlay

    def test_labels_default_to_english_and_can_be_translated(self):
        html = render(self.m, {"image_1": "x"})
        self.assertIn('data-play-label="Play video"', html)
        html = render(self.m, {"image_1": "x", "play_label": "Chalao", "pause_label": "Roko"})
        self.assertIn('data-play-label="Chalao"', html)
        self.assertIn('data-pause-label="Roko"', html)

    def test_video_cards_get_a_sound_button_that_starts_off_and_image_cards_do_not(self):
        html = render(self.m, {"media_type_1": "video", "video_1": "video-file"})
        self.assertEqual(html.count("data-sound data-target"), 1)
        self.assertIn('aria-pressed="false"', html)
        self.assertIn('aria-label="Turn sound on"', html)
        self.assertNotIn("data-sound data-target", render(self.m, {"media_type_1": "image", "image_1": "x"}))

    def test_sound_labels_default_to_english_and_can_be_translated(self):
        html = render(self.m, {"image_1": "x"})
        self.assertIn('data-sound-on-label="Turn sound on"', html)
        self.assertIn('data-sound-off-label="Turn sound off"', html)
        html = render(self.m, {"image_1": "x", "sound_on_label": "Awaaz chalu", "sound_off_label": "Awaaz band"})
        self.assertIn('data-sound-on-label="Awaaz chalu"', html)
        self.assertIn('data-sound-off-label="Awaaz band"', html)

    def test_heading_is_optional_and_escaped(self):
        self.assertNotIn("dtj-reels__heading", render(self.m, {"image_1": "x"}))
        html = render(self.m, {"image_1": "x", "heading": "<b>Hi</b>"})
        self.assertIn("&lt;b&gt;Hi&lt;/b&gt;", html)


class LoopOnly(Sequence):
    """Stand-in for Shopify's product_list: it can be looped over (as Shopify documents) but NOT read by position.
    Reading item [0] gives nothing: the suspected cause of the empty Option Picker in the real editor on 6 Oct 2026.
    It is a Sequence only because python-liquid loops over nothing else; __iter__ is used for loops, never __getitem__."""

    def __init__(self, items):
        self._items = list(items)

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def __getitem__(self, index):
        raise TypeError("a product_list cannot be read by position")


def option(handle, title, available=True):
    return {"handle": handle, "title": title, "url": f"/products/{handle}", "featured_media": f"media-{handle}",
            "selected_or_first_available_variant": {"available": available}}


@unittest.skipIf(Environment is None, "python-liquid not installed (use .work/.venv)")
class OptionPickerTests(unittest.TestCase):
    m = manifest("shade-picker")
    TWO = {"products": [option("a", "Product A"), option("b", "Product B")]}

    def test_the_product_the_shopper_is_on_is_marked_current(self):
        html = render(self.m, self.TWO, product={"handle": "b"})
        self.assertEqual(html.count('data-current="true"'), 1)
        self.assertIn('data-current="true" data-unavailable="false" title="Product B" aria-current="page"', html)

    def test_no_current_option_when_the_page_is_not_one_of_them(self):
        self.assertNotIn('data-current="true"', render(self.m, self.TWO, product={"handle": "other"}))
        self.assertNotIn('data-current="true"', render(self.m, self.TWO))  # not a product page at all

    def test_sold_out_options_are_marked_and_not_clickable(self):
        html = render(self.m, {"products": [option("a", "A", available=False), option("b", "B")]})
        self.assertEqual(html.count('data-unavailable="true"'), 1)
        self.assertIn('aria-disabled="true"', html)

    def test_name_defaults_to_the_product_title_and_can_be_overridden(self):
        html = render(self.m, {**self.TWO, "s2_label": "Custom name"})
        self.assertIn("Product A", html)
        self.assertIn("Custom name", html)
        self.assertNotIn("Product B", html)

    def test_current_name_appears_beside_the_label_when_enabled(self):
        html = render(self.m, {**self.TWO, "label_text": "Option", "show_selected": True}, product={"handle": "a"})
        self.assertRegex(html, r'Option\s*<strong data-selected>Product A</strong>')
        self.assertNotIn("data-selected", render(self.m, {**self.TWO, "label_text": "Option", "show_selected": False}, product={"handle": "a"}))

    def test_no_label_row_without_text_or_a_selected_name(self):
        self.assertNotIn("dtj-shade-picker__label", render(self.m, self.TWO, product={"handle": "other"}))

    def test_pill_style_has_text_buttons_and_no_images(self):
        html = render(self.m, {**self.TWO, "style": "pill"})
        self.assertIn("dtj-shade-picker__pill", html)
        self.assertNotIn("<img", html)

    def test_swatch_style_uses_the_swatch_image_then_the_product_image(self):
        html = render(self.m, {**self.TWO, "s1_swatch": "my-swatch"})
        self.assertIn("//img.example/my-swatch", html)
        self.assertIn("//img.example/media-b", html)

    def test_caption_and_subtitle_are_optional(self):
        html = render(self.m, {**self.TWO, "s1_subtitle": "For fair tones", "show_caption": True})
        self.assertIn("For fair tones", html)
        self.assertNotIn("dtj-shade-picker__caption", render(self.m, {**self.TWO, "show_caption": False}))

    def test_up_to_eight_options(self):
        html = render(self.m, {"products": [option(f"p{i}", f"P{i}") for i in range(1, 10)]})  # nine picked: eight are shown
        self.assertEqual(html.count("data-item"), 8)
        self.assertNotIn("P9", html)

    def test_a_single_product_is_enough_to_show_the_row_but_options_are_hidden_when_empty(self):
        self.assertEqual(render(self.m, {}), "")
        self.assertIn("Product A", render(self.m, {"products": [option("a", "Product A")]}))


def addon_product(n, title, price, available=True, compare=None, media=None):
    return {"id": n, "handle": f"h{n}", "title": title, "url": f"/products/h{n}", "featured_media": f"media-{n}",
            "variants": [{"id": n * 10, "price": price}],
            "selected_or_first_available_variant": {"id": n * 10, "price": price, "compare_at_price": compare, "available": available, "featured_media": media}}


@unittest.skipIf(Environment is None, "python-liquid not installed (use .work/.venv)")
class AddonsTests(unittest.TestCase):
    m = manifest("addons")
    ONE = {"products": [addon_product(1, "Product One", 50000)]}

    def test_up_to_four_add_ons_and_empty_slots_are_hidden(self):
        html = render(self.m, {"products": [addon_product(i, f"P{i}", 1000 * i) for i in range(1, 7)]})  # six picked: four cards
        self.assertEqual(html.count("data-card"), 4)
        self.assertNotIn("P5", html)
        self.assertEqual(render(self.m, {"products": [addon_product(1, "A", 100), addon_product(2, "B", 200)]}).count("data-card"), 2)

    def test_only_real_variant_prices_are_used(self):
        html = render(self.m, self.ONE)
        self.assertIn('data-price-main="50000"', html)
        self.assertIn(">Rs. 50000<", html)
        self.assertNotIn("addon_price", html)  # the pack's manual display price is gone on purpose

    def test_compare_at_price_only_when_real_and_enabled(self):
        sale = {"products": [addon_product(1, "Sale", 50000, compare=70000)]}
        self.assertIn('data-compare-main="70000"', render(self.m, sale))
        self.assertIn(" data-compare>", render(self.m, sale))  # a real discount: the crossed-out price is visible
        self.assertIn(" data-compare hidden>", render(self.m, self.ONE))  # no real discount: it stays hidden
        self.assertNotIn('class="dtj-addons__compare"', render(self.m, {**sale, "s1_show_compare": False}))  # switched off: not output at all

    def test_sold_out_is_flagged(self):
        html = render(self.m, {"products": [addon_product(1, "Gone", 100, available=False)]})
        self.assertIn('data-sold-out="true"', html)

    def test_alternative_product_adds_the_swap_buttons(self):
        five = [addon_product(i, f"P{i}", 1000 * i) for i in range(1, 5)] + [addon_product(9, "Alt Product", 60000)]
        html = render(self.m, {"products": five, "s1_alt": "5"})  # card 1 offers product 5 of the list as the switch
        self.assertIn('data-variant-alt="90"', html)
        self.assertIn('data-price-alt="60000"', html)
        self.assertEqual(html.count("data-swap="), 2)
        self.assertEqual(html.count("data-variant-alt="), 1)  # only card 1 has an alternative
        self.assertNotIn("data-swap", render(self.m, self.ONE))

    def test_an_alternative_pointing_at_itself_or_nothing_is_ignored(self):
        self.assertNotIn("data-swap", render(self.m, {"products": [addon_product(1, "A", 1), addon_product(2, "B", 2)], "s1_alt": "1"}))
        self.assertNotIn("data-swap", render(self.m, {"products": [addon_product(1, "A", 1)], "s1_alt": "7"}))  # nothing at position 7

    def test_recommended_tag_marks_exactly_one_card(self):
        two = {"products": [addon_product(1, "A", 1), addon_product(2, "B", 2)], "recommended_slot": "2", "recommended_label": "Our pick"}
        html = render(self.m, two)
        self.assertEqual(html.count('data-recommended="true"'), 1)
        self.assertIn('data-rec-label="Our pick"', html)
        self.assertEqual(render(self.m, {**two, "recommended_slot": "0"}).count('data-recommended="true"'), 0)

    def test_the_main_products_variant_prices_are_handed_to_the_script(self):
        page = {"selected_or_first_available_variant": {"id": 5, "price": 99900}, "variants": [{"id": 5, "price": 99900}, {"id": 6, "price": 109900}]}
        html = render(self.m, self.ONE, product=page)
        self.assertIn('data-main-variant="5"', html)
        self.assertIn('data-main-prices="5:99900,6:109900,"', html)

    def test_after_add_defaults_to_the_reliable_cart_page(self):
        self.assertIn('data-after-add="cart"', render(self.m, self.ONE))
        self.assertIn('data-after-add="drawer"', render(self.m, {**self.ONE, "after_add": "drawer"}))

    def test_total_only_when_enabled_and_text_is_escaped(self):
        self.assertIn("data-total", render(self.m, {**self.ONE, "show_total": True}))
        self.assertNotIn("data-total", render(self.m, {**self.ONE, "show_total": False}))
        self.assertNotIn("<script>", render(self.m, {**self.ONE, "heading": "<script>x</script>", "s1_headline": "<script>y</script>"}))


@unittest.skipIf(Environment is None, "python-liquid not installed (use .work/.venv)")
class LoopOnlyProductListTests(unittest.TestCase):
    """The three blocks that take a product_list must work when the list can only be looped over, like Shopify's."""

    def test_the_stand_in_really_cannot_be_read_by_position(self):
        from tests.test_generated_blocks import Environment as Env
        self.assertEqual(Env().from_string("{{ l[0].title }}").render(l=LoopOnly([{"title": "X"}])).strip(), "")

    def test_option_picker_shows_every_picked_product_in_order(self):
        products = LoopOnly([option("a", "Product A"), option("b", "Product B"), option("c", "Product C")])
        html = render(manifest("shade-picker"), {"products": products, "s2_label": "Second name"}, product={"handle": "b"})
        self.assertEqual(html.count("data-item"), 3)
        # order of the option buttons (the current name also appears earlier, beside the label)
        self.assertLess(html.index('data-label="Product A"'), html.index('data-label="Second name"'))
        self.assertLess(html.index('data-label="Second name"'), html.index('data-label="Product C"'))
        self.assertEqual(html.count('data-current="true"'), 1)

    def test_add_ons_show_cards_and_the_swap_from_position_five(self):
        five = LoopOnly([addon_product(i, f"P{i}", 1000 * i) for i in range(1, 5)] + [addon_product(9, "Alt Product", 60000)])
        html = render(manifest("addons"), {"products": five, "s1_alt": "5"})
        self.assertEqual(html.count("data-card"), 4)
        self.assertIn('data-variant-alt="90"', html)
        self.assertNotIn("P5", html)

    def test_reels_link_each_card_to_the_product_in_the_same_position(self):
        second = {"title": "Second product", "url": "/products/second", "price": 100}
        html = render(manifest("shoppable-reels"), {"image_1": "a", "image_2": "b", "products": LoopOnly([ShoppableReelsTests.PRODUCT, second])})
        self.assertEqual(html.count("dtj-reels__product"), 2)
        self.assertLess(html.index("Sample product"), html.index("Second product"))

    def test_the_editor_note_says_how_many_products_arrived(self):
        self.assertIn("Products received: 0.", render(manifest("shade-picker"), {}, design_mode=True))
        self.assertIn("Products received: 1.", render(manifest("shade-picker"), {"products": LoopOnly([None])}, design_mode=True))
        self.assertIn("Products received: 0.", render(manifest("addons"), {}, design_mode=True))


@unittest.skipIf(Environment is None, "python-liquid not installed (use .work/.venv)")
class EmptyBlockNoteTests(unittest.TestCase):
    """An empty block hides itself. In the theme editor only, it must say what to fill in, naming real settings."""

    # block id -> labels the note must mention (each must also be a real setting label in the manifest)
    NEEDS = {
        "testimonials": ["Review 1 text"],
        "shoppable-reels": ["Card 1 shows", "Card 1 video", "Card 1 image"],
        "shade-picker": ["Option products"],
        "addons": ["Add-on products"],
    }

    def test_empty_block_in_the_editor_says_what_to_fill_in(self):
        for block_id, labels in self.NEEDS.items():
            m = manifest(block_id)
            real = {s.get("label") for s in m["settings"]}
            html = render(m, {}, design_mode=True)
            self.assertIn("is empty", html, block_id)
            self.assertIn("editor only", html, block_id)
            for label in labels:
                self.assertIn(label, real, f"{block_id}: the note names a setting that does not exist: {label}")
                self.assertIn(f'"{label}"', html, f"{block_id}: the note must name {label}")

    def test_empty_block_on_the_storefront_still_prints_nothing(self):
        for block_id in self.NEEDS:
            self.assertEqual(render(manifest(block_id), {}, design_mode=False), "", block_id)

    def test_a_block_with_content_never_shows_the_note(self):
        samples = {m["id"]: m["test"]["sample"] for m in generated()}
        for block_id in self.NEEDS:
            html = render(manifest(block_id), samples[block_id], design_mode=True)
            self.assertNotIn("is empty", html, block_id)

    def test_with_the_licence_off_the_editor_shows_only_the_licence_note(self):
        for block_id in self.NEEDS:
            html = render(manifest(block_id), {}, metafield="inactive", design_mode=True)
            self.assertIn("flag seen: inactive", html, block_id)
            self.assertNotIn("is empty", html, block_id)

    def test_reels_with_a_video_but_the_card_left_on_image_explains_itself(self):
        # the exact situation seen on 6 Oct 2026: a video was chosen but "Card N shows" was still Image
        html = render(manifest("shoppable-reels"), {"media_type_1": "image", "video_1": "video-file"}, design_mode=True)
        self.assertIn("is empty", html)
        self.assertNotIn("dtj-reels__slide", html)


class JavascriptTests(unittest.TestCase):
    def test_the_add_ons_cart_logic_runs_correctly_under_node(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed")
        done = subprocess.run([node, str(ROOT / "tests" / "addons_logic.js")], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stdout[-1500:] + done.stderr[-500:])
        self.assertIn("ALL OK", done.stdout)

    def test_the_reels_tap_and_sound_logic_runs_correctly_under_node(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed")
        done = subprocess.run([node, str(ROOT / "tests" / "reels_logic.js")], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stdout[-1500:] + done.stderr[-1500:])
        self.assertIn("ALL OK", done.stdout)


class AssetAndBudgetTests(unittest.TestCase):
    def test_every_generated_script_is_valid_javascript(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed")
        scripts = sorted((ROOT / "extensions/dtj-blocks/assets").glob("*.js"))
        self.assertTrue(scripts)
        for script in scripts:
            done = subprocess.run([node, "--check", str(script)], capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, f"{script.name}: {done.stderr[:200]}")

    def test_liquid_stays_inside_shopifys_100_kb_limit(self):
        kb, count = cl.liquid_budget()
        self.assertLess(kb, cl.LIQUID_BUDGET_KB, f"{kb:.1f} KB of Liquid: Shopify refuses the deploy above {cl.LIQUID_BUDGET_KB} KB")
        self.assertLessEqual(count, 30)

    def test_the_schema_javascript_key_points_at_a_real_asset(self):
        for path in (ROOT / "extensions/dtj-blocks/blocks").glob("*.liquid"):
            js = cl.extract_schema(path.read_text(encoding="utf-8")).get("javascript")
            if js:
                self.assertTrue((ROOT / "extensions/dtj-blocks/assets" / js).is_file(), f"{path.name} names missing {js}")


if __name__ == "__main__":
    unittest.main()

