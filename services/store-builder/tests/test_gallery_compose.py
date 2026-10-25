"""The gallery's type: every printed line checked against the facts before anything is drawn, one layout grid for the set.
Nothing reaches Google Fonts or a browser here (the renderer and the font rules are stand-ins)."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from provision import gallery_compose as gc

FACTS = {
    "trust_points": [{"text": "High protein spread", "source": "pack: HIGH PROTEIN PERI SPREAD"}],
    "social_proof": {"lines": [{"text": "65 g protein in every 250 g jar", "source": "pack: 65g PROTEIN PER 250g"}]},
    "key_facts": [{"value": "26 g", "label": "Protein per 100 g", "source": "nutrition table: protein 26.0 g per 100 g"},
                  {"value": "88%", "label": "Peanut butter", "source": "pack ingredients: Peanut Butter 88.00%"}],
    "cta": {"label": "Spice up my protein", "source": "DTJ COPY (basis: pack line SPICE UP YOUR PROTEIN)"},
    "rating": {"value": "4.6", "source": "SAMPLE: no reviews yet"},
}


class Compose(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "pack.png").write_bytes(b"\x89PNG")
        self.drawn = []

    def renderer(self, doc, out):
        self.drawn.append(doc)
        out.write_bytes(b"\x89PNG")
        return out

    def spec(self, **pic):
        base = {"name": "g1", "layout": "pack", "ground": "light", "photo": "pack.png", "headline": "High Protein Peri Spread",
                "sub": "Spice up your protein", "sticker": {"value": "65g", "label": "protein in every 250g jar"}}
        return {"brand": {"primary": "#9E1B22", "accent": "#FFC94A"}, "pictures": [{**base, **pic}]}

    def test_a_picture_gets_its_checked_lines_one_font_system_and_the_brand_colours(self):
        done = gc.compose(self.spec(), FACTS, self.tmp / "out", self.tmp, renderer=self.renderer, faces="")
        self.assertEqual(done[0]["words"][2], {"text": "65g protein in every 250g jar", "source": "pack: 65g PROTEIN PER 250g"})
        doc = self.drawn[0]
        for part in ("High Protein Peri Spread", "Spice up your protein", "<b>65g</b>", "--ground:#FFC94A", "--head:#9E1B22",
                     "font-family:'H'", "document.fonts.load"):
            self.assertIn(part, doc)
        self.assertEqual(json.loads((self.tmp / "out" / "gallery.json").read_text(encoding="utf-8"))[0]["name"], "g1")

    def test_a_line_that_is_not_a_sourced_fact_stops_the_whole_set_before_drawing(self):
        for bad in ({"headline": "India's best spread"}, {"sub": "Rated 4.6 by 1000 customers"}, {"sticker": {"value": "4.6", "label": ""}}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                gc.compose(self.spec(**bad), FACTS, self.tmp / "out", self.tmp, renderer=self.renderer, faces="")
        self.assertEqual(self.drawn, [])

    def test_every_layout_draws_and_a_missing_photo_is_reported(self):
        items = [{"value": "26g", "label": "protein per 100g", "photo": "pack.png"},
                 {"value": "88%", "label": "peanut butter", "photo": "pack.png"}]
        for layout in gc.LAYOUTS:
            with self.subTest(layout=layout):
                spec = self.spec(layout=layout, items=items, headline="High Protein Peri Spread", sub="", sticker={})
                done = gc.compose(spec, FACTS, self.tmp / "out", self.tmp, renderer=self.renderer, faces="")
                self.assertIn("path", done[0], done)
        done = gc.compose(self.spec(photo="nothing.png"), FACTS, self.tmp / "out", self.tmp, renderer=self.renderer, faces="")
        self.assertIn("photo missing", done[0]["error"])
        with self.assertRaises(gc.ComposeError):
            gc.page({"name": "x", "layout": "collage"}, gc.DEFAULT_BRAND, self.tmp, "")

    def test_a_stacked_headline_puts_one_sentence_per_line(self):
        doc = gc.page({"name": "s", "layout": "stack", "headline": "Spread it. Dip it. Stuff it.", "items": []}, gc.DEFAULT_BRAND, self.tmp, "")
        self.assertIn("<em>Spread it.</em><em>Dip it.</em><em>Stuff it.</em>", doc)
        one = gc.page({"name": "s", "layout": "stack", "headline": "Protein in every meal.", "items": []}, gc.DEFAULT_BRAND, self.tmp, "")
        self.assertNotIn("<em>", one)  # one sentence wraps as usual instead of shrinking to fit one line
        unit = gc.page({"name": "b", "layout": "bottom", "headline": "8 g protein per tablespoon", "items": []}, gc.DEFAULT_BRAND, self.tmp, "")
        self.assertIn('<i class="nb">8 g</i> protein', unit)  # the number keeps its unit, with a normal space

    def test_numbers_keep_every_digit_with_the_unit_and_four_tiles_sit_two_by_two(self):
        # 26 Oct 2026 (Senso): "14 g" printed as "1" over "4 g" and a pill's "100 ml" left its pill (a <span> took .num span / .shot span)
        nums = gc.page({"name": "n", "layout": "numbers", "headline": "x", "items": [{"value": "14 g", "label": "in every sachet"},
                        {"value": "100 ml", "label": "hot water"}]}, gc.DEFAULT_BRAND, self.tmp, "")
        self.assertIn('<b><i class="nb">14 g</i></b>', nums)
        self.assertIn('<b><i class="nb">100 ml</i></b>', nums)
        self.assertNotIn('<span class="nb">', nums)
        tiles = [{"photo": "pack.png", "label": n} for n in ("Tea", "Milk", "Clove", "Ginger")]
        four = gc.page({"name": "t", "layout": "tiles", "headline": "What's inside", "items": tiles}, gc.DEFAULT_BRAND, self.tmp, "")
        self.assertIn('<div class="grid g2">', four)
        three = gc.page({"name": "t", "layout": "tiles", "headline": "What's inside", "items": tiles[:3]}, gc.DEFAULT_BRAND, self.tmp, "")
        self.assertIn('<div class="grid">', three)


if __name__ == "__main__":
    unittest.main()
