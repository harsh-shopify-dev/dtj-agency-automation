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
