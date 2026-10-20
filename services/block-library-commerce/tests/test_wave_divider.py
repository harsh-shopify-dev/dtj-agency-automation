"""DTJ Wave Divider: a decorative single or layered wave, drawn from our own maths."""
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
MANIFEST = json.loads((HERE / "manifests" / "wave-divider.json").read_text(encoding="utf-8"))
CSS = HERE / "extensions" / "dtj-commerce" / "assets" / "dtj-wave-divider.css"


def paths(html):
    return re.findall(r'<path d="([^"]+)"', html)


def y_values(d):
    nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", d)]
    # M x y, L x y, Q cx cy x y, T x y ... L x y Z: every second number from the second one is a y
    return nums[1::2]


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class WaveDividerTests(unittest.TestCase):
    m = MANIFEST

    def r(self, design_mode=False, **extra):
        return render(self.m, {"wave_color": "#b0daeb", **extra}, design_mode=design_mode)

    def test_nothing_shows_until_a_wave_color_is_picked_and_the_editor_says_so(self):
        self.assertEqual(render(self.m, {"wave_color": ""}), "")
        hint = render(self.m, {"wave_color": ""}, design_mode=True)
        self.assertIn("DTJ Wave Divider is empty", hint)
        self.assertNotIn("<svg", hint)

    def test_it_is_decorative_has_no_text_no_script_and_hides_from_readers(self):
        html = self.r()
        self.assertIn('aria-hidden="true"', html)
        self.assertNotIn("<script", html)
        self.assertNotRegex(re.sub(r"<[^>]+>", "", html).strip(), r"\w")  # no words at all

    def test_a_single_wave_is_one_svg_with_the_right_number_of_humps(self):
        html = self.r(waves=6, animate=False)
        self.assertEqual(html.count("<svg"), 1)
        d = paths(html)[0]
        self.assertTrue(d.startswith("M0 100 L0 50 Q "))
        self.assertTrue(d.endswith(" L 1200 100 Z"))
        self.assertEqual(d.count(" T "), 5)  # 6 humps: one Q and five T
        self.assertIn('viewBox="0 0 1200 100"', html)

    def test_drifting_waves_are_drawn_two_screens_wide_so_the_loop_is_seamless(self):
        html = self.r(waves=6, animate=True)
        self.assertIn("dtj-wv--drift", html)
        self.assertIn("--wv-periods: 2", html)
        self.assertIn('viewBox="0 0 2400 100"', html)
        d = paths(html)[0]
        self.assertEqual(d.count(" T "), 11)  # 12 humps over two screens
        self.assertTrue(d.endswith(" L 2400 100 Z"))
        still = self.r(animate=False)
        self.assertNotIn("dtj-wv--drift", still)
        self.assertIn("--wv-periods: 1", still)

    def test_layered_waves_cross_each_other_and_the_front_one_is_solid(self):
        html = self.r(style="layered", layers=4, waves=6, animate=True)
        self.assertEqual(html.count("<svg"), 4)
        ds = paths(html)
        self.assertEqual(len({d.count(" T ") for d in ds}), 4)  # each layer has its own number of humps
        ops = [float(x) for x in re.findall(r"--wv-op: ([\d.]+)", html)]
        self.assertEqual(ops, sorted(ops))
        self.assertEqual(ops[-1], 1.0)
        self.assertLess(ops[0], 0.5)
        durs = [float(x) for x in re.findall(r"--wv-dur: ([\d.]+)s", html)]
        self.assertEqual(len(set(durs)), 4)  # different speeds
        self.assertEqual(html.count("dtj-wv__svg--rev"), 2)  # every second layer drifts the other way
        self.assertEqual(self.r(style="layered", layers=2).count("<svg"), 2)
        self.assertEqual(self.r(style="single", layers=4).count("<svg"), 1)  # layers only count for the layered style

    def test_every_wave_stays_inside_its_band_at_the_deepest_setting(self):
        for style in ("single", "layered"):
            html = self.r(style=style, layers=4, wave_depth=60, waves=8)
            for d in paths(html):
                ys = y_values(d)
                # control points reach twice the amplitude but the curve itself peaks at the amplitude: check the drawn crests and troughs
                self.assertTrue(all(-30 <= y <= 130 for y in ys), (style, min(ys), max(ys)))
            # the baselines plus and minus the amplitude (30) never leave 0..100
            mids = [int(m) for m in re.findall(r"L0 (\d+) Q", html)]
            for mid in mids:
                self.assertGreaterEqual(mid - 30, 0)
                self.assertLessEqual(mid + 30, 100)

    def test_size_flip_and_pull_follow_the_settings(self):
        html = self.r(wave_height=200, wave_height_mobile=60, flip=True, pull=24)
        for part in ("--wv-h-d: 200px", "--wv-h-m: 60px", "dtj-wv--flip", "--wv-pull: 24px"):
            self.assertIn(part, html)
        self.assertNotIn("dtj-wv--flip", self.r())

    def test_the_css_drifts_by_exactly_one_screen_and_respects_reduced_motion(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn("translateX(-50%)", css)
        self.assertIn("prefers-reduced-motion: reduce", css)
        self.assertRegex(css, r"prefers-reduced-motion: reduce\)[^@]*animation: none")
        self.assertRegex(css, r"(?m)^\.dtj-wv \{[^}]*width: 100%")
        self.assertRegex(css, r"overflow: hidden")
        self.assertRegex(css, r"(?m)^\.dtj-wv__svg \{[^}]*max-width: none")  # the theme caps svg width at 100%: a 2-screen-wide layer must override it
        self.assertIn("pointer-events: none", css)  # never in the way of a click on the section above or below

    def test_the_block_has_a_sane_number_of_settings_and_headers(self):
        interactive = [s for s in self.m["settings"] if s["type"] not in ("header", "paragraph")]
        headers = [s for s in self.m["settings"] if s["type"] in ("header", "paragraph")]
        self.assertLessEqual(len(interactive) + 3, 75)
        self.assertLessEqual(len(headers) + 1, 6)


if __name__ == "__main__":
    unittest.main()
