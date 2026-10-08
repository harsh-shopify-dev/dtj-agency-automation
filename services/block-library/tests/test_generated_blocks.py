"""Tests that run for EVERY generated block (any manifest with `settings`): licence gate, empty copy, escaping,
standard controls, and that nobody hand-edited a generated file.

Snippets are wrapped in the theme editor's HTML comments, as on a real store (see test_licence_render.py).
Shopify-only filters are stubbed.
"""
import json
import os
import re
import sys
import unittest
from pathlib import Path

TOOLS_HOME = Path(__file__).resolve().parents[1]  # services/block-library: the shared tools live here
ROOT = Path(os.environ.get("DTJ_APP_ROOT") or TOOLS_HOME).resolve()  # the second app runs these generic tests with DTJ_APP_ROOT set
sys.path.insert(0, str(TOOLS_HOME / "tools"))
import build_blocks as bb  # noqa: E402
import check_library as cl  # noqa: E402

try:
    from liquid import DictLoader, Environment
except ImportError:
    Environment = None

SNIPPETS = cl.ext_of(ROOT) / "snippets"
STANDARD_IDS = {
    "spacing": {"padding_top", "padding_bottom", "padding_left", "padding_right", "margin_top", "margin_bottom"},
    "spacing_v": {"padding_top", "padding_bottom"},
    "gutter": {"side_padding"},
    "align": {"align"}, "colors": {"text_color", "background"}, "shape": {"corner_radius"}, "text_size": {"text_size"},
}


