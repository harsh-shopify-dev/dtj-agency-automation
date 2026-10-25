"""Header and footer from the brand's palette (Harsh, 21 Oct 2026: "the header and footer will be designed according to the color palette"):
the builder, the run against a stand-in draft theme and the Tier 2 write of the two group files. Nothing reaches Shopify."""
import contextlib
import copy
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_home_page import brand as _brand  # noqa: E402

from page_builder import direction, push_page, run_chrome  # noqa: E402
from page_builder import theme_target as tt  # noqa: E402
from page_builder.assemble import InputError  # noqa: E402
from page_builder.assemble_chrome import FOOTER_FILE, HEADER_FILE, PARTS, build_chrome, check_parts  # noqa: E402
from provision.theme import ThemeError  # noqa: E402

STORE, THEME = "test-store.myshopify.com", "123456"
SRC = "the brand's shipping policy page, 21 Oct 2026"

# Horizon 4.2.0 as it ships (the elevate-with-harsh draft on 21 Oct 2026, trimmed): the placeholders a client must never keep
HEADER = {"sections": {
    "header_announcements_9jGBFp": {"type": "header-announcements", "blocks": {"announcement_BxgCk9": {"type": "_announcement", "settings": {
        "text": "Welcome to our store", "link": "", "font": "var(--font-subheading--family)", "font_size": "0.75rem"}}},
        "block_order": ["announcement_BxgCk9"], "settings": {"speed": 5, "divider_width": 1, "padding-block-start": 15, "padding-block-end": 15}},
    "header_section": {"type": "header", "settings": {"logo_position": "left", "menu_position": "left", "show_search": True}}},
    "order": ["header_announcements_9jGBFp", "header_section"]}
FOOTER = {"sections": {
    "footer": {"type": "footer", "blocks": {"group_wErUQf": {"type": "group", "settings": {"gap": 12}, "blocks": {
        "text_pF6rVi": {"type": "text", "settings": {"text": "<h2>Join our email list</h2>"}},
        "text_HafH7P": {"type": "text", "settings": {"text": "<p>Get exclusive deals and early access to new products.</p>"}},
        "email-signup_HafH7P": {"type": "email-signup", "settings": {"label": "Sign up", "style_class": "button-secondary"}}}},
        "menu_footer": {"type": "menu", "settings": {"menu": "footer"}}},
        "block_order": ["group_wErUQf", "menu_footer"], "settings": {"background_color": "{{ settings.color_palette.color1 }}"}},
    "utilities": {"type": "footer-utilities", "blocks": {
        "copyright": {"type": "footer-copyright", "settings": {"show_powered_by": True}},
        "policy_list": {"type": "footer-policy-list", "settings": {}},
        "social_icons": {"type": "social-links", "settings": {"facebook_url": "https://www.facebook.com", "instagram_url": "https://www.instagram.com",
                                                              "youtube_url": "https://www.youtube.com"}}},
        "block_order": ["copyright", "policy_list", "social_icons"], "settings": {}}},
    "order": ["footer", "utilities"]}


def brand():
    return _brand("home-care")


def facts(lines=("Free shipping above Rs. 499", "Cash on delivery")):
    return {"announcements": {"source": SRC, "items": [{"text": t, "source": SRC} for t in lines]}}


def build(chrome=None, f=None):
    return build_chrome(brand(), facts() if f is None else f, chrome or {}, copy.deepcopy(HEADER), copy.deepcopy(FOOTER))


def blocks_of(group, sid):
    return group["sections"][sid].get("blocks", {})


