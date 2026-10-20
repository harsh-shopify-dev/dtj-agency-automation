"""DTJ Category Slider: the swipeable category tiles with slanted, leaf or rounded shapes."""
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
MANIFEST = json.loads((HERE / "manifests" / "category-slider.json").read_text(encoding="utf-8"))
ASSETS = HERE / "extensions" / "dtj-commerce" / "assets"


def tiles(n, **extra):
    return {**{f"title_{i}": f"Tile {i}" for i in range(1, n + 1)}, **{f"image_{i}": f"p{i}" for i in range(1, n + 1)}, **extra}


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class CategorySliderTests(unittest.TestCase):
    m = MANIFEST

    def test_nothing_renders_empty_and_no_copy_is_shipped_by_default(self):
        self.assertEqual(render(self.m, {}), "")
        html = render(self.m, {"heading": "H"})
        for part in ("dtj-cr__sub", "dtj-cr__track", "dtj-cr__tile", "dtj-cr__prev", "dtj-cr__bg"):
            self.assertNotIn(part, html)

    def test_a_tile_shows_with_a_collection_a_picture_or_a_title_and_there_are_at_most_eight(self):
        self.assertEqual(render(self.m, tiles(3)).count('class="dtj-cr__tile"'), 3)
        self.assertEqual(render(self.m, {"title_1": "A", "image_2": "p", "title_9": "ignored"}).count('class="dtj-cr__tile"'), 2)
        many = [{"title": f"C{i}", "url": f"/c{i}"} for i in range(1, 7)]
        self.assertEqual(render(self.m, {"collections": many}).count('class="dtj-cr__tile"'), 6)
        self.assertEqual(render(self.m, {"link_1": "/orphan"}), "")

    def test_a_collection_supplies_the_name_picture_and_link_and_every_part_can_be_overridden(self):
        coll = {"title": "Throws", "url": "/collections/throws", "image": "collection-pic"}
        html = render(self.m, {"collections": [coll]})
        self.assertIn("Throws", html)
        self.assertIn("//img.example/collection-pic", html)
        self.assertIn('href="/collections/throws"', html)
        over = render(self.m, {"collections": [coll], "title_1": "Soft", "image_1": "own", "link_1": "/pages/guide"})
        self.assertIn("Soft", over)
        self.assertIn("//img.example/own", over)
        self.assertIn('href="/pages/guide"', over)
        self.assertNotIn("/collections/throws", over)

    def test_each_tile_has_one_link_and_a_tile_without_an_address_has_none(self):
        html = render(self.m, tiles(2, link_1="/a"))
        self.assertEqual(html.count("<a "), 1)
        self.assertNotIn("<a ", render(self.m, tiles(2)))

    def test_the_shape_the_slant_and_the_picture_scale_follow_the_settings(self):
        slant = render(self.m, tiles(3, skew_angle=10, tile_ratio="1.05"))
        for part in ("dtj-cr--shape-slant", "--cr-sk: 10deg", "--cr-ar: 1.05", "--cr-nm: 1.5"):
            self.assertIn(part, slant)
        self.assertIn("dtj-cr--shape-leaf", render(self.m, tiles(3, shape="leaf")))
        self.assertIn("dtj-cr--shape-round", render(self.m, tiles(3, shape="round")))
        straight = render(self.m, tiles(3, skew_angle=0))
        self.assertIn("--cr-sk: 0deg", straight)
        self.assertRegex(straight, r"--cr-sc: 1\.04")  # nothing to compensate for: the picture is barely scaled

    def test_the_picture_is_scaled_up_enough_to_cover_a_slanted_tile(self):
        scale = float(re.search(r"--cr-sc: ([\d.]+)", render(self.m, tiles(3, skew_angle=10, tile_ratio="1.05"))).group(1))
        self.assertGreater(scale, 1.2)  # tan(10 deg) / 1.05 + 1.04
        taller = float(re.search(r"--cr-sc: ([\d.]+)", render(self.m, tiles(3, skew_angle=10, tile_ratio="0.75"))).group(1))
        self.assertGreater(taller, scale)  # a portrait tile is slanted more, so it needs more scale

    def test_titles_can_be_below_left_below_centred_on_the_picture_or_hidden(self):
        for value, cls in (("below_left", "dtj-cr--cap-below-left"), ("below_center", "dtj-cr--cap-below-center"), ("overlay", "dtj-cr--cap-overlay")):
            html = render(self.m, tiles(2, caption=value))
            self.assertIn(cls, html)
            self.assertIn("dtj-cr__title", html)
        self.assertNotIn("dtj-cr__title", render(self.m, tiles(2, caption="none")))

    def test_the_card_the_fade_the_background_picture_and_the_heading_choices_become_classes(self):
        html = render(self.m, tiles(3, panel=True, edge_fade=True, bg_image="water", bg_overlay=20, heading="H", heading_align="left", sub_align="center", subheading="S"))
        for part in ("dtj-cr--panel", "dtj-cr--fade", "dtj-cr--bgimg", "dtj-cr__bg-img", "--cr-ov: 0.2", "dtj-cr--head-left", "dtj-cr--sub-center"):
            self.assertIn(part, html)
        plain = render(self.m, tiles(3, heading="H", subheading="S"))
        self.assertIn("dtj-cr--sub-center", plain)  # the subheading follows the heading (centred) unless set
        self.assertNotIn("dtj-cr--panel", plain)

    def test_arrows_need_two_tiles_and_can_be_switched_off_or_made_round(self):
        self.assertEqual(render(self.m, tiles(3)).count('class="dtj-cr__arrow'), 2)
        self.assertNotIn("dtj-cr__arrow", render(self.m, tiles(1)))
        self.assertNotIn("dtj-cr__arrow", render(self.m, tiles(3, arrows="none")))
        self.assertIn("dtj-cr--arrows-circle", render(self.m, tiles(3, arrows="circle")))

    def test_pictures_are_sized_lazy_and_only_the_first_two_are_eager_at_the_top(self):
        html = render(self.m, tiles(4))
        self.assertEqual(html.count("<img "), 4)
        self.assertEqual(html.count('loading="lazy"'), 4)
        self.assertNotIn("fetchpriority", html)
        for img in re.findall(r"<img [^>]*>", html):
            self.assertRegex(img, r'width="\d+" height="\d+"')
            self.assertIn('decoding="async"', img)
        top = render(self.m, tiles(4, priority=True))
        self.assertEqual(top.count('loading="eager"'), 2)
        self.assertEqual(top.count('fetchpriority="high"'), 1)

    def test_text_is_escaped_and_the_heading_tag_is_limited(self):
        html = render(self.m, {"heading": "<b>H</b>", "title_1": "<i>t</i>", "heading_tag": "script"})
        for bad in ("<b>", "<i>"):
            self.assertNotIn(bad, html)
        self.assertIn("<h2", html)

    def test_the_track_is_a_native_scroll_row_and_the_script_stays_small_and_quiet(self):
        css = (ASSETS / "dtj-category-slider.css").read_text(encoding="utf-8")
        self.assertIn("scroll-snap-type: x mandatory", css)
        js = (ASSETS / "dtj-category-slider.js").read_text(encoding="utf-8")
        self.assertLess(len(js.encode("utf-8")), 4000)
        for banned in ("fetch(", "XMLHttpRequest", "innerHTML", "setInterval", "document.write"):
            self.assertNotIn(banned, js)
        self.assertIn("passive: true", js)
        self.assertRegex(css, r"(?m)^\.dtj-cr \{[^}]*width: 100%")

    def test_the_block_has_a_sane_number_of_settings_and_headers(self):
        interactive = [s for s in self.m["settings"] if s["type"] not in ("header", "paragraph")]
        headers = [s for s in self.m["settings"] if s["type"] in ("header", "paragraph")]
        self.assertLessEqual(len(interactive) + 8, 75)
        self.assertLessEqual(len(headers) + 1, 6)


if __name__ == "__main__":
    unittest.main()