def generated():
    out = []
    for path in sorted((ROOT / "manifests").glob("*.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if "settings" in manifest:
            out.append(manifest)
    return out


def block_text(manifest):
    return (ROOT / manifest["block_file"]).read_text(encoding="utf-8")


def defaults(manifest):
    # Shopify gives every declared setting a value: its default, or nil when it has none, and nil counts as `blank`.
    # python-liquid says nil is NOT blank (checked 5 Oct 2026), so an unset setting is modelled as "" (blank in both).
    schema = cl.extract_schema(block_text(manifest))
    return {s["id"]: s.get("default", "") for s in schema["settings"] if "id" in s}


def render(manifest, overlay=None, metafield="active", design_mode=False, keep_comments=False, wrap=True, product=None):
    def source(path):
        text = path.read_text(encoding="utf-8")
        return f"<!-- BEGIN app snippet: {path.stem} -->{text}<!-- END app snippet -->" if wrap else text

    env = Environment(loader=DictLoader({p.stem: source(p) for p in SNIPPETS.glob("*.liquid")}))
    env.add_filter("image_url", lambda value, **kw: f"//img.example/{value}")
    env.add_filter("payment_type_img_url", lambda value: f"//pay.example/{value}.svg")
    env.add_filter("json", lambda value: json.dumps(value, ensure_ascii=False, default=str))  # Shopify's json filter
    env.add_filter("video_tag", lambda value, **kw: f'<video id="{kw.get("id")}" class="{kw.get("class")}" data-source="{value}"></video>')
    env.add_filter("money", lambda value: f"Rs. {value}")
    env.add_filter("money_without_trailing_zeros", lambda value: f"Rs. {value}")
    app = {"metafields": {"dtj": {"licence": {"value": metafield}}}} if metafield is not None else {"metafields": {}}
    template = env.from_string(cl.strip_schema(block_text(manifest)), globals={"request": {"design_mode": design_mode}})
    context = {"app": app, "block": {"settings": {**defaults(manifest), **(overlay or {})}, "shopify_attributes": ""}}
    if product is None:
        product = manifest.get("test", {}).get("product")  # a block that reads the product brings its own sample one
    if product is not None:
        context["product"] = product
    html = template.render(**context)
    return (html if keep_comments else re.sub(r"<!--.*?-->", "", html, flags=re.S)).strip()


class GeneratedFilesTests(unittest.TestCase):
    def test_there_are_generated_blocks(self):
        self.assertGreaterEqual(len(generated()), 1)

    def test_generated_files_are_up_to_date(self):
        # fails if someone edits dtj-<id>.liquid / .css by hand instead of the manifest, body or stylesheet source
        for path, expected in bb.targets():
            self.assertEqual(path.read_text(encoding="utf-8"), expected, f"{path.name} is stale: run tools/build_blocks.py")

    def test_every_block_has_all_its_standard_controls(self):
        for manifest in generated():
            ids = {s["id"] for s in cl.extract_schema(block_text(manifest))["settings"] if "id" in s}
            for control in manifest["standard_controls"]:
                self.assertTrue(STANDARD_IDS[control] <= ids, f"{manifest['id']} lacks {control}")

    def test_the_builder_refuses_a_body_that_brings_its_own_gate(self):
        manifest = generated()[0]
        with self.assertRaises(ValueError):
            bb.build_one(manifest, "{%- render 'dtj-licence' -%}", "")

    def test_the_builder_refuses_duplicate_setting_ids(self):
        manifest = {**generated()[0], "settings": generated()[0]["settings"] + [{"type": "range", "id": "padding_top", "label": "x", "min": 0, "max": 10, "step": 1, "default": 0}]}
        with self.assertRaises(ValueError):
            bb.build_one(manifest, "x", "")


@unittest.skipIf(Environment is None, "python-liquid not installed (use .work/.venv)")
class EveryBlockTests(unittest.TestCase):
    def test_licensed_and_filled_renders_the_expected_content(self):
        for m in generated():
            for wrap in (True, False):
                html = render(m, m["test"]["sample"], wrap=wrap)
                for needle in m["test"]["expect"]:
                    self.assertIn(needle, html, f"{m['id']} (wrap={wrap}) is missing {needle!r}")

    def test_not_licensed_renders_nothing_and_ships_no_markup(self):
        for m in generated():
            for value in ("inactive", "revoked", "", None):
                self.assertEqual(render(m, m["test"]["sample"], metafield=value), "", f"{m['id']} showed content with flag {value!r}")
                raw = render(m, m["test"]["sample"], metafield=value, keep_comments=True)
                for needle in m["test"]["expect"]:
                    self.assertNotIn(needle, raw, f"{m['id']} leaked {needle!r} with flag {value!r}")

    def test_flag_is_case_and_space_tolerant_but_exact(self):
        for m in generated():
            self.assertIn(m["test"]["expect"][0], render(m, m["test"]["sample"], metafield="  Active "), m["id"])
            self.assertEqual(render(m, m["test"]["sample"], metafield="active-ish"), "", m["id"])

    def test_editor_notice_explains_why_it_is_hidden(self):
        for m in generated():
            self.assertIn("flag seen: inactive", render(m, m["test"]["sample"], metafield="inactive", design_mode=True), m["id"])

    def test_no_copy_means_no_block_even_with_a_licence(self):
        for m in generated():
            self.assertEqual(render(m, {}, product={}), "", f"{m['id']} rendered with no copy: defaults must be empty")  # product={}: no product data either

    def test_whitespace_only_copy_counts_as_empty(self):
        for m in generated():
            text_slots = {s["id"]: "   " for s in m["slots"] if s["type"] == "text"}
            if text_slots:
                self.assertEqual(render(m, text_slots, product={}), "", m["id"])

    def test_plain_text_slots_are_escaped(self):
        for m in generated():
            overlay = {**m["test"]["sample"], **{s["id"]: "<script>alert(1)</script>" for s in m["slots"] if s["type"] == "text"}}
            html = render(m, overlay)
            self.assertNotIn("<script>", html, m["id"])

    def test_standard_colours_only_appear_when_set(self):
        for m in generated():
            if "colors" in m["standard_controls"]:
                self.assertNotIn("--dtj-text-color", render(m, m["test"]["sample"]), m["id"])
                self.assertIn("--dtj-text-color: rgb(1, 2, 3)", render(m, {**m["test"]["sample"], "text_color": "rgb(1, 2, 3)"}), m["id"])


class RuleCheckTests(unittest.TestCase):
    def test_every_manifest_passes_the_library_rules(self):
        for path in sorted((ROOT / "manifests").glob("*.json")):
            self.assertEqual(cl.check_block(path), [], path.stem)


if __name__ == "__main__":
    unittest.main()