class BuildTests(unittest.TestCase):
    def test_colours_come_from_the_brands_palette_and_every_pair_reads_clearly(self):
        res = build()
        roles = direction.derive(brand(), None).roles
        self.assertEqual(res.header["sections"]["header_announcements_9jGBFp"]["settings"]["background_color"], roles["dark"])
        hs = res.header["sections"]["header_section"]["settings"]
        self.assertEqual((hs["background_color_top"], hs["text_color_top"]), (roles["bg"], roles["text"]))
        self.assertEqual((hs["bubble_background_color"], hs["bubble_text_color"]), (roles["button_bg"], roles["button_text"]))
        self.assertEqual(res.footer["sections"]["footer"]["settings"]["background_color"], roles["dark"])
        self.assertEqual(res.report["problems"], [])
        self.assertTrue(all(v >= 4.5 for v in res.report["contrast"].values()), res.report["contrast"])
        self.assertEqual((hs["logo_position"], hs["show_search"]), ("left", True))  # the theme's own layout choices are kept

    def test_a_bold_brand_wears_its_own_colour_on_the_bar_and_the_footer(self):
        # Harsh, 24 Oct 2026 (NoCheat, playful): the header and footer in the page's maroon, not its near-black ink
        bold = {**brand(), "vibe": "playful", "voice": "playful", "colors": {"primary": "#9E1B22", "accent": "#FFC94A",
                                                                             "background": "#FFFFFF", "text": "#24090B"}}
        res = build_chrome(bold, facts(), {}, copy.deepcopy(HEADER), copy.deepcopy(FOOTER))
        roles = direction.derive(bold, None).roles
        self.assertEqual(res.header["sections"]["header_announcements_9jGBFp"]["settings"]["background_color"], roles["band"])
        self.assertEqual(res.footer["sections"]["footer"]["settings"]["background_color"], roles["band"])
        self.assertTrue(all(v >= 4.5 for v in res.report["contrast"].values()), res.report["contrast"])

    def test_the_announcement_lines_come_from_the_facts_with_their_source(self):
        res = build()
        sec = res.header["sections"]["header_announcements_9jGBFp"]
        self.assertEqual([sec["blocks"][b]["settings"]["text"] for b in sec["block_order"]], ["Free shipping above Rs. 499", "Cash on delivery"])
        self.assertEqual(res.report["provenance"]["header_announcements_9jGBFp.dtj_announcement_1"]["source"], SRC)
        self.assertIn("Welcome to our store", res.report["removed_placeholders"])
        sample = build(f={"announcements": {"source": "SAMPLE", "items": [{"text": "Sample: your shipping promise goes here", "source": "SAMPLE demo"}]}})
        self.assertEqual(sample.report["samples"], ["header_announcements_9jGBFp.dtj_announcement_1"])  # marked, so the write needs --allow-samples
        chrome = build(chrome={"announcements": [{"text": "Free returns in 7 days", "source": "refund policy", "link": "/policies/refund-policy"}]})
        b = chrome.header["sections"]["header_announcements_9jGBFp"]["blocks"]["dtj_announcement_1"]["settings"]
        self.assertEqual((b["text"], b["link"]), ("Free returns in 7 days", "/policies/refund-policy"))  # chrome.json wins over the home facts

    def test_without_a_line_the_bar_is_switched_off_never_the_theme_placeholder(self):
        res = build(f={})
        self.assertTrue(res.header["sections"]["header_announcements_9jGBFp"]["disabled"])
        with self.assertRaises(InputError):
            build(f=facts(lines=("Welcome to our store",)))
        with self.assertRaises(InputError):
            build(f={"announcements": {"items": [{"text": "Free shipping"}]}})  # no source

    def test_the_footer_keeps_no_placeholder_promise_or_fake_social_link(self):
        res = build()
        g = blocks_of(res.footer, "footer")["group_wErUQf"]["blocks"]
        self.assertNotIn("exclusive deals", g["text_HafH7P"]["settings"]["text"])
        self.assertEqual(g["text_pF6rVi"]["settings"]["text"], "<h2>Join our email list</h2>")  # a heading that promises nothing stays
        social = blocks_of(res.footer, "utilities")["social_icons"]["settings"]
        self.assertEqual([social[k] for k in ("facebook_url", "instagram_url", "youtube_url")], ["", "", ""])
        self.assertFalse(blocks_of(res.footer, "utilities")["copyright"]["settings"]["show_powered_by"])
        real = build(chrome={"social": {"instagram": {"url": "https://www.instagram.com/toilova/", "source": "the brand's site footer"}}})
        self.assertEqual(blocks_of(real.footer, "utilities")["social_icons"]["settings"]["instagram_url"], "https://www.instagram.com/toilova/")
        with self.assertRaises(InputError):
            build(chrome={"social": {"instagram": {"url": "https://www.instagram.com/x/"}}})  # a link needs where it was found

    def test_every_section_and_block_of_the_theme_is_kept(self):
        res = build()
        self.assertEqual(res.header["order"], HEADER["order"])
        self.assertEqual(res.footer["order"], FOOTER["order"])
        self.assertEqual(set(blocks_of(res.footer, "footer")), set(blocks_of(FOOTER, "footer")))
        self.assertEqual(set(blocks_of(res.footer, "utilities")), set(blocks_of(FOOTER, "utilities")))
        self.assertEqual(blocks_of(res.footer, "footer")["menu_footer"], blocks_of(FOOTER, "footer")["menu_footer"])

    def test_a_value_horizon_does_not_know_is_caught_before_shopify_refuses_the_file(self):
        self.assertTrue(check_parts("header", {"section_height": "huge"}))
        self.assertTrue(check_parts("footer", {"nonsense": 1}))
        self.assertTrue(check_parts("header", {"background_color_top": "blue"}))
        self.assertEqual(check_parts("header", {"background_color_top": "#FFFFFF"}), [])
        self.assertIn("bubble_background_color", PARTS["header"])


