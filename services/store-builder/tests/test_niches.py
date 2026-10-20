"""Niche-aware block choice: every block is tagged, the order is niche first / universal second / other niches last, and nothing breaks
for a niche that has no blocks of its own yet."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from page_builder import ai_plan, direction, niches  # noqa: E402
from page_builder.catalog import SERVICES, registry  # noqa: E402


def existing_blocks() -> set[str]:
    out = set()
    for app, entry in registry().items():
        for f in (SERVICES / entry["folder"]).glob("dtj-*.liquid"):
            out.add(f"{app}/{re.sub(r'^dtj-', '', f.stem)}")
    return out


class TagsTests(unittest.TestCase):
    def test_every_block_of_every_app_has_a_tag_and_every_tag_is_a_real_block(self):
        have, tagged = existing_blocks(), set(niches.tags())
        self.assertGreater(len(have), 20)
        self.assertEqual(sorted(have - tagged), [], "a block exists without a niche tag: add it to page_builder/block_tags.json")
        self.assertEqual(sorted(tagged - have), [], "a tag points to a block that does not exist")

    def test_every_niche_named_in_a_tag_is_one_the_categories_map_to(self):
        known = set(niches._tags()["niche_of_category"].values())
        for block, tag in niches.tags().items():
            self.assertTrue(set(tag["niches"]) <= known, block)

    def test_every_client_category_has_a_niche(self):
        self.assertEqual(set(direction.CATEGORY), set(niches._tags()["niche_of_category"]))
        self.assertEqual(niches.niche_of("apparel"), "fashion")
        self.assertEqual(niches.niche_of("something-new"), "general")


class OrderTests(unittest.TestCase):
    A, B, C = "dtj-sections/science-stats", "dtj-sections-2/stat-cards", "dtj-blocks/shade-picker"

    def test_niche_first_then_universal_then_other_niches(self):
        self.assertEqual(niches.order_blocks([self.B, self.A], "supplements"), [self.A, self.B])  # science-stats is made for wellness
        self.assertEqual(niches.order_blocks([self.A, self.B], "apparel"), [self.B, self.A])      # fashion: the universal block leads
        self.assertEqual(niches.rank(self.A, "apparel"), niches.OTHER_NICHE)

    def test_a_block_that_makes_no_sense_in_a_niche_is_dropped_but_never_the_last_one(self):
        self.assertEqual(niches.order_blocks([self.C, self.B], "home-care"), [self.B])
        self.assertEqual(niches.order_blocks([self.C], "home-care"), [self.C])
        self.assertEqual(niches.order_blocks([self.C, self.B], "beauty"), [self.C, self.B])

    def test_a_note_after_the_block_name_is_ignored_and_the_order_is_stable(self):
        entry = "dtj-sections-2/stat-cards (when every figure has a picture)"
        self.assertEqual(niches.rank(entry, "beauty"), niches.UNIVERSAL)
        self.assertEqual(niches.order_blocks(["dtj-sections/faq", "dtj-sections/marquee"], "food"), ["dtj-sections/faq", "dtj-sections/marquee"])

    def test_unwired_blocks_are_listed_honestly(self):
        self.assertIn("dtj-blocks/rotating-text", niches.unwired())
        self.assertNotIn("dtj-sections/faq", niches.unwired())


class PlanStepTests(unittest.TestCase):
    def test_the_menu_keeps_every_section_and_every_block_whatever_the_niche(self):
        for category in direction.CATEGORY:
            for section, entries in ai_plan.BLOCKS.items():
                ordered = niches.order_blocks(entries, category)
                self.assertTrue(ordered, (category, section))
                self.assertTrue(set(ordered) <= set(entries))

    def test_the_request_names_the_niche_and_the_prompt_explains_it(self):
        self.assertIn("`niche`", ai_plan.system_prompt())
        self.assertIn("Prefer the first block", ai_plan.system_prompt())


if __name__ == "__main__":
    unittest.main()
