"""Tests for the Claude API plan step (page_builder/ai_plan.py) and build_pdp(plan=...). No real API call: a stand-in client returns
prepared answers, so these run offline, cost nothing and need no key."""
import json
import tempfile
import unittest
from pathlib import Path

from page_builder import ai_plan, sections
from page_builder.assemble import InputError, build_pdp
from page_builder.copy_step import MODEL
from page_builder.examples import fixtures
from tests.test_copy_step import Block, FakeClient, Resp


def toilova():
    return fixtures.toilova()


def reply(data: dict, **kw) -> Resp:
    return Resp([Block("thinking", ""), Block("text", json.dumps(data))], **kw)


def answer(order, left=(), signature="free_from_band", **choices) -> dict:
    return {
        "sections": [{"section": n, "why": f"why {n}"} for n in order],
        "left_out": [{"section": n, "why": f"skip {n}"} for n in left],
        "signature": signature,
        "brand_choices": {**{k: "keep" for k in ai_plan.CHOICES}, **choices},
        "summary": "Trust first, then how it works.",
    }


ALL = list(sections.BUILDERS)


class MenuAndRequest(unittest.TestCase):
    def test_menu_offers_every_section_and_says_which_the_facts_can_fill(self):
        b, f = toilova()
        menu = {m["section"]: m for m in ai_plan.menu(b, f)}
        self.assertEqual(list(menu), ALL)
        self.assertFalse(menu["reviews_slider"]["available"])
        self.assertIn("REAL reviews", menu["reviews_slider"]["why_not"])
        self.assertFalse(menu["comparison"]["available"])  # TOILOVA's comparison is not approved by the owner
        self.assertTrue(menu["free_from"]["available"])
        self.assertEqual(menu["faq"]["blocks"], ["dtj-sections/faq"])

    def test_request_shape(self):
        b, f = toilova()
        p = ai_plan.request_params(b, f)
        self.assertEqual(p["model"], MODEL)
        self.assertEqual(p["betas"], [ai_plan.FALLBACK_BETA])
        schema = p["output_config"]["format"]["schema"]
        self.assertEqual(schema["properties"]["sections"]["items"]["properties"]["section"]["enum"], ALL)
        self.assertFalse(schema["additionalProperties"])
        req = json.loads(p["messages"][0]["content"][-1]["text"])
        self.assertEqual(req["brand"]["not_set"], ["shape_language", "heading_class"])
        self.assertEqual(req["facts"], f)
        self.assertEqual(req["house_default"][0], "trust_marquee")
        self.assertIn("Never copy their text, numbers, claims", req["agency_references"])  # the sample-page notes travel with every plan
        self.assertNotIn("api_key", json.dumps(p).lower())
        plain = ai_plan.request_params(b, f, fallbacks=False)
        self.assertNotIn("betas", plain)

    def test_reference_images_go_first_as_images(self):
        b, f = toilova()
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp, "ref.png")
            png.write_bytes(b"\x89PNG fake")
            content = ai_plan.request_params(b, f, references=[png])["messages"][0]["content"]
            self.assertEqual(content[0]["type"], "image")
            self.assertEqual(content[0]["source"]["media_type"], "image/png")
            self.assertIn("references only", content[1]["text"])
            bad = Path(tmp, "ref.pdf")
            bad.write_bytes(b"x")
            with self.assertRaises(ai_plan.ReferenceImageError):
                ai_plan.load_references([bad])
            with self.assertRaises(ai_plan.ReferenceImageError):
                ai_plan.load_references([png] * 6)
            big = Path(tmp, "big.jpg")
            big.write_bytes(b"0" * (ai_plan.MAX_IMAGE_BYTES + 1))
            with self.assertRaises(ai_plan.ReferenceImageError):
                ai_plan.load_references([big])

    def test_dry_run_calls_nothing(self):
        b, f = toilova()
        out = ai_plan.run_plan_step(b, f)
        self.assertEqual((out.mode, out.status, out.plan), ("dry-run", "not-run", None))
        self.assertEqual(out.brand, b)


