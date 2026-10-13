"""Tests for what is specific to the blocks of DTJ Commerce (the generic ones, licence / escaping / defaults, live in
services/block-library/tests/test_generated_blocks.py and run against this app with DTJ_APP_ROOT set).

    cd services/block-library-commerce
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


def five(**extra):
    return {**{f"title_{i}": f"Tile {i}" for i in range(1, 6)}, **extra}


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class CategoryGridTests(unittest.TestCase):
    m = manifest("category-grid")

    def css(self):
        return (HERE / "extensions" / "dtj-commerce" / "assets" / "dtj-category-grid.css").read_text(encoding="utf-8")

    def test_nothing_renders_empty_and_no_copy_is_shipped_by_default(self):
        self.assertEqual(render(self.m, {}), "")
        html = render(self.m, {"heading": "H"})
        for part in ("dtj-cg__sub", "dtj-cg__grid", "dtj-cg__tile", "dtj-cg__btn"):
            self.assertNotIn(part, html)

    def test_a_tile_shows_with_a_collection_a_picture_or_a_title_and_there_are_at_most_five(self):
        html = render(self.m, {"title_1": "A", "image_2": "p", "title_6": "ignored"})
        self.assertEqual(html.count('class="dtj-cg__tile'), 2)
        three = render(self.m, {"collections": [{"title": "C1", "url": "/c1"}, {"title": "C2", "url": "/c2"}, {"title": "C3", "url": "/c3"}]})
        self.assertEqual(three.count('class="dtj-cg__tile'), 3)  # each collection in the list is one tile
        self.assertEqual(render(self.m, {"button_1": "orphan button only"}), "")  # a button label alone is not a tile

    def test_a_collection_supplies_the_name_picture_and_link_and_every_part_can_be_overridden(self):
        coll = {"title": "Throws", "url": "/collections/throws", "image": "collection-pic"}
        html = render(self.m, {"collections": [coll], "button_1": "Shop throws"})
        self.assertIn("Throws", html)
        self.assertIn("//img.example/collection-pic", html)
        self.assertIn('href="/collections/throws"', html)
        over = render(self.m, {"collections": [coll], "title_1": "Soft to the touch", "image_1": "own", "link_1": "/pages/guide", "button_1": "Guide"})
        self.assertIn("Soft to the touch", over)
        self.assertIn("//img.example/own", over)
        self.assertIn('href="/pages/guide"', over)
        self.assertNotIn("/collections/throws", over)

    def test_each_tile_has_one_link_and_the_title_is_the_link_when_there_is_no_button(self):
        with_button = render(self.m, {"title_1": "A", "button_1": "Shop", "link_1": "/a"})
        self.assertEqual(with_button.count("<a "), 1)
        self.assertIn('<a class="dtj-cg__btn dtj-cg__stretch" href="/a">', with_button)
        title_link = render(self.m, {"title_1": "A", "link_1": "/a"})
        self.assertEqual(title_link.count("<a "), 1)
        self.assertIn('<a class="dtj-cg__title dtj-cg__stretch" href="/a">A</a>', title_link)
        self.assertNotIn("dtj-cg__stretch", render(self.m, {"title_1": "A", "button_1": "Shop"}))  # no address, no link

    def test_the_big_layouts_need_exactly_five_tiles_otherwise_the_grid_is_even(self):
        self.assertIn("dtj-cg--bento-left", render(self.m, five()))
        self.assertIn("dtj-cg--bento-right", render(self.m, five(layout="bento_right")))
        self.assertIn("dtj-cg--even", render(self.m, {"title_1": "A", "title_2": "B", "title_3": "C", "title_4": "D"}))
        self.assertIn("dtj-cg--even", render(self.m, five(layout="even")))

    def test_the_big_tile_is_the_first_on_the_left_layout_and_the_fifth_on_the_right_layout(self):
        left = re.findall(r'<div class="dtj-cg__tile( dtj-cg__tile--feature)?">', render(self.m, five()))
        self.assertEqual([bool(x) for x in left], [True, False, False, False, False])
        right = re.findall(r'<div class="dtj-cg__tile( dtj-cg__tile--feature)?">', render(self.m, five(layout="bento_right")))
        self.assertEqual([bool(x) for x in right], [False, False, False, False, True])
        even = re.findall(r'<div class="dtj-cg__tile( dtj-cg__tile--feature)?">', render(self.m, five(layout="even")))
        self.assertEqual(sum(bool(x) for x in even), 0)

    def test_pictures_are_sized_lazy_and_only_the_first_is_eager_at_the_top(self):
        html = render(self.m, five(image_1="a", image_2="b"))
        self.assertEqual(html.count('<img '), 2)
        self.assertEqual(html.count('loading="lazy"'), 2)
        self.assertNotIn("fetchpriority", html)
        for img in re.findall(r"<img [^>]*>", html):
            self.assertRegex(img, r'width="\d+" height="\d+"')
            self.assertIn('decoding="async"', img)
        top = render(self.m, five(image_1="a", image_2="b", priority=True))
        self.assertEqual(top.count('fetchpriority="high"'), 1)

    def test_the_button_is_a_regular_rectangle_never_an_oval(self):
        for rule in re.findall(r"\.dtj-cg[^{]*btn[^{]*\{[^}]*\}", self.css()):
            self.assertNotRegex(rule, r"border-radius:\s*(999|9999|50%|100px)")
        shapes = [o["value"] for s in self.m["settings"] if s.get("id") == "button_shape" for o in s["options"]]
        self.assertEqual(sorted(shapes), ["rounded", "square"])

    def test_the_tint_the_gap_and_the_caption_position_become_styles_and_classes(self):
        html = render(self.m, five(overlay=30, gap=8, caption_position="middle", feature_middle=True))
        for part in ("--cg-ov: 0.3", "--cg-gap: 8px", "dtj-cg--cap-middle", "dtj-cg--fmid"):
            self.assertIn(part, html)

    def test_text_is_escaped_and_the_heading_tag_is_limited(self):
        html = render(self.m, {"heading": "<b>H</b>", "title_1": "<i>t</i>", "button_1": "<u>b</u>", "heading_tag": "script"})
        for bad in ("<b>", "<i>", "<u>"):
            self.assertNotIn(bad, html)
        self.assertIn("<h2", html)

    def test_the_block_root_is_full_width_and_there_is_no_script(self):
        self.assertRegex(self.css(), r"(?m)^\.dtj-cg \{[^}]*width: 100%")
        self.assertNotIn("<script", render(self.m, five()))
        self.assertFalse((HERE / "extensions" / "dtj-commerce" / "assets" / "dtj-category-grid.js").exists())

    def test_the_block_has_a_sane_number_of_settings_and_headers(self):
        interactive = [s for s in self.m["settings"] if s["type"] not in ("header", "paragraph")]
        headers = [s for s in self.m["settings"] if s["type"] in ("header", "paragraph")]
        self.assertLessEqual(len(interactive) + 8, 75)
        self.assertLessEqual(len(headers) + 1, 6)


if __name__ == "__main__":
    unittest.main()
