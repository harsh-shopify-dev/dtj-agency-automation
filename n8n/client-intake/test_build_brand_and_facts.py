"""Tests for the n8n Code node that turns a client intake form answer into the page builder's
brand profile and product facts (build_brand_and_facts.js).

The node's JavaScript runs here in Node exactly as n8n runs it (wrapped in a function that
receives $json), and its output is checked against the page builder's real JSON schemas.
Run: python -m unittest discover -s n8n/client-intake -t n8n/client-intake
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

import jsonschema

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CODE = HERE / "build_brand_and_facts.js"
EXPORT = HERE / "workflow.json"
SCHEMAS = REPO / "services" / "store-builder" / "page_builder" / "schemas"

RUNNER = r"""
const fs = require('fs');
const src = fs.readFileSync(process.argv[1], 'utf8');
const answers = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = new Function('$json', src)(answers);
process.stdout.write(JSON.stringify(out));
"""

NODE = shutil.which("node")


def run(answers):
    done = subprocess.run([NODE, "-e", RUNNER, str(CODE)], input=json.dumps(answers), capture_output=True,
                          text=True, encoding="utf-8", check=True)
    out = json.loads(done.stdout)
    assert set(out) == {"json"}, out
    return out["json"]


def schema(name):
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))


# A full answer built only from TOILOVA's own text (services/store-builder/page_builder/examples/toilova.json).
TOILOVA = {
    "store_domain": "https://Elevate-With-Harsh.myshopify.com/",
    "brand_name": "TOILOVA",
    "category": "home-care",
    "price_tier": "value (lower price than most)",
    "voice": "plain (simple and direct)",
    "shape_language": "Not sure",
    "color_primary": "#0b4a6f",
    "color_accent": "12803B",
    "color_background": "#fff",
    "color_text": "",
    "heading_style": "Not sure",
    "logo_link": "",
    "product_title": "TOILOVA",
    "product_link": "https://elevate-with-harsh.myshopify.com/products/toilova-1?variant=1",
    "picture_links": "pack | https://cdn.example.com/a.webp\nhttps://cdn.example.com/b.webp",
    "default_source": "product description",
    "buybox_tagline": "Brush-free. No touch.",
    "trust_points": "No scrubbing needed\nFull-bowl foam coverage\nZero touch cleaning [pack artwork]\r\n\nSafe for septic tanks [pack artwork]",
    "benefits": "No scrubbing needed | Sprinkle the sachet, wait, and flush. No brush.\nAcid-free and safe | No toxic fumes.\nSafe for septic tanks [pack artwork]",
    "story_heading": "Foam that actually works. [product artwork text]",
    "story_body": "TOILOVA's smart foam expands to reach deep stains and hidden corners.",
    "steps": "Drop the sachet into the toilet [how-it-works artwork]\nBlue foam rises and covers the bowl\nFlush, and the bowl is left clean",
    "key_facts": "400 g | Net weight | Printed on the pack: 100 g x 4 bags [pack]\n4 bags | 100 g each, in every box [pack]",
    "pack_contents": "Foam powder sachets | Lemon Fresh [pack]",
    "free_from": "Acid\nToxic fumes",
    "faqs": "Do I need a brush? | No. TOILOVA is brush-free. The foam does the work.\nWhat is in the pack? | One box of 400 g, made up of 4 bags of 100 g each. [pack]",
    "reviews": "",
    "rating": "",
    "guarantees": "",
    "comparison_other_label": "Regular cleaners",
    "comparison_rows": "Full coverage | Misses spots [store's own comparison artwork]\nNo scrubbing required | Scrubbing required\nTouch-free cleaning | Requires brushes and contact",
    "comparison_approved": [],
    "facts_confirmed": ["Yes, these facts are true and can be shown on the store"],
    "notes": "",
    "submittedAt": "2026-10-09T10:00:00.000+05:30",
    "formMode": "test",
}


class FullAnswer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = run(TOILOVA)
        cls.brand = json.loads(cls.out["brand_json"])
        cls.facts = json.loads(cls.out["facts_json"])

    def test_clean_answer_is_new_with_no_problems(self):
        self.assertEqual(self.out["problems"], "")
        self.assertEqual(self.out["problem_count"], 0)
        self.assertEqual(self.out["status"], "new")

    def test_outputs_pass_the_page_builder_schemas(self):
        jsonschema.validate(self.brand, schema("brand-profile"))
        jsonschema.validate(self.facts, schema("product-facts"))

    def test_brand_profile(self):
        self.assertEqual(self.brand, {
            "brand_name": "TOILOVA", "category": "home-care", "price_tier": "value", "voice": "plain",
            "colors": {"primary": "#0B4A6F", "accent": "#12803B", "background": "#FFFFFF"},
        })

    def test_store_domain_and_handle_are_normalised(self):
        self.assertEqual(self.out["store_domain"], "elevate-with-harsh.myshopify.com")
        self.assertEqual(self.facts["product"], {"title": "TOILOVA", "handle": "toilova-1"})

    def test_sources_default_or_come_from_brackets(self):
        self.assertEqual(self.facts["trust_points"], [
            {"text": "No scrubbing needed", "source": "product description"},
            {"text": "Full-bowl foam coverage", "source": "product description"},
            {"text": "Zero touch cleaning", "source": "pack artwork"},
            {"text": "Safe for septic tanks", "source": "pack artwork"},
        ])
        self.assertEqual(self.facts["story"]["source"], "product artwork text")
        self.assertEqual(self.facts["steps"], {"items": [
            "Drop the sachet into the toilet", "Blue foam rises and covers the bowl", "Flush, and the bowl is left clean"],
            "source": "how-it-works artwork"})

    def test_split_lines(self):
        self.assertEqual(self.facts["benefits"][0], {"title": "No scrubbing needed",
                         "text": "Sprinkle the sachet, wait, and flush. No brush.", "source": "product description"})
        self.assertEqual(self.facts["benefits"][2], {"title": "Safe for septic tanks", "source": "pack artwork"})
        self.assertEqual(self.facts["key_facts"][0], {"value": "400 g", "label": "Net weight",
                         "note": "Printed on the pack: 100 g x 4 bags", "source": "pack"})
        self.assertEqual(self.facts["faqs"][1]["source"], "pack")
        self.assertEqual(self.facts["pack_contents"], [{"name": "Foam powder sachets", "detail": "Lemon Fresh", "source": "pack"}])
        self.assertEqual(self.facts["buybox"], {"tagline": "Brush-free. No touch.", "source": "product description"})

    def test_comparison_keeps_the_approval_answer_and_labels(self):
        comp = self.facts["comparison"]
        self.assertEqual(len(comp["rows"]), 3)
        self.assertIs(comp["claims_approved"], False)
        self.assertEqual((comp["ours_label"], comp["other_label"]), ("TOILOVA", "Regular cleaners"))
        approved = run({**TOILOVA, "comparison_approved": ["The brand has approved these comparison claims"]})
        self.assertIs(json.loads(approved["facts_json"])["comparison"]["claims_approved"], True)

    def test_nothing_is_invented_and_demo_is_never_set(self):
        for absent in ("reviews", "rating", "guarantees", "media", "demo"):
            self.assertNotIn(absent, self.facts)
        self.assertNotIn("logo", self.brand)

    def test_picture_links_are_kept_apart_from_the_facts(self):
        self.assertEqual(json.loads(self.out["picture_links_json"]), [
            {"role": "pack", "url": "https://cdn.example.com/a.webp"},
            {"role": "photo_2", "url": "https://cdn.example.com/b.webp"},
        ])

    def test_raw_answer_is_stored_unedited(self):
        self.assertEqual(json.loads(self.out["raw_json"]), TOILOVA)
        self.assertEqual(self.out["submitted_at"], TOILOVA["submittedAt"])


class Problems(unittest.TestCase):
    def check(self, changes, *expected):
        out = run({**TOILOVA, **changes})
        self.assertEqual(out["status"], "needs-fixes")
        for text in expected:
            self.assertIn(text, out["problems"])
        jsonschema.validate(json.loads(out["brand_json"]), schema("brand-profile"))
        jsonschema.validate(json.loads(out["facts_json"]), schema("product-facts"))
        return out, json.loads(out["brand_json"]), json.loads(out["facts_json"])

    def test_custom_domain_is_refused(self):
        self.check({"store_domain": "toilova.in"}, ".myshopify.com address")

    def test_theme_id_from_a_number_or_an_editor_link(self):
        self.assertEqual(run({**TOILOVA, "theme_id": "150000000001"})["theme_id"], "150000000001")
        link = "https://admin.shopify.com/store/elevate-with-harsh/themes/150000000001/editor"
        self.assertEqual(run({**TOILOVA, "theme_id": link})["theme_id"], "150000000001")
        self.assertEqual(run(TOILOVA)["theme_id"], "")  # optional: DTJ can add it later
        out, _, _ = self.check({"theme_id": "Horizon draft"}, "should be the theme's number")
        self.assertEqual(out["theme_id"], "")

    def test_bad_colour_is_reported_and_left_out(self):
        _, brand, _ = self.check({"color_accent": "green"}, 'Accent colour: "green"')
        self.assertNotIn("accent", brand["colors"])

    def test_unconfirmed_facts(self):
        self.check({"facts_confirmed": []}, "not confirmed")

    def test_too_few_steps_and_comparison_rows_leave_the_section_out(self):
        _, _, facts = self.check({"steps": "Only one step", "comparison_rows": "A | B\nC | D"},
                                 "at least 2 steps", "at least 3 rows")
        self.assertNotIn("steps", facts)
        self.assertNotIn("comparison", facts)

    def test_bad_review_line_is_reported_not_guessed(self):
        _, _, facts = self.check({"reviews": "Great product\n5 | Priya, Pune | Works well [Judge.me]"}, '"Great product"')
        self.assertEqual(facts["reviews"], [{"quote": "Works well", "name": "Priya", "rating": 5,
                                             "location": "Pune", "source": "Judge.me"}])
        for stars in ("6", "4.5", "0", "five"):
            _, _, facts = self.check({"reviews": f"{stars} | Priya | Works well [Judge.me]"}, "should look like")
            self.assertNotIn("reviews", facts)

    def test_rating_must_be_a_real_score(self):
        _, _, facts = self.check({"rating": "4.65 [Judge.me]"}, "0 to 5")
        self.assertNotIn("rating", facts)
        ok = json.loads(run({**TOILOVA, "rating": "4.6 [Judge.me]"})["facts_json"])
        self.assertEqual(ok["rating"], {"value": "4.6", "source": "Judge.me"})

    def test_over_limit_lists_keep_the_first_and_say_so(self):
        _, _, facts = self.check({"trust_points": "\n".join(f"Point {i}" for i in range(8))}, "only 6 are allowed")
        self.assertEqual([t["text"] for t in facts["trust_points"]], [f"Point {i}" for i in range(6)])

    def test_long_text_is_reported_not_cut(self):
        _, _, facts = self.check({"buybox_tagline": "x" * 41}, "longer than 40")
        self.assertNotIn("buybox", facts)

    def test_missing_source_is_reported(self):
        _, _, facts = self.check({"default_source": "", "free_from": "Acid\nParabens [pack]"}, '"Acid" has no usable source')
        self.assertEqual(facts["free_from"], [{"name": "Parabens", "source": "pack"}])

    def test_unknown_choice_is_reported(self):
        _, brand, _ = self.check({"voice": "shouty"}, 'Brand voice: "shouty"')
        self.assertNotIn("voice", brand)


class Keys(unittest.TestCase):
    def test_answers_keyed_by_label_give_the_same_result(self):
        import re
        labels = dict(re.findall(r"^  (\w+): '([^']+)',$", CODE.read_text(encoding="utf-8"), re.M))
        by_label = {labels.get(k, k): v for k, v in TOILOVA.items()}
        a, b = run(TOILOVA), run(by_label)
        for key in ("brand_json", "facts_json", "picture_links_json", "problems", "status"):
            self.assertEqual(a[key], b[key], key)

    def test_empty_optional_answer_still_valid(self):
        minimal = {"store_domain": "a-b.myshopify.com", "brand_name": "Zed", "category": "other",
                   "product_title": "Zed One", "facts_confirmed": ["Yes"], "submittedAt": "x"}
        out = run(minimal)
        self.assertEqual(out["status"], "new", out["problems"])
        self.assertEqual(json.loads(out["facts_json"]), {"product": {"title": "Zed One"}})
        self.assertEqual(json.loads(out["brand_json"]), {"brand_name": "Zed", "category": "other"})


@unittest.skipUnless(EXPORT.exists(), "workflow not exported yet")
class Export(unittest.TestCase):
    def test_n8n_node_runs_exactly_this_code(self):
        wf = json.loads(EXPORT.read_text(encoding="utf-8"))
        nodes = [n for n in wf["nodes"] if n["type"] == "n8n-nodes-base.code"]
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["parameters"]["jsCode"], CODE.read_text(encoding="utf-8"))

    def test_export_holds_no_secret(self):
        text = EXPORT.read_text(encoding="utf-8").lower()
        for word in ("bearer ", "api_key", "apikey", "password\":", "shpat_", "sk-ant-"):
            self.assertNotIn(word, text)


if NODE is None:
    raise unittest.SkipTest("node is not installed")

if __name__ == "__main__":
    unittest.main()