class LivePlan(unittest.TestCase):
    ORDER = ["how_split", "trust_marquee", "free_from", "why_features", "faq"]

    def run_plan(self, data=None, **kw):
        b, f = toilova()
        client = FakeClient(kw.pop("resp", None) or reply(data), kw.pop("exc", None))
        return b, f, client, ai_plan.run_plan_step(b, f, client=client, **kw)

    def test_plan_decides_the_sections_and_their_order(self):
        b, f, client, out = self.run_plan(answer(self.ORDER, [n for n in ALL if n not in self.ORDER]))
        self.assertEqual(out.status, "applied")
        self.assertEqual(client.calls[0][0], "beta")
        self.assertEqual(out.notes, [])
        result = build_pdp(out.brand, f, plan=out.plan)
        self.assertEqual([s["kind"] for s in result.report["sections_built"]], self.ORDER)
        self.assertEqual(result.report["chosen_by"], "plan")
        self.assertEqual(result.report["sections_built"][0]["why"], "why how_split")
        omitted = {o["section"]: o["reason"] for o in result.report["sections_omitted"]}
        self.assertEqual(omitted["story_split"], "left out by the plan: skip story_split")
        self.assertTrue(result.ok, result.report)

    def test_signature_from_the_plan_puts_its_section_on_the_dark_band(self):
        _, f, _, out = self.run_plan(answer(["trust_marquee", "proof_panel", "free_from"], signature="proof_panel"))
        roles = {s["kind"]: s["role"] for s in build_pdp(out.brand, f, plan=out.plan).report["sections_built"]}
        self.assertEqual(roles["proof_panel"], "dark")
        self.assertNotEqual(roles["free_from"], "dark")

    def test_open_style_choices_are_filled_but_the_clients_choices_win(self):
        _, f, _, out = self.run_plan(answer(self.ORDER, shape_language="round", heading_class="serif", voice="luxe"))
        self.assertEqual(out.brand["shape_language"], "round")
        self.assertEqual(out.brand["fonts"]["heading_class"], "serif")
        self.assertEqual(out.brand["voice"], "plain")  # TOILOVA's own answer
        self.assertTrue(any("client already chose it" in n for n in out.notes))
        self.assertEqual(build_pdp(out.brand, f, plan=out.plan).report["direction"]["shape"]["name"], "round")

    def test_failures_leave_the_house_rules_in_charge(self):
        cases = {
            "refusal": dict(resp=reply({}, stop="refusal")),
            "cut-off": dict(resp=reply({}, stop="max_tokens")),
            "api-error": dict(exc=RuntimeError("overloaded")),
            "bad-json": dict(resp=Resp([Block("text", "not json")])),
            "empty": dict(resp=reply(answer(["reviews_slider"]))),
        }
        for status, kw in cases.items():
            with self.subTest(status):
                b, f, _, out = self.run_plan(**kw)
                self.assertEqual(out.status, status)
                self.assertIsNone(out.plan)
                self.assertEqual(out.brand, b)
                self.assertEqual(build_pdp(out.brand, f, plan=out.plan).report["chosen_by"], "house rules")

    def test_report_holds_usage_and_no_secret(self):
        _, _, _, out = self.run_plan(answer(self.ORDER))
        rep = out.as_report()
        self.assertEqual(rep["decided_by"], "claude plan (checked by code)")
        self.assertEqual(rep["usage"]["input_tokens"], 1200)
        self.assertIsNotNone(rep["cost_usd"])
        self.assertNotIn("sk-ant", json.dumps(rep))


