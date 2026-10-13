"""DTJ Press Strip: the "as seen in" logo row, grid and scrolling band."""
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
MANIFEST = json.loads((HERE / "manifests" / "press-strip.json").read_text(encoding="utf-8"))
CSS = HERE / "extensions" / "dtj-commerce" / "assets" / "dtj-press-strip.css"


def logos(n, **extra):
    return {**{f"logo_{i}": f"l{i}" for i in range(1, n + 1)}, **{f"name_{i}": f"Press {i}" for i in range(1, n + 1)}, **extra}


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class PressStripTests(unittest.TestCase):
    m = MANIFEST

    def test_nothing_renders_empty_and_no_publication_is_ever_shipped_by_default(self):
        self.assertEqual(render(self.m, {}), "")
        html = render(self.m, {"heading": "As seen in"})
        for part in ("dtj-ps__item", "dtj-ps__logo", "dtj-ps__list", "dtj-ps__band"):
            self.assertNotIn(part, html)

    def test_an_item_needs_a_logo_or_a_name_and_there_are_at_most_eight(self):
        self.assertEqual(render(self.m, logos(3)).count('class="dtj-ps__item"'), 3)
        self.assertEqual(render(self.m, {"name_2": "B", "logo_5": "x", "name_9": "ignored"}).count('class="dtj-ps__item"'), 2)
        self.assertEqual(render(self.m, {"link_1": "/orphan"}), "")

    def test_a_name_without_a_logo_is_shown_as_words_and_a_logo_is_a_picture_with_alt_text(self):
        words = render(self.m, {"name_1": "The Daily"})
        self.assertIn('<span class="dtj-ps__word">The Daily</span>', words)
        self.assertNotIn("<img", words)
        pic = render(self.m, {"logo_1": "l1", "name_1": "The Daily"})
        self.assertIn('alt="The Daily"', pic)

    def test_a_logo_links_only_when_it_has_an_address(self):
        html = render(self.m, logos(2, link_1="/press/one"))
        self.assertEqual(html.count("<a "), 1)
        self.assertIn('href="/press/one"', html)
        self.assertIn('aria-label="Press 1"', html)

    def test_the_layouts_and_tones_become_classes(self):
        self.assertIn("dtj-ps--row", render(self.m, logos(2)))
        self.assertIn("dtj-ps--grid", render(self.m, logos(2, layout="grid", columns=5)))
        self.assertIn("--ps-cols: 5", render(self.m, logos(2, layout="grid", columns=5)))
        for tone in ("original", "gray", "dark", "light"):
            self.assertIn(f"dtj-ps--tone-{tone}", render(self.m, logos(2, logo_tone=tone)))
        self.assertIn("dtj-ps--hover", render(self.m, logos(2)))
        self.assertNotIn("dtj-ps--hover", render(self.m, logos(2, color_on_hover=False)))
        self.assertIn("dtj-ps--lines", render(self.m, logos(2, bordered=True)))

    def test_the_scrolling_band_has_two_copies_and_the_second_is_hidden_from_everyone(self):
        html = render(self.m, logos(3, layout="marquee", link_1="/a", speed=40))
        self.assertEqual(html.count('class="dtj-ps__list"'), 2)
        self.assertEqual(html.count('aria-hidden="true"'), 1)
        self.assertIn("--ps-speed: 40s", html)
        copy = html.split('aria-hidden="true"')[1]
        self.assertNotIn("<a ", copy)  # the copy has no real link: nothing to tab to twice
        self.assertNotIn(' href="', copy)
        self.assertEqual(render(self.m, logos(3)).count('class="dtj-ps__list"'), 1)  # the row layout has one list

    def test_the_band_stops_on_hover_and_stands_still_for_reduced_motion_and_has_no_script(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn("animation-play-state: paused", css)
        self.assertRegex(css, r"prefers-reduced-motion: reduce\)[^@]*animation: none")
        self.assertFalse((HERE / "extensions" / "dtj-commerce" / "assets" / "dtj-press-strip.js").exists())
        self.assertNotIn("<script", render(self.m, logos(2, layout="marquee")))
        self.assertRegex(css, r"(?m)^\.dtj-ps \{[^}]*width: 100%")

    def test_logos_are_lazy_sized_and_the_heading_tag_is_limited(self):
        html = render(self.m, logos(3))
        self.assertEqual(html.count('loading="lazy"'), 3)
        for img in re.findall(r"<img [^>]*>", html):
            self.assertRegex(img, r'width="\d+" height="\d+"')
        h = render(self.m, {"heading": "<b>Seen</b>", "heading_tag": "script", "name_1": "<i>x</i>"})
        for bad in ("<b>", "<i>", "<script"):
            self.assertNotIn(bad, h)
        self.assertIn("<p ", render(self.m, {"heading": "H"}))
        self.assertIn("<h2", render(self.m, {"heading": "H", "heading_tag": "h2"}))

    def test_the_block_has_a_sane_number_of_settings_and_headers(self):
        interactive = [s for s in self.m["settings"] if s["type"] not in ("header", "paragraph")]
        headers = [s for s in self.m["settings"] if s["type"] in ("header", "paragraph")]
        self.assertLessEqual(len(interactive) + 8, 75)
        self.assertLessEqual(len(headers) + 1, 6)


if __name__ == "__main__":
    unittest.main()
