"""DTJ Circle Menu: story rings, large circles and framed squares."""
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
MANIFEST = json.loads((HERE / "manifests" / "circle-menu.json").read_text(encoding="utf-8"))
CSS = HERE / "extensions" / "dtj-commerce" / "assets" / "dtj-circle-menu.css"


def tiles(n, **extra):
    return {**{f"title_{i}": f"Tile {i}" for i in range(1, n + 1)}, **{f"image_{i}": f"p{i}" for i in range(1, n + 1)}, **extra}


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class CircleMenuTests(unittest.TestCase):
    m = MANIFEST

    def test_nothing_renders_empty_and_ships_no_copy(self):
        self.assertEqual(render(self.m, {}), "")
        html = render(self.m, {"heading": "H"})
        for part in ("dtj-cm__list", "dtj-cm__tile", "dtj-cm__label"):
            self.assertNotIn(part, html)

    def test_a_tile_shows_with_a_collection_a_picture_or_a_name_and_there_are_at_most_eight(self):
        self.assertEqual(render(self.m, tiles(3)).count('class="dtj-cm__tile"'), 3)
        self.assertEqual(render(self.m, {"title_1": "A", "image_2": "p", "title_9": "ignored"}).count('class="dtj-cm__tile"'), 2)
        many = [{"title": f"C{i}", "url": f"/c{i}"} for i in range(1, 8)]
        self.assertEqual(render(self.m, {"collections": many}).count('class="dtj-cm__tile"'), 7)
        self.assertEqual(render(self.m, {"link_1": "/orphan"}), "")

    def test_a_collection_supplies_the_name_picture_and_link_and_every_part_can_be_overridden(self):
        coll = {"title": "Dresses", "url": "/collections/dresses", "image": "collection-pic"}
        html = render(self.m, {"collections": [coll], "variation": "circle"})
        self.assertIn("Dresses", html)
        self.assertIn("//img.example/collection-pic", html)
        self.assertIn('href="/collections/dresses"', html)
        over = render(self.m, {"collections": [coll], "variation": "circle", "title_1": "Frocks", "image_1": "own", "link_1": "/pages/frocks"})
        self.assertIn("Frocks", over)
        self.assertIn("//img.example/own", over)
        self.assertNotIn("/collections/dresses", over)

    def test_the_three_versions_set_their_own_names_and_phone_layout_and_an_explicit_choice_wins(self):
        ring = render(self.m, tiles(3))
        for part in ("dtj-cm--ring", "dtj-cm--labels-hide", "dtj-cm--m-scroll"):
            self.assertIn(part, ring)
        self.assertNotIn("dtj-cm__label", ring)
        circle = render(self.m, tiles(3, variation="circle"))
        for part in ("dtj-cm--circle", "dtj-cm--labels-show", "dtj-cm--m-wrap"):
            self.assertIn(part, circle)
        self.assertEqual(circle.count('class="dtj-cm__label"'), 3)
        square = render(self.m, tiles(3, variation="square"))
        self.assertIn("dtj-cm--square", square)
        self.assertIn("dtj-cm__label", square)
        both = render(self.m, tiles(3, labels="show", mobile_layout="wrap"))  # a ring with names that wraps
        self.assertIn("dtj-cm__label", both)
        self.assertIn("dtj-cm--m-wrap", both)
        self.assertNotIn("dtj-cm__label", render(self.m, tiles(3, variation="circle", labels="hide")))

    def test_a_tile_without_names_still_has_an_accessible_name_and_one_link(self):
        ring = render(self.m, tiles(2, link_1="/a"))
        self.assertIn('aria-label="Tile 1"', ring)
        self.assertEqual(ring.count("<a "), 1)
        self.assertNotIn("<a ", render(self.m, tiles(2)))

    def test_sizes_are_automatic_per_version_until_a_number_is_chosen(self):
        auto = render(self.m, tiles(2))
        for part in ("--cm-size:", "--cm-size-m:", "--cm-gap:"):
            self.assertNotIn(part, auto)
        css = CSS.read_text(encoding="utf-8")
        for needle in ("--cm-d: 100px", "--cm-m: 72px", "--cm-d: 184px", "--cm-m: 104px", "--cm-d: 112px", "--cm-m: 84px"):
            self.assertIn(needle, css)  # the reference sizes: rings 100, circles 184, squares 112
        chosen = render(self.m, tiles(2, tile_size=150, tile_size_mobile=90, gap=30))
        for part in ("--cm-size: 150px", "--cm-size-m: 90px", "--cm-gap: 30px"):
            self.assertIn(part, chosen)

    def test_the_ring_the_frame_and_the_background_gradient_follow_the_settings(self):
        html = render(self.m, tiles(2, ring_width=5, ring_color_1="#111111", frame_color="#ffc0cb", frame_width=3, corner_radius=8, bg_color_2="#ffb6b9"))
        for part in ("--cm-ring: 5px", "--cm-r1: #111111", "--cm-fc: #ffc0cb", "--cm-frame: 3px", "--cm-r: 8px", "dtj-cm--grad", "--cm-bg2: #ffb6b9"):
            self.assertIn(part, html)
        self.assertNotIn("dtj-cm--grad", render(self.m, tiles(2)))

    def test_pictures_are_sized_lazy_and_the_first_five_are_eager_only_at_the_top(self):
        html = render(self.m, tiles(7))
        self.assertEqual(html.count("<img "), 7)
        self.assertEqual(html.count('loading="lazy"'), 7)
        for img in re.findall(r"<img [^>]*>", html):
            self.assertRegex(img, r'width="\d+" height="\d+"')
            self.assertIn('decoding="async"', img)
        self.assertEqual(render(self.m, tiles(7, priority=True)).count('loading="eager"'), 4)  # the first four only

    def test_text_is_escaped_and_the_heading_tag_is_limited(self):
        html = render(self.m, {"heading": "<b>H</b>", "title_1": "<i>t</i>", "heading_tag": "script", "variation": "circle"})
        for bad in ("<b>", "<i>", "<script"):
            self.assertNotIn(bad, html)
        self.assertIn("<h2", html)

    def test_there_is_no_script_and_the_root_is_full_width_and_motion_respects_the_visitor(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertRegex(css, r"(?m)^\.dtj-cm \{[^}]*width: 100%")
        self.assertIn("prefers-reduced-motion: reduce", css)
        self.assertFalse((HERE / "extensions" / "dtj-commerce" / "assets" / "dtj-circle-menu.js").exists())
        self.assertNotIn("<script", render(self.m, tiles(3)))

    def test_the_block_has_a_sane_number_of_settings_and_headers(self):
        interactive = [s for s in self.m["settings"] if s["type"] not in ("header", "paragraph")]
        headers = [s for s in self.m["settings"] if s["type"] in ("header", "paragraph")]
        self.assertLessEqual(len(interactive) + 8, 75)
        self.assertLessEqual(len(headers) + 1, 6)


if __name__ == "__main__":
    unittest.main()
