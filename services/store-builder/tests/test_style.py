import json
import tempfile
import unittest
from pathlib import Path

from provision import style
from provision.run import InputError, validate

SETTINGS = """/*
 * generated header
 */
{
  "current": {
    "type_body_font": "inter_n4",
    "type_heading_font": "inter_n7",
    "color_palette": {"background": "#ffffff", "foreground": "#000000", "color1": "#333333", "color2": "#EEF1EA", "color3": "#DFDFDF"}
  },
  "presets": {"Default": {"type_body_font": "inter_n4"}}
}
"""


def png(path, rgb, size=(40, 40), alpha=255):
    from PIL import Image
    Image.new("RGBA", size, (*rgb, alpha)).save(path)


class ContrastTests(unittest.TestCase):
    def test_black_on_white_is_21(self):
        self.assertAlmostEqual(style.contrast("#000000", "#FFFFFF"), 21.0, places=1)

    def test_mix(self):
        self.assertEqual(style.mix("#000000", "#FFFFFF", 0.5), "#808080")


class PaletteTests(unittest.TestCase):
    def test_nothing_provided_gives_defaults_and_says_so(self):
        p = style.resolve_palette(None)
        self.assertEqual({v["source"] for k, v in p.items() if k in ("background", "foreground", "color1")}, {"default"})
        self.assertEqual(p["color2"]["source"], "derived")

    def test_provided_colors_are_kept(self):
        p = style.resolve_palette({"colors": {"primary": "#1f3a5f", "accent": "#c8963e", "background": "#ffffff", "text": "#1a1a1a"}})
        self.assertEqual(p["color1"], {"value": "#1F3A5F", "source": "provided"})
        self.assertEqual(p["color2"], {"value": "#C8963E", "source": "provided"})
        self.assertEqual(p["foreground"]["source"], "provided")

    def test_unreadable_text_is_corrected(self):
        p = style.resolve_palette({"colors": {"background": "#FFFFFF", "text": "#EEEEEE"}})
        self.assertEqual(p["foreground"], {"value": "#000000", "source": "adjusted_for_contrast"})

    def test_light_primary_is_darkened_until_buttons_are_readable(self):
        p = style.resolve_palette({"colors": {"primary": "#FFE066"}})
        self.assertEqual(p["color1"]["source"], "adjusted_for_contrast")
        self.assertGreaterEqual(style.contrast(p["color1"]["value"], p["background"]["value"]), style.MIN_BRAND_CONTRAST)

    def test_every_result_is_readable(self):
        for primary in ("#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#808080", "#123456"):
            p = style.resolve_palette({"colors": {"primary": primary}})
            self.assertGreaterEqual(style.contrast(p["color1"]["value"], p["background"]["value"]), style.MIN_BRAND_CONTRAST, primary)

    def test_primary_comes_from_the_logo_when_missing(self):
        with tempfile.TemporaryDirectory() as d:
            logo = Path(d, "logo.png")
            png(logo, (200, 30, 30))
            p = style.resolve_palette({"logo": "logo.png"}, logo)
            self.assertEqual(p["color1"]["source"] in ("from_logo", "adjusted_for_contrast"), True)
            r, g, b = style._rgb(p["color1"]["value"])
            self.assertTrue(r > g and r > b)  # still reddish

    def test_grey_or_transparent_logo_falls_back_to_default(self):
        with tempfile.TemporaryDirectory() as d:
            for name, rgb, alpha in (("grey.png", (120, 120, 120), 255), ("clear.png", (200, 30, 30), 0), ("white.png", (255, 255, 255), 255)):
                png(Path(d, name), rgb, alpha=alpha)
                self.assertEqual(style.resolve_palette(None, Path(d, name))["color1"]["source"], "default", name)

    def test_bad_hex_is_rejected(self):
        with self.assertRaises(ValueError):
            style.resolve_palette({"colors": {"primary": "blue"}})

    def test_schema_accepts_style_and_rejects_bad_values(self):
        base = {"client_id": "t1", "brand_name": "T", "store_domain": "t.myshopify.com"}
        validate({**base, "style": {"colors": {"primary": "#1F3A5F"}, "fonts": {"heading": "Playfair Display"}, "logo": "logo.png"}},
                 "brand-config.schema.json")
        for bad in ({"colors": {"primary": "red"}}, {"logo": "../x.png"}, {"fonts": {"body": "Evil;Font"}}, {"colors": {"x": "#FFFFFF"}}):
            with self.assertRaises(InputError):
                validate({**base, "style": bad}, "brand-config.schema.json")


class FontAndSettingsTests(unittest.TestCase):
    def test_font_handles(self):
        self.assertEqual(style.font_handle("Playfair Display", 7), "playfair_display_n7")
        self.assertEqual(style.font_handle("Inter"), "inter_n4")
        with self.assertRaises(ValueError):
            style.font_handle("Bad;Name")

    def test_apply_changes_current_only_and_keeps_header(self):
        palette = style.resolve_palette({"colors": {"primary": "#1F3A5F"}})
        text, changes = style.apply_to_settings(SETTINGS, palette, style.resolve_fonts({"fonts": {"heading": "Lora", "body": "Inter"}}),
                                                "shopify://shop_images/logo.png")
        self.assertTrue(text.startswith("/*\n * generated header"))
        data = json.loads(text[text.index("{"):])
        self.assertEqual(data["current"]["color_palette"]["color1"], "#1F3A5F")
        self.assertEqual(data["current"]["type_heading_font"], "lora_n7")
        self.assertEqual(data["current"]["logo"], "shopify://shop_images/logo.png")
        self.assertEqual(data["presets"]["Default"]["type_body_font"], "inter_n4")  # presets untouched
        self.assertTrue(any(c["setting"] == "color_palette.color1" and c["source"] == "provided" for c in changes))

    def test_applying_twice_changes_nothing_the_second_time(self):
        palette = style.resolve_palette({"colors": {"primary": "#1F3A5F"}})
        once, _ = style.apply_to_settings(SETTINGS, palette, {})
        _, changes = style.apply_to_settings(once, palette, {})
        self.assertEqual(changes, [])


if __name__ == "__main__":
    unittest.main()