class FakeTheme:
    def __init__(self, role="unpublished"):
        self.store, self.role, self.pushed, self.commands = STORE, role, [], []
        self.files = {"config/settings_schema.json": json.dumps([{"name": "theme_info", "theme_name": "Horizon", "theme_version": "4.2.0"}]),
                      "templates/product.json": "{}", HEADER_FILE: json.dumps(HEADER), FOOTER_FILE: json.dumps(FOOTER)}

    def themes(self, theme_id):
        return [{"id": int(theme_id), "name": "Draft copy", "role": self.role}]

    def pull(self, theme_id, files, dest):
        for f in files:
            if f in self.files:
                (dest / f).parent.mkdir(parents=True, exist_ok=True)
                (dest / f).write_text(self.files[f], encoding="utf-8")
        return dest

    def push_product_template(self, theme_id, staging, file):
        if not tt.PAGE_FILES.fullmatch(file):
            raise ThemeError("not a file the page builder writes")
        self.pushed.append(file)
        self.files[file] = (staging / file).read_text(encoding="utf-8")
        return {"role": self.role, "name": "Draft copy"}


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
        code = fn(*a, **k)
    return code, out.getvalue() + err.getvalue()


class RunAndWriteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.client = self.tmp / "client"
        self.client.mkdir()
        (self.client / "brand.json").write_text(json.dumps(brand()), encoding="utf-8")
        (self.client / "home-facts.json").write_text(json.dumps(facts()), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_both_files_are_built_from_the_draft_and_written_only_with_their_own_codes(self):
        fake = FakeTheme()
        code, out = quiet(run_chrome.main, ["--client", str(self.client), "--store", STORE, "--theme", THEME], access=fake)
        self.assertEqual(code, 0, out)
        for name, file in (("header", HEADER_FILE), ("footer", FOOTER_FILE)):
            a = json.loads((self.client / "chrome-run" / name / "approval.json").read_text(encoding="utf-8"))
            self.assertEqual((a["file"], a["pushable"], a["standing_rule"]), (file, True, False))
            code, out = quiet(push_page.main, ["--out", str(self.client / "chrome-run" / name), "--approve", "000000000000", "--approved-by", "Harsh"],
                              access=fake)
            self.assertEqual(code, 1)  # a wrong code writes nothing
            code, out = quiet(push_page.main, ["--out", str(self.client / "chrome-run" / name), "--approve", a["approve_code"], "--approved-by", "Harsh"],
                              access=fake)
            self.assertEqual(code, 0, out)
        self.assertEqual(fake.pushed, [HEADER_FILE, FOOTER_FILE])
        self.assertNotIn("Welcome to our store", fake.files[HEADER_FILE])
        self.assertNotIn("https://www.facebook.com", fake.files[FOOTER_FILE])

    def test_a_live_theme_is_refused_and_only_the_two_group_files_may_be_written(self):
        code, out = quiet(run_chrome.main, ["--client", str(self.client), "--store", STORE, "--theme", THEME], access=FakeTheme(role="main"))
        self.assertEqual(code, 1)
        for ok in (HEADER_FILE, FOOTER_FILE):
            self.assertTrue(tt.PAGE_FILES.fullmatch(ok), ok)
        for bad in ("sections/overlay-group.json", "sections/header.liquid", "config/settings_data.json"):
            self.assertFalse(tt.PAGE_FILES.fullmatch(bad), bad)

    def test_design_only_from_a_pulled_theme(self):
        src = self.tmp / "theme"
        for file, body in ((HEADER_FILE, HEADER), (FOOTER_FILE, FOOTER)):
            (src / file).parent.mkdir(parents=True, exist_ok=True)
            (src / file).write_text(json.dumps(body), encoding="utf-8")
        code, out = quiet(run_chrome.main, ["--client", str(self.client), "--from", str(src)])
        self.assertEqual(code, 0, out)
        self.assertFalse(json.loads((self.client / "chrome-run" / "header" / "approval.json").read_text(encoding="utf-8"))["pushable"])


if __name__ == "__main__":
    unittest.main()