class ClaudeCodeAnswer(unittest.TestCase):
    """The plan written by a Claude Code session instead of the API: same request, same gate."""

    def test_request_file_carries_the_same_prompt_menu_and_answer_shape(self):
        b, f = toilova()
        req = ai_plan.plan_request(b, f)
        self.assertEqual(req["system"], ai_plan.system_prompt())
        self.assertEqual(req["answer_schema"], ai_plan.response_schema())
        self.assertEqual([m["section"] for m in req["request"]["menu"]], ALL)
        with self.assertRaises(ai_plan.ReferenceImageError):
            ai_plan.plan_request(b, f, references=["page.pdf"])

    def test_answer_goes_through_the_same_gate(self):
        b, f = toilova()
        out = ai_plan.apply_answer(b, f, answer(["trust_marquee", "reviews_slider", "faq"], shape_language="round"))
        self.assertEqual((out.mode, out.status), ("claude-code", "applied"))
        self.assertEqual(out.plan["order"], ["trust_marquee", "faq"])  # reviews dropped: no real reviews
        self.assertEqual(out.brand["shape_language"], "round")
        self.assertEqual(out.as_report()["decided_by"], "claude code session plan (checked by code)")
        bad = ai_plan.apply_answer(b, f, None)
        self.assertEqual((bad.status, bad.plan, bad.as_report()["decided_by"]), ("bad-json", None, "house rules (recipes/pdp.json)"))

    def test_answer_files_plain_or_api_shaped(self):
        data = answer(["faq"])
        with tempfile.TemporaryDirectory() as tmp:
            plain, wrapped, junk = Path(tmp, "a.json"), Path(tmp, "b.json"), Path(tmp, "c.json")
            plain.write_text(json.dumps(data), encoding="utf-8")
            wrapped.write_text(json.dumps({"content": [{"type": "text", "text": json.dumps(data)}]}), encoding="utf-8")
            junk.write_text("not json", encoding="utf-8")
            self.assertEqual(ai_plan.read_answer(plain), data)
            self.assertEqual(ai_plan.read_answer(wrapped), data)
            self.assertIsNone(ai_plan.read_answer(junk))
            self.assertIsNone(ai_plan.read_answer(Path(tmp, "missing.json")))


class Guardrails(unittest.TestCase):
    def check(self, data):
        b, f = toilova()
        return ai_plan.check_plan(data, b, f)

    def test_a_section_the_facts_cannot_fill_is_left_out_and_reported(self):
        plan, _, notes = self.check(answer(["trust_marquee", "reviews_slider", "faq"]))
        self.assertEqual(plan["order"], ["trust_marquee", "faq"])
        self.assertIn("cannot be built", plan["left_out"]["reviews_slider"])
        self.assertTrue(any("reviews_slider" in n for n in notes))

    def test_same_figures_twice_keeps_the_first(self):
        plan, _, notes = self.check(answer(["facts_glance", "why_features", "proof_panel"]))
        self.assertEqual(plan["order"], ["facts_glance", "why_features"])
        self.assertIn("same figures", plan["left_out"]["proof_panel"])
        self.assertTrue(notes)

    def test_duplicates_unknown_and_unmentioned(self):
        data = answer(["faq", "trust_marquee", "trust_marquee"])
        data["sections"].append({"section": "hero_banner", "why": "x"})
        plan, _, notes = self.check(data)
        self.assertEqual(plan["order"], ["trust_marquee", "faq"])  # faq moved last, duplicate dropped, unknown ignored
        self.assertTrue(any("twice" in n for n in notes))
        self.assertTrue(any("unknown section" in n for n in notes))
        self.assertTrue(any("faq moved" in n for n in notes))
        self.assertEqual(plan["left_out"]["story_split"], "not mentioned by the plan")
        self.assertEqual(set(plan["order"]) | set(plan["left_out"]), set(ALL))

    def test_unknown_signature_and_choice_are_ignored(self):
        data = answer(["trust_marquee"], signature="hero_slideshow", shape_language="blobby")
        plan, brand, notes = self.check(data)
        self.assertIsNone(plan["signature"])
        self.assertNotIn("shape_language", brand)
        self.assertEqual(len(notes), 2 + len(ALL) - 1)  # signature, choice, and every unmentioned section

    def test_build_refuses_a_plan_with_an_unknown_section(self):
        b, f = toilova()
        with self.assertRaises(InputError):
            build_pdp(b, f, plan={"order": ["hero_banner"], "left_out": {}, "why": {}})


if __name__ == "__main__":
    unittest.main()
