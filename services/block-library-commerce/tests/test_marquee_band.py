"""DTJ Marquee Band: three looks of one sliding strip of icon + words, a seamless CSS-only loop."""
import json
import os
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
os.environ["DTJ_APP_ROOT"] = str(HERE)
sys.path.insert(0, str(HERE.parent / "block-library" / "tests"))
import test_generated_blocks as tg  # noqa: E402

render = tg.render
MANIFEST = json.loads((HERE / "manifests" / "marquee-band.json").read_text(encoding="utf-8"))
CSS = HERE / "extensions" / "dtj-commerce" / "assets" / "dtj-marquee-band.css"
ICONS = HERE / "extensions" / "dtj-commerce" / "snippets" / "dtj-mq-icon.liquid"
SAMPLE = {"icon_1": "return", "text_1": "30 days return policy", "icon_2": "e-bolt", "text_2": "Fast delivery", "text_3": "Plain words"}


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class MarqueeBandTests(unittest.TestCase):
    m = MANIFEST

    def r(self, design_mode=False, **extra):
        return render(self.m, {**SAMPLE, **extra}, design_mode=design_mode)

    def test_it_ships_empty_and_the_editor_says_so(self):
        self.assertEqual(render(self.m, {}), "")
        hint = render(self.m, {}, design_mode=True)
        self.assertIn("DTJ Marquee Band is empty", hint)
        self.assertNotIn("dtj-mq__track", hint)

    def test_an_item_without_words_is_skipped_even_with_an_icon(self):
        html = self.r(icon_4="truck", text_4="")
        self.assertNotIn("dtj-mq__svg", self.r(icon_1="none", icon_4="truck", text_4="", text_1="Only words"))
        self.assertEqual(html.count("Fast delivery"), 2 * 3)  # 3 passes in each of the two halves

    def test_three_versions_are_a_class_each(self):
        for v in ("line", "dark", "bold"):
            self.assertIn(f"dtj-mq--{v}", self.r(variation=v))
        self.assertIn("dtj-mq--line", self.r())
        self.assertEqual([o["value"] for o in next(s for s in self.m["settings"] if s.get("id") == "variation")["options"]], ["line", "dark", "bold"])

    def test_line_icons_are_svg_and_emoji_are_text_and_both_are_hidden_from_readers(self):
        html = self.r()
        self.assertIn("dtj-mq__svg", html)
        self.assertIn("dtj-mq__emoji", html)
        self.assertIn("&#9889;", html)
        for tag in re.findall(r"<(?:svg|span) class=\"dtj-mq__(?:svg|emoji)\"[^>]*>", html):
            self.assertIn('aria-hidden="true"', tag)
        self.assertNotIn("dtj-mq__icon", self.r(icon_1="none", icon_2="none"))

    def test_the_loop_has_two_equal_halves_and_the_second_is_hidden_from_readers(self):
        html = self.r(repeat=2)
        lists = re.findall(r'<ul class="dtj-mq__list"[^>]*>(.*?)</ul>', html, flags=re.S)
        self.assertEqual(len(lists), 2)
        self.assertEqual(lists[0].count("<li"), lists[1].count("<li"))
        self.assertEqual(lists[0].count("<li"), 3 * 2)
        self.assertIn('class="dtj-mq__list" role="list" aria-hidden="true"', html)
        # only the very first pass of items is read aloud
        self.assertEqual(len(re.findall(r'<li class="dtj-mq__item">', html)), 3)
        self.assertEqual(len(re.findall(r'<li class="dtj-mq__item" aria-hidden="true">', html)), 3 * 2 * 2 - 3)

    def test_repeat_controls_how_many_passes_each_half_holds(self):
        for n in (1, 3, 6):
            html = self.r(repeat=n)
            self.assertEqual(html.count("Plain words"), 2 * n)

    def test_links_work_once_and_the_loop_copies_never_take_the_keyboard(self):
        html = self.r(link_2="/pages/shipping", repeat=3)
        self.assertEqual(html.count(' href="/pages/shipping"'), 1)
        self.assertEqual(html.count("<a "), 1)
        self.assertIn('data-href="/pages/shipping"', html)

    def test_words_are_escaped(self):
        html = self.r(text_3="<b>Sale</b> & more")
        self.assertNotIn("<b>Sale</b>", html)
        self.assertIn("&lt;b&gt;Sale&lt;/b&gt;", html)

    def test_numbers_left_at_zero_keep_the_versions_own_size(self):
        html = self.r()
        for var in ("--mq-fs:", "--mq-gap:", "--mq-icon:", "--mq-line-w:", "--mq-icon-color", "--mq-line:"):
            self.assertNotIn(var, html)
        html = self.r(font_size=40, gap=80, icon_size=50, line_width=3, icon_color="#ff0000", line_color="#00ff00")
        for part in ("--mq-fs: 40px", "--mq-gap: 80px", "--mq-icon: 50px", "--mq-line-w: 3px", "--mq-icon-color: #ff0000", "--mq-line: #00ff00"):
            self.assertIn(part, html)

    def test_direction_pause_and_lines_follow_the_settings(self):
        html = self.r(direction="right", pause_on_hover=True, show_lines=False)
        for cls in ("dtj-mq--right", "dtj-mq--pause", "dtj-mq--nolines"):
            self.assertIn(cls, html)
        html = self.r(show_lines=True, pause_on_hover=False)
        for cls in ("dtj-mq--right", "dtj-mq--pause", "dtj-mq--nolines"):
            self.assertNotIn(cls, html)
        self.assertIn("dtj-mq--left", html)

    def test_every_icon_in_the_picker_draws_something_and_an_unknown_one_draws_nothing(self):
        values = [o["value"] for o in next(s for s in self.m["settings"] if s.get("id") == "icon_1")["options"] if o["value"] != "none"]
        for v in values:
            html = render(self.m, {"text_1": "x", "icon_1": v})
            self.assertTrue("dtj-mq__svg" in html or "dtj-mq__emoji" in html, v)
        self.assertNotIn("dtj-mq__svg", render(self.m, {"text_1": "x", "icon_1": "nonsense"}))

    def test_the_css_slides_by_exactly_one_half_stops_on_hover_and_respects_reduced_motion(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn("translateX(-50%)", css)
        self.assertRegex(css, r"prefers-reduced-motion: reduce\)[\s\S]*animation: none")
        self.assertIn("animation-play-state: paused", css)
        self.assertIn("animation-direction: reverse", css)
        self.assertRegex(css, r"(?m)^\.dtj-mq \{[^}]*width: 100%")
        self.assertRegex(css, r"(?m)^\.dtj-mq \{[^}]*overflow: hidden")
        self.assertNotRegex(css, r"#[0-9a-fA-F]{3,8}\b")

    def test_the_icon_snippet_has_no_hard_coded_colors(self):
        self.assertNotRegex(ICONS.read_text(encoding="utf-8"), r"(?:fill|stroke)=\"#")

    def test_there_is_no_default_copy_and_the_setting_count_is_sane(self):
        for s in self.m["settings"]:
            if s["type"] in ("text", "textarea"):
                self.assertNotIn("default", s, s["id"])
        interactive = [s for s in self.m["settings"] if s["type"] not in ("header", "paragraph")]
        self.assertLessEqual(len(interactive) + 12, 75)
        self.assertLessEqual(sum(1 for s in self.m["settings"] if s["type"] == "header") + 1, 8)


if __name__ == "__main__":
    unittest.main()
