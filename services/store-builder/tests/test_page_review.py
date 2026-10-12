"""Tests for the screenshot review loop: colour maths, every check on a hand-made probe, the local page renderer, the loop's one allowed
fix (reverting Claude-written lines), and the end-to-end command. A stand-in browser is used here so the tests are fast and need no Edge;
the real browser run is `python -m page_builder.run_page` (see docs/page-builder-design-judgment.md)."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from page_builder import render, review, run_page
from page_builder.assemble import build_pdp
from page_builder.examples import fixtures

try:
    import liquid  # noqa: F401
except ImportError:
    liquid = None


def probe(width=390, **parts):
    base = {"width": width, "page_width": width, "page_height": 3000, "texts": [], "offenders": [], "clipped": [], "taps": [],
            "broken_images": [], "blocks": [], "sections": []}
    base.update(parts)
    return base


def text(colour, layers, size=15, weight=400, txt="Some words", image=False, section="dtj_why", block="b1"):
    return {"section": section, "block": block, "dtj": "dtj-x/y", "tag": "p", "text": txt, "color": colour, "image": image,
            "layers": layers, "size": size, "weight": weight}


def checks(findings):
    return sorted((f.check, f.severity) for f in findings)


class ColourTests(unittest.TestCase):
    def test_contrast_matches_wcag(self):
        self.assertEqual(review.contrast((0, 0, 0, 1), (255, 255, 255, 1)), 21.0)
        self.assertEqual(review.contrast((119, 119, 119, 1), (255, 255, 255, 1)), 4.48)

    def test_colour_formats_browsers_report(self):
        self.assertEqual(review.parse_colour("rgb(15, 42, 58)"), (15.0, 42.0, 58.0, 1.0))
        self.assertEqual(review.parse_colour("rgba(0, 0, 0, 0.5)")[3], 0.5)
        r, g, b, a = review.parse_colour("color(srgb 0.0588235 0.164706 0.227451 / 0.55)")
        self.assertEqual((round(r), round(g), round(b), a), (15, 42, 58, 0.55))
        with self.assertRaises(review.UnmeasurableColour):
            review.parse_colour("oklch(0.7 0.1 200)")

    def test_semi_transparent_layers_are_blended_from_the_outside_in(self):
        bg = review.effective_background(["rgba(0, 0, 0, 0.5)", "rgb(255, 255, 255)"])
        self.assertEqual([round(v) for v in bg[:3]], [128, 128, 128])


class AnalyseTests(unittest.TestCase):
    def test_a_clean_page_has_no_findings(self):
        p = probe(texts=[text("rgb(15, 42, 58)", ["rgb(255, 255, 255)"])], blocks=[{"block": "b1", "dtj": "x/y", "section": "s", "height": 200, "text_len": 40, "images": 0}])
        self.assertEqual(review.analyse(p, 390), [])

    def test_sideways_scrolling_and_elements_past_the_edge(self):
        p = probe(page_width=452, offenders=[{"section": "main", "block": "b", "dtj": "x/y", "tag": "div", "left": 16, "right": 452}])
        self.assertEqual(checks(review.analyse(p, 390)), [("R01", "error"), ("R02", "error")])

    def test_low_contrast_text_fails_once_per_colour_pair(self):
        grey = text("rgb(150, 150, 150)", ["rgb(255, 255, 255)"])
        p = probe(texts=[grey, dict(grey, text="other words")])
        found = review.analyse(p, 390)
        self.assertEqual(checks(found), [("R03", "error")])
        self.assertIn("needs 4.5:1", found[0].message)

    def test_large_text_and_symbols_need_3_to_1(self):
        mid = "rgb(140, 140, 140)"  # about 3.4:1 on white
        self.assertEqual(review.analyse(probe(texts=[text(mid, ["rgb(255, 255, 255)"], size=28)]), 390), [])
        self.assertEqual(review.analyse(probe(texts=[text(mid, ["rgb(255, 255, 255)"], txt="★★★★★")]), 390), [])
        self.assertEqual(checks(review.analyse(probe(texts=[text(mid, ["rgb(255, 255, 255)"])]), 390)), [("R03", "error")])
        pale_star = text("rgb(224, 161, 0)", ["rgb(255, 255, 255)"], txt="★")  # the plain gold the loop caught (2.27:1)
        self.assertEqual(checks(review.analyse(probe(texts=[pale_star]), 390)), [("R03", "error")])

    def test_text_on_a_picture_or_an_unknown_colour_space_is_left_to_a_person(self):
        p = probe(texts=[text("rgb(255, 255, 255)", [], image=True), text("oklch(0.5 0.1 20)", ["rgb(255, 255, 255)"], block="b2")])
        self.assertEqual(checks(review.analyse(p, 390)), [("R04", "warn"), ("R04", "warn")])

    def test_cut_off_text_empty_blocks_small_taps_and_broken_pictures(self):
        p = probe(clipped=[{"section": "s", "block": "b", "tag": "p", "text": "long"}],
                  blocks=[{"block": "b", "dtj": "x/y", "section": "s", "height": 0, "text_len": 0, "images": 0}],
                  taps=[{"section": "s", "block": "b", "tag": "button", "w": 20, "h": 20, "label": "next"}],
                  broken_images=[{"section": "s", "block": "b", "src": "x.webp"}])
        self.assertEqual(checks(review.analyse(p, 390)), [("R05", "warn"), ("R06", "error"), ("R07", "warn"), ("R08", "error")])
        self.assertNotIn("R07", [f.check for f in review.analyse(dict(p, width=1280, page_width=1280), 1280)])


@unittest.skipIf(liquid is None, "python-liquid not installed")
class RenderTests(unittest.TestCase):
    def test_every_section_and_buy_box_block_is_rendered_with_the_real_block_files(self):
        b, f = fixtures.toilova()
        result = build_pdp(b, f)
        doc, notes = render.page_html(result)
        for sid in result.template["order"]:
            self.assertIn(f'data-pb-section="{sid}"', doc)
        for sec in result.model.buybox_sections:
            self.assertIn(f'data-pb-dtj="{sec.app}/{sec.block}"', doc)
        body = doc.split("<script>")[0]
        for leftover in ("Liquid error", "{{", "{%"):
            self.assertNotIn(leftover, body)
        self.assertEqual(body.count('class="dtj-b'), doc.count("data-pb-dtj="))  # every block passed the licence gate
        self.assertIn("theme product gallery", notes["stand_ins"])
        self.assertIn('data-pb-theme="buy-buttons"', doc)

    def test_pictures_are_placeholders_unless_the_file_is_given(self):
        b, f = fixtures.toilova()
        result = build_pdp(b, f)
        doc, notes = render.page_html(result)
        self.assertGreater(notes["placeholder_pictures"], 0)
        with tempfile.TemporaryDirectory() as tmp:
            name = f["media"][0]["file"]
            try:
                from PIL import Image
                Image.new("RGB", (300, 200), "#123456").save(Path(tmp) / name, format="WEBP")
            except Exception:  # noqa: BLE001 - without Pillow, any bytes will do for the path check
                (Path(tmp) / name).write_bytes(b"x")
            doc2, notes2 = render.page_html(result, media_dir=Path(tmp))
            self.assertIn(Path(tmp, name).resolve().as_uri(), doc2)
            self.assertLess(notes2["placeholder_pictures"], notes["placeholder_pictures"])


class FakeBrowser:
    """Returns prepared probes, one per measure() call; records screenshots as tiny files."""

    def __init__(self, probes):
        self.probes, self.measured, self.shots = list(probes), [], []

    def measure(self, doc, width):
        self.measured.append((width, doc))
        p = self.probes.pop(0) if self.probes else probe(width)
        return dict(p, width=width, page_width=p["page_width"] if p["page_width"] != p["width"] else width)

    def screenshot(self, doc, width, height, out_png, scale=1):
        out_png.write_bytes(b"\x89PNG test")
        self.shots.append(width)
        return out_png


def failing(section, width):
    return probe(width, texts=[text("rgb(150, 150, 150)", ["rgb(255, 255, 255)"], section=section)])


@unittest.skipIf(liquid is None, "python-liquid not installed")
class LoopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.brand, self.facts = fixtures.toilova()

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_clean_page_passes_in_one_round_and_writes_its_files(self):
        br = FakeBrowser([probe(390), probe(1280)])
        rep = review.review_page(self.brand, self.facts, out_dir=self.out, browser=br)
        self.assertEqual((rep["verdict"], len(rep["rounds"])), ("pass", 1))
        for name in ("review.json", "preview.html", "page-390.png", "page-1280.png"):
            self.assertTrue((self.out / name).is_file(), name)
        self.assertEqual(sorted(br.shots), [390, 1280])

    def test_claude_lines_in_a_failing_section_are_reverted_and_the_page_rechecked(self):
        overrides = {"dtj_why.heading": "Why people pick TOILOVA", "dtj_faq.heading": "Your questions"}
        br = FakeBrowser([failing("dtj_why", 390), probe(1280), probe(390), probe(1280)])
        rep = review.review_page(self.brand, self.facts, out_dir=self.out, browser=br, copy_overrides=overrides)
        self.assertEqual(rep["verdict"], "pass")
        self.assertEqual(len(rep["rounds"]), 2)
        self.assertEqual(list(rep["reverted_copy"]), ["dtj_why.heading"])
        self.assertEqual(rep["copy_lines_kept"], ["dtj_faq.heading"])
        final = rep["_result"]
        self.assertEqual(final.model.prov[("dtj_why", "heading")]["kind"], "structure")
        self.assertEqual(final.model.prov[("dtj_faq", "heading")]["kind"], "copy")

    def test_a_failure_the_loop_may_not_fix_goes_to_a_person(self):
        br = FakeBrowser([failing("dtj_stats", 390), probe(1280)])
        rep = review.review_page(self.brand, self.facts, out_dir=self.out, browser=br, copy_overrides={"dtj_why.heading": "Why people pick TOILOVA"})
        self.assertEqual((rep["verdict"], len(rep["rounds"]), rep["reverted_copy"]), ("needs human", 1, {}))
        self.assertTrue((self.out / "page-390.png").is_file())  # the person gets the screenshots

    def test_the_report_says_what_was_not_checked(self):
        rep = review.review_page(self.brand, self.facts, out_dir=self.out, browser=FakeBrowser([]))
        saved = json.loads((self.out / "review.json").read_text(encoding="utf-8"))
        self.assertTrue(any("stand-ins" in n for n in saved["not_checked_here"]))
        self.assertNotIn("_result", saved)


@unittest.skipIf(liquid is None, "python-liquid not installed")
class CommandTests(unittest.TestCase):
    def test_end_to_end_with_a_live_copy_step_and_a_clean_review(self):
        from tests.test_copy_step import FakeClient, answer, current_slots
        b, f = fixtures.toilova()
        slots = current_slots(b, f)
        slots["dtj_faq.heading"] = "Your questions"
        with tempfile.TemporaryDirectory() as tmp:
            code = run_page.main(["--example", "toilova", "--out", tmp, "--copy", "live"],
                                 browser=FakeBrowser([]), client=FakeClient(answer(slots)))
            self.assertEqual(code, 0)
            copy_rep = json.loads(Path(tmp, "copy.json").read_text(encoding="utf-8"))
            self.assertEqual((copy_rep["status"], copy_rep["accepted"]), ("applied", {"dtj_faq.heading": "Your questions"}))
            self.assertNotIn("system", copy_rep["request"])
            self.assertIn("Your questions", Path(tmp, "template.json").read_text(encoding="utf-8"))

    def test_a_live_run_without_a_key_calls_nothing(self):
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict("os.environ", env, clear=True), \
                mock.patch.object(run_page, "make_client", side_effect=AssertionError("must not create a client")):
            self.assertEqual(run_page.main(["--example", "toilova", "--out", tmp, "--copy", "live", "--no-browser"]), 1)

    def test_every_example_brand_builds_and_reviews_without_errors_in_the_stand_in_browser(self):
        for name in ["toilova", *fixtures.BRANDS]:
            with tempfile.TemporaryDirectory() as tmp:
                self.assertEqual(run_page.main(["--example", name, "--out", tmp], browser=FakeBrowser([])), 0, name)


if __name__ == "__main__":
    unittest.main()
